from django.contrib import admin
from .models import UserProfile, Address


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "get_phone_number",
        "get_email",
        "get_full_name",
        "total_orders",
        "loyalty_points",
        "created_at",
    )
    search_fields = (
        "user__phone_number",
        "user__email",
        "user__first_name",
        "user__last_name",
        "alternate_phone",
    )
    list_filter = (
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "total_orders",
        "loyalty_points",
        "created_at",
        "updated_at",
    )

    # Custom callable fields to pull data from the related User model
    @admin.display(description="Phone Number", ordering="user__phone_number")
    def get_phone_number(self, obj):
        return obj.user.phone_number

    @admin.display(description="Email", ordering="user__email")
    def get_email(self, obj):
        return obj.user.email or "-"

    @admin.display(description="Full Name")
    def get_full_name(self, obj):
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full_name if full_name else "-"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "title",
        "address_type",
        "street_address",
        "area",
        "city",
        "is_default",
    )
    list_filter = (
        "address_type",
        "is_default",
        "city",
        "created_at",
    )
    search_fields = (
        "user__phone_number",
        "user__email",
        "title",
        "street_address",
        "area",
        "city",
    )
    list_editable = (
        "is_default",
    )
    readonly_fields = (
        "created_at",
    )