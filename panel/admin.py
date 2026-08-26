from django.contrib import admin

from .models import Region, RegionAdminProfile


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "code",
        "city",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "city",
    )

    search_fields = (
        "name",
        "code",
        "city",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "name",
    )


@admin.register(RegionAdminProfile)
class RegionAdminProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "assigned_region",
        "can_manage_stock",
        "can_assign_riders",
        "created_at",
    )

    list_filter = (
        "assigned_region",
        "can_manage_stock",
        "can_assign_riders",
    )

    search_fields = (
        "user__phone_number",
        "user__email",
        "user__first_name",
        "user__last_name",
        "assigned_region__name",
        "assigned_region__code",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "user",
        "assigned_region",
    )

    ordering = (
        "assigned_region__name",
        "user__email",
    )