from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ("inventory",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "user",
        "dark_store",
        "status",
        "payment_status",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "payment_status", "dark_store", "created_at")
    search_fields = ("order_number", "user__phone_number", "user__email")
    inlines = [OrderItemInline]
    readonly_fields = ("id", "order_number", "created_at", "updated_at")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product_name_en",
        "unit_price",
        "quantity",
        "subtotal",
    )
    raw_id_fields = ("order", "inventory")
