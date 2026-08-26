from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from orders.models import Order
from .models import (
    DailySalesSummary,
    ProductSalesMetric,
    DailyProductSales,
)
from .serializers import (
    DailySalesSummarySerializer,
    ProductSalesMetricSerializer,
    DailyProductSalesSerializer,
    DashboardOverviewSerializer,
)


class IsAdminOrManager(permissions.BasePermission):
    """
    Allows platform administrators and authorized warehouse/store staff
    to access analytics.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and (
                getattr(user, "is_superuser", False)
                or getattr(user, "role", None) in [
                    "ADMIN",
                    "WAREHOUSE_STAFF",
                ]
            )
        )


class AnalyticsViewSet(viewsets.ViewSet):
    """
    Analytics API for BanglaMart.

    Provides:
        - Dashboard overview
        - Top selling products
        - Daily sales breakdown
        - Daily product sales
    """

    permission_classes = [IsAdminOrManager]

    # ==========================================================
    # DASHBOARD OVERVIEW
    # ==========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="overview",
    )
    def dashboard_overview(self, request):
        """
        GET /api/analytics/overview/

        Query parameters:

            ?days=30
            ?dark_store_id=<UUID>
        """

        # ------------------------------------------------------
        # Validate days
        # ------------------------------------------------------

        try:
            days = int(
                request.query_params.get(
                    "days",
                    30,
                )
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": "days must be a valid integer."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if days < 1 or days > 365:
            return Response(
                {
                    "detail": "days must be between 1 and 365."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        dark_store_id = request.query_params.get(
            "dark_store_id"
        )

        # ------------------------------------------------------
        # Date range
        # ------------------------------------------------------

        end_date = timezone.now().date()

        start_date = (
            end_date -
            timedelta(days=days - 1)
        )

        # ------------------------------------------------------
        # Orders
        # ------------------------------------------------------

        orders_queryset = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )

        if dark_store_id:
            orders_queryset = orders_queryset.filter(
                dark_store_id=dark_store_id
            )

        # ------------------------------------------------------
        # Aggregation
        # ------------------------------------------------------

        aggregates = orders_queryset.aggregate(
            total_orders=Count("id"),

            completed_orders=Count(
                "id",
                filter=Q(
                    status="DELIVERED"
                ),
            ),

            cancelled_orders=Count(
                "id",
                filter=Q(
                    status="CANCELLED"
                ),
            ),

            gross_revenue=Sum(
                "total_amount",
                filter=Q(
                    payment_status="PAID"
                ),
            ),

            average_order_value=Avg(
                "total_amount",
                filter=Q(
                    payment_status="PAID"
                ),
            ),
        )

        # ------------------------------------------------------
        # Decimal values
        # ------------------------------------------------------

        gross_revenue = (
            aggregates["gross_revenue"]
            or Decimal("0.00")
        )

        average_order_value = (
            aggregates["average_order_value"]
            or Decimal("0.00")
        )

        # ------------------------------------------------------
        # Response
        # ------------------------------------------------------

        payload = {
            "start_date": start_date,
            "end_date": end_date,

            "total_orders": (
                aggregates["total_orders"]
                or 0
            ),

            "completed_orders": (
                aggregates["completed_orders"]
                or 0
            ),

            "cancelled_orders": (
                aggregates["cancelled_orders"]
                or 0
            ),

            "total_gross_revenue": gross_revenue,

            # Until discounts/refunds are calculated
            # separately, don't pretend gross == net.
            "total_net_revenue": gross_revenue,

            "average_order_value": average_order_value,
        }

        serializer = DashboardOverviewSerializer(
            data=payload
        )

        serializer.is_valid(
            raise_exception=True
        )

        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # TOP PRODUCTS
    # ==========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="top-products",
    )
    def top_products(self, request):
        """
        GET /api/analytics/top-products/

        Query parameters:

            ?limit=10
        """

        try:
            limit = int(
                request.query_params.get(
                    "limit",
                    10,
                )
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": "limit must be a valid integer."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if limit < 1 or limit > 100:
            return Response(
                {
                    "detail": "limit must be between 1 and 100."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = (
            ProductSalesMetric.objects
            .select_related("product")
            .order_by("-total_units_sold")
        )

        queryset = queryset[:limit]

        serializer = ProductSalesMetricSerializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # DAILY SALES
    # ==========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="daily-breakdown",
    )
    def daily_breakdown(self, request):
        """
        GET /api/analytics/daily-breakdown/

        Query parameters:

            ?days=30
            ?dark_store_id=<UUID>
        """

        try:
            days = int(
                request.query_params.get(
                    "days",
                    30,
                )
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": "days must be a valid integer."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if days < 1 or days > 365:
            return Response(
                {
                    "detail": "days must be between 1 and 365."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        end_date = timezone.now().date()

        start_date = (
            end_date -
            timedelta(days=days - 1)
        )

        dark_store_id = request.query_params.get(
            "dark_store_id"
        )

        queryset = (
            DailySalesSummary.objects
            .select_related("dark_store")
            .filter(
                date__gte=start_date,
                date__lte=end_date,
            )
        )

        if dark_store_id:
            queryset = queryset.filter(
                dark_store_id=dark_store_id
            )

        queryset = queryset.order_by("-date")

        serializer = DailySalesSummarySerializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # DAILY PRODUCT SALES
    # ==========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="daily-product-sales",
    )
    def daily_product_sales(self, request):
        """
        GET /api/analytics/daily-product-sales/

        Query parameters:

            ?days=30
            ?dark_store_id=<UUID>
            ?product_id=<UUID>
        """

        try:
            days = int(
                request.query_params.get(
                    "days",
                    30,
                )
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": "days must be a valid integer."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if days < 1 or days > 365:
            return Response(
                {
                    "detail": "days must be between 1 and 365."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        end_date = timezone.now().date()

        start_date = (
            end_date -
            timedelta(days=days - 1)
        )

        queryset = (
            DailyProductSales.objects
            .select_related(
                "product",
                "dark_store",
            )
            .filter(
                date__gte=start_date,
                date__lte=end_date,
            )
        )

        dark_store_id = request.query_params.get(
            "dark_store_id"
        )

        product_id = request.query_params.get(
            "product_id"
        )

        if dark_store_id:
            queryset = queryset.filter(
                dark_store_id=dark_store_id
            )

        if product_id:
            queryset = queryset.filter(
                product_id=product_id
            )

        queryset = queryset.order_by(
            "-date",
            "-units_sold",
        )

        serializer = DailyProductSalesSerializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )