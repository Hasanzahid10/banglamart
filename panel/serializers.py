from rest_framework import serializers

from logistics.models import DarkStore
from products.models import ProductInventory

from .models import Region, RegionAdminProfile


# ============================================================
# REGION
# ============================================================

class RegionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Region
        fields = (
            "id",
            "name",
            "code",
            "city",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


# ============================================================
# REGIONAL ADMIN
# ============================================================

class RegionAdminProfileSerializer(serializers.ModelSerializer):

    user_phone = serializers.CharField(
        source="user.phone_number",
        read_only=True,
    )

    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    region_name = serializers.CharField(
        source="assigned_region.name",
        read_only=True,
    )

    region_code = serializers.CharField(
        source="assigned_region.code",
        read_only=True,
    )

    class Meta:
        model = RegionAdminProfile

        fields = (
            "id",
            "user",
            "user_phone",
            "user_email",
            "assigned_region",
            "region_name",
            "region_code",
            "can_manage_stock",
            "can_assign_riders",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "user_phone",
            "user_email",
            "region_name",
            "region_code",
            "created_at",
            "updated_at",
        )


# ============================================================
# DARK STORE
# ============================================================

class AdminDarkStoreSerializer(serializers.ModelSerializer):

    total_orders = serializers.IntegerField(
        read_only=True,
    )

    active_riders = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = DarkStore

        fields = (
            "id",
            "name",
            "code",
            "address",
            "contact_number",
            "is_active",
            "total_orders",
            "active_riders",
            "created_at",
        )

        read_only_fields = (
            "id",
            "total_orders",
            "active_riders",
            "created_at",
        )


# ============================================================
# STOCK
# ============================================================

class StockAdjustmentSerializer(serializers.Serializer):

    product_id = serializers.IntegerField()

    dark_store_id = serializers.UUIDField()

    available_quantity = serializers.IntegerField(
        min_value=0,
    )