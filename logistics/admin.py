from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import DarkStore, DeliveryZone, DeliverySlot, DeliveryOrder


class DeliverySlotInline(admin.TabularInline):
    model = DeliverySlot

    extra = 0

    fields = (
        "start_time",
        "end_time",
        "max_orders",
        "is_active",
    )

    ordering = (
        "start_time",
    )


@admin.register(DarkStore)
class DarkStoreAdmin(GISModelAdmin):

    list_display = (
        "name",
        "code",
        "contact_number",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
        "address",
        "contact_number",
    )

    list_filter = (
        "is_active",
    )

    list_editable = (
        "is_active",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Dark Store Information",
            {
                "fields": (
                    "name",
                    "code",
                    "address",
                    "contact_number",
                ),
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "location",
                ),
                "description": (
                    "Set the exact warehouse location "
                    "using the map."
                ),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                ),
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    inlines = [
        DeliverySlotInline,
    ]

    ordering = (
        "name",
    )


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(GISModelAdmin):

    list_display = (
        "name",
        "dark_store",
        "is_active",
    )

    list_filter = (
        "is_active",
        "dark_store",
    )

    search_fields = (
        "name",
        "dark_store__name",
        "dark_store__code",
    )

    list_editable = (
        "is_active",
    )

    autocomplete_fields = (
        "dark_store",
    )

    fieldsets = (
        (
            "Delivery Zone",
            {
                "fields": (
                    "dark_store",
                    "name",
                    "boundary",
                    "is_active",
                ),
            },
        ),
    )

    ordering = (
        "dark_store",
        "name",
    )


@admin.register(DeliverySlot)
class DeliverySlotAdmin(admin.ModelAdmin):

    list_display = (
        "dark_store",
        "start_time",
        "end_time",
        "max_orders",
        "is_active",
    )

    list_filter = (
        "dark_store",
        "is_active",
    )

    search_fields = (
        "dark_store__name",
        "dark_store__code",
    )

    list_editable = (
        "max_orders",
        "is_active",
    )

    autocomplete_fields = (
        "dark_store",
    )

    ordering = (
        "dark_store",
        "start_time",
    )


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(GISModelAdmin):

    list_display = (
        "tracking_number",
        "user",
        "dark_store",
        "rider",
        "status",
        "created_at",
    )

    search_fields = (
        "tracking_number",
        "recipient_name",
        "recipient_phone",
    )

    list_filter = (
        "status",
        "dark_store",
        "created_at",
    )

    readonly_fields = (
        "tracking_number",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )