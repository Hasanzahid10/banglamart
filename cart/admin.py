from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ("inventory", "quantity", "unit_price", "get_subtotal")
    readonly_fields = ("get_subtotal",)

    @admin.display(description="Subtotal")
    def get_subtotal(self, obj):
        return obj.subtotal if obj.pk else 0.00


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "dark_store",
        "get_total_items",
        "get_total_price",
        "updated_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "get_total_items",
        "get_total_price",
    )
    inlines = [CartItemInline]
    search_fields = (
        "id",
        "user__phone_number",
        "user__email",
        "dark_store__name",
        "dark_store__code",
    )
    list_filter = ("created_at", "updated_at", "dark_store")

    @admin.display(description="Total Items")
    def get_total_items(self, obj):
        return obj.total_items

    @admin.display(description="Total Price")
    def get_total_price(self, obj):
        return f"${obj.total_price:.2f}"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cart",
        "product",
        "quantity",
        "unit_price",
        "get_subtotal",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "get_subtotal",
    )
    search_fields = (
        "cart__id",
        "cart__user__phone_number",
        "product__name",
    )
    list_filter = ("created_at", "updated_at")

    @admin.display(description="Subtotal")
    def get_subtotal(self, obj):
        return f"${obj.subtotal:.2f}"