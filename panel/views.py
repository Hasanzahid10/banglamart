from django.db import transaction
from django.db.models import Count, Q

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from logistics.models import DarkStore
from products.models import ProductInventory
from .models import Region, RegionAdminProfile
from .serializers import (
    RegionSerializer,
    RegionAdminProfileSerializer,
    AdminDarkStoreSerializer,
    StockAdjustmentSerializer,
)


# ============================================================
# PERMISSION
# ============================================================

class IsRegionalAdminPermission(permissions.BasePermission):
    """
    Only regional ADMIN users can access this panel.

    Each ADMIN must have a RegionAdminProfile with
    an assigned region.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        if getattr(user, "role", None) != "ADMIN":
            return False

        profile = getattr(user, "region_profile", None)

        return (
            profile is not None
            and profile.assigned_region is not None
        )


# ============================================================
# REGIONAL ADMIN PROFILE
# ============================================================

class RegionAdminProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Regional Admin can see only their own profile.
    """

    permission_classes = [IsRegionalAdminPermission]
    serializer_class = RegionAdminProfileSerializer

    def get_queryset(self):
        return RegionAdminProfile.objects.filter(
            user=self.request.user
        ).select_related(
            "user",
            "assigned_region",
        )


# ============================================================
# REGION
# ============================================================

class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Regional Admin can only view their assigned region.

    Region creation/update/deletion is NOT handled here.
    That should belong to your separate Super Admin system.
    """

    permission_classes = [IsRegionalAdminPermission]
    serializer_class = RegionSerializer

    def get_queryset(self):
        profile = self.request.user.region_profile

        return Region.objects.filter(
            id=profile.assigned_region_id,
            is_active=True,
        )


# ============================================================
# DARK STORE
# ============================================================

class AdminDarkStoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Regional Admin can manage/view DarkStores belonging
    to their assigned region.
    """

    permission_classes = [IsRegionalAdminPermission]
    serializer_class = AdminDarkStoreSerializer

    def get_queryset(self):
        region = self.request.user.region_profile.assigned_region

        return (
            DarkStore.objects
            .filter(
                region=region,
            )
            .annotate(
                total_orders=Count("orders"),
                active_riders=Count(
                    "assigned_riders",
                    filter=Q(
                        assigned_riders__is_on_duty=True,
                        assigned_riders__is_available=True,
                    ),
                ),
            )
            .order_by("name")
        )

    # ========================================================
    # TOGGLE DARK STORE
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="toggle-active",
    )
    def toggle_active_status(self, request, pk=None):

        dark_store = self.get_object()

        dark_store.is_active = not dark_store.is_active

        dark_store.save(
            update_fields=["is_active"]
        )

        return Response(
            {
                "message": (
                    f"DarkStore '{dark_store.name}' is now "
                    f"{'Active' if dark_store.is_active else 'Inactive'}."
                ),
                "dark_store_id": str(dark_store.id),
                "is_active": dark_store.is_active,
            },
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # ADJUST STOCK
    # ========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="adjust-stock",
    )
    def adjust_stock(self, request):

        serializer = StockAdjustmentSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        product_id = serializer.validated_data[
            "product_id"
        ]

        dark_store_id = serializer.validated_data[
            "dark_store_id"
        ]

        quantity = serializer.validated_data[
            "available_quantity"
        ]

        # ----------------------------------------------------
        # Verify DarkStore belongs to Admin's region
        # ----------------------------------------------------

        region = request.user.region_profile.assigned_region

        try:
            dark_store = DarkStore.objects.get(
                id=dark_store_id,
                region=region,
            )
        except DarkStore.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "DarkStore does not belong to "
                        "your assigned region."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ----------------------------------------------------
        # Stock update
        # ----------------------------------------------------

        with transaction.atomic():

            stock, created = (
                ProductInventory.objects.select_for_update()
                .get_or_create(
                    dark_store=dark_store,
                    product_id=product_id,
                    defaults={
                        "stock_qty": quantity,
                    },
                )
            )

            if not created:
                stock.stock_qty = quantity

                stock.save(
                    update_fields=[
                        "stock_qty",
                    ]
                )

        return Response(
            {
                "message": "Stock adjusted successfully.",
                "dark_store_id": str(dark_store.id),
                "dark_store_name": dark_store.name,
                "product_id": product_id,
                "available_quantity": stock.stock_qty,
            },
            status=status.HTTP_200_OK,
        )