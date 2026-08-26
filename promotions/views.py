from django.db.models import Q
from django.utils import timezone

from rest_framework import (
    viewsets,
    permissions,
    status,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Banner, FlashSale
from .serializers import (
    BannerSerializer,
    FlashSaleSerializer,
)


class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public banners.

    Global banner:
        dark_store = NULL

    Dark-store banner:
        dark_store = specific store
    """

    permission_classes = [
        permissions.AllowAny
    ]

    serializer_class = BannerSerializer

    def get_queryset(self):

        now = timezone.now()

        queryset = (
            Banner.objects
            .filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now,
            )
            .select_related("dark_store")
            .order_by(
                "display_order",
                "-created_at",
            )
        )

        # --------------------------------------------------
        # DARK STORE FILTER
        # --------------------------------------------------

        dark_store_id = self.request.query_params.get(
            "dark_store_id"
        )

        if dark_store_id:
            queryset = queryset.filter(
                Q(dark_store_id=dark_store_id)
                | Q(dark_store__isnull=True)
            )

        return queryset


class FlashSaleViewSet(
    viewsets.ReadOnlyModelViewSet
):
    """
    Public Flash Sale API.

    Returns active and upcoming sales.
    """

    permission_classes = [
        permissions.AllowAny
    ]

    serializer_class = FlashSaleSerializer

    def get_queryset(self):

        now = timezone.now()

        queryset = (
            FlashSale.objects
            .filter(
                is_active=True,
                end_time__gte=now,
            )
            .select_related(
                "dark_store",
            )
            .prefetch_related(
                "items__product",
            )
            .order_by(
                "start_time"
            )
        )

        # --------------------------------------------------
        # DARK STORE FILTER
        # --------------------------------------------------

        dark_store_id = self.request.query_params.get(
            "dark_store_id"
        )

        if dark_store_id:
            queryset = queryset.filter(
                Q(dark_store_id=dark_store_id)
                | Q(dark_store__isnull=True)
            )

        return queryset

    @action(
        detail=False,
        methods=["get"],
        url_path="active",
    )
    def active_flash_sale(self, request):

        now = timezone.now()

        queryset = (
            FlashSale.objects
            .filter(
                is_active=True,
                start_time__lte=now,
                end_time__gte=now,
            )
            .select_related(
                "dark_store",
            )
            .prefetch_related(
                "items__product",
            )
        )

        # --------------------------------------------------
        # DARK STORE FILTER
        # --------------------------------------------------

        dark_store_id = self.request.query_params.get(
            "dark_store_id"
        )

        if dark_store_id:
            queryset = queryset.filter(
                Q(dark_store_id=dark_store_id)
                | Q(dark_store__isnull=True)
            )

        active_sale = queryset.first()

        if not active_sale:
            return Response(
                {
                    "message": (
                        "No active flash sales right now."
                    )
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            FlashSaleSerializer(
                active_sale
            ).data,
            status=status.HTTP_200_OK,
        )