from django.contrib import admin

from .models import RiderProfile, DeliveryTask


@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for rider profiles.

    RiderProfile belongs to the rider app, while DarkStore
    is managed by the logistics app.
    """

    list_display = (
        "user",
        "dark_store",
        "vehicle_type",
        "is_available",
        "is_on_duty",
        "last_location_update",
        "created_at",
    )

    list_filter = (
        "is_available",
        "is_on_duty",
        "vehicle_type",
        "dark_store",
    )

    search_fields = (
        "user__phone_number",
        "user__email",
        "user__first_name",
        "user__last_name",
        "dark_store__name",
        "dark_store__code",
        "vehicle_type",
        "license_number",
    )

    autocomplete_fields = (
        "user",
        "dark_store",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_location_update",
    )

    fieldsets = (
        (
            "Rider",
            {
                "fields": (
                    "user",
                    "dark_store",
                )
            },
        ),
        (
            "Vehicle Information",
            {
                "fields": (
                    "vehicle_type",
                    "license_number",
                )
            },
        ),
        (
            "Duty Status",
            {
                "fields": (
                    "is_available",
                    "is_on_duty",
                )
            },
        ),
        (
            "Live Location",
            {
                "fields": (
                    "last_location_update",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(DeliveryTask)
class DeliveryTaskAdmin(admin.ModelAdmin):
    """
    Admin interface for rider delivery tasks.
    """

    list_display = (
        "id",
        "delivery_order",
        "rider",
        "status",
        "assigned_at",
        "accepted_at",
        "picked_up_at",
        "delivered_at",
    )

    list_filter = (
        "status",
        "assigned_at",
        "accepted_at",
        "picked_up_at",
        "delivered_at",
    )

    search_fields = (
        "delivery_order__tracking_number",
        "rider__phone_number",
        "rider__email",
        "rider__first_name",
        "rider__last_name",
    )

    autocomplete_fields = (
        "delivery_order",
        "rider",
    )

    readonly_fields = (
        "id",
        "assigned_at",
        "accepted_at",
        "picked_up_at",
        "delivered_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Delivery Assignment",
            {
                "fields": (
                    "id",
                    "delivery_order",
                    "rider",
                )
            },
        ),
        (
            "Delivery Status",
            {
                "fields": (
                    "status",
                    "failure_reason",
                )
            },
        ),
        (
            "Delivery Timeline",
            {
                "fields": (
                    "assigned_at",
                    "accepted_at",
                    "picked_up_at",
                    "delivered_at",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )