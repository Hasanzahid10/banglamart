from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    GlobalPlatformConfig,
    SystemFeatureFlag,
)

User = get_user_model()


# ============================================================
# GLOBAL PLATFORM CONFIG
# ============================================================

class GlobalPlatformConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = GlobalPlatformConfig

        fields = (
            "id",
            "platform_name",
            "maintenance_mode",
            "base_delivery_fee",
            "free_delivery_threshold",
            "support_phone",
            "support_email",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "updated_at",
        )


# ============================================================
# FEATURE FLAGS
# ============================================================

class SystemFeatureFlagSerializer(serializers.ModelSerializer):

    class Meta:
        model = SystemFeatureFlag

        fields = (
            "id",
            "name",
            "is_enabled",
            "description",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "updated_at",
        )


# ============================================================
# USER ROLE MANAGEMENT
# ============================================================

class UserRoleUpdateSerializer(serializers.Serializer):

    user_id = serializers.IntegerField()

    role = serializers.ChoiceField(
        choices=[
            "CUSTOMER",
            "RIDER",
            "WAREHOUSE_STAFF",
            "ADMIN",
        ]
    )

    is_staff = serializers.BooleanField(
        required=False,
    )

    def validate_user_id(self, value):

        if not User.objects.filter(
            id=value
        ).exists():

            raise serializers.ValidationError(
                "Target user not found."
            )

        return value

    def validate(self, attrs):

        user = User.objects.get(
            id=attrs["user_id"]
        )

        # Never allow changing the existing
        # Super Admin through this serializer.
        if user.is_superuser:
            raise serializers.ValidationError(
                {
                    "user_id": (
                        "Super Admin accounts cannot be "
                        "modified through this endpoint."
                    )
                }
            )

        return attrs