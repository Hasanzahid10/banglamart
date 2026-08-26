from django.contrib import admin

from .models import Wishlist, WishlistItem


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0

    fields = (
        "product",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "get_total_items",
        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "get_total_items",
    )

    search_fields = (
        "user__email",
        "user__phone_number",
        "user__first_name",
        "user__last_name",
    )

    inlines = [
        WishlistItemInline,
    ]

    @admin.display(
        description="Total Items"
    )
    def get_total_items(self, obj):
        return obj.total_items


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "wishlist",
        "get_user",
        "product",
        "created_at",
    )

    search_fields = (
        "wishlist__user__email",
        "wishlist__user__phone_number",
        "product__name_en",
        "product__name_bn",
        "product__sku",
    )

    list_filter = (
        "created_at",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

    @admin.display(
        description="Customer"
    )
    def get_user(self, obj):
        return obj.wishlist.user