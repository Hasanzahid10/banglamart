from django.contrib import admin
from .models import GlobalPlatformConfig, SystemFeatureFlag


# ============================================================
# GLOBAL PLATFORM CONFIG
# ============================================================

@admin.register(GlobalPlatformConfig)
class GlobalPlatformConfigAdmin(admin.ModelAdmin):
    """
    Global platform configuration.

    This should have only ONE record.
    It is intended for SuperAdmin-level configuration.
    """

    list_display = (
        "platform_name",
        "maintenance_mode",
        "base_delivery_fee",
        "free_delivery_threshold",
        "support_phone",
        "support_email",
        "updated_at",
    )

    readonly_fields = (
        "id",
        "updated_at",
    )

    fieldsets = (
        (
            "Platform",
            {
                "fields": (
                    "id",
                    "platform_name",
                    "maintenance_mode",
                )
            },
        ),
        (
            "Delivery & Pricing",
            {
                "fields": (
                    "base_delivery_fee",
                    "free_delivery_threshold",
                )
            },
        ),
        (
            "Customer Support",
            {
                "fields": (
                    "support_phone",
                    "support_email",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        """
        Prevent creating multiple global configurations.
        """

        return not GlobalPlatformConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """
        Never delete the global platform configuration.
        """

        return False


# ============================================================
# SYSTEM FEATURE FLAGS
# ============================================================

@admin.register(SystemFeatureFlag)
class SystemFeatureFlagAdmin(admin.ModelAdmin):
    """
    Manage global platform feature flags.
    """

    list_display = (
        "name",
        "is_enabled",
        "description",
        "updated_at",
    )

    list_filter = (
        "is_enabled",
    )

    search_fields = (
        "name",
        "description",
    )

    readonly_fields = (
        "id",
        "updated_at",
    )

    ordering = (
        "name",
    )

    fieldsets = (
        (
            "Feature",
            {
                "fields": (
                    "id",
                    "name",
                    "is_enabled",
                    "description",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "updated_at",
                )
            },
        ),
    )