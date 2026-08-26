from django.contrib import admin
from django.utils.html import format_html

from .models import Product, ProductInventory


class ProductInventoryInline(admin.TabularInline):
    """
    Manage dark-store inventory directly from the Product admin page.
    """

    model = ProductInventory

    extra = 0

    fields = (
        "dark_store",
        "stock_qty",
        "store_price",
        "is_available",
    )

    autocomplete_fields = (
        "dark_store",
    )

    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "image_thumbnail",
        "name_en",
        "name_bn",
        "sku",
        "category",
        "brand",
        "unit",
        "base_price",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "category",
        "brand",
    )

    search_fields = (
        "name_en",
        "name_bn",
        "sku",
        "brand",
        "slug",
    )

    prepopulated_fields = {
        "slug": ("name_en",),
    }

    list_editable = (
        "base_price",
        "is_active",
    )

    autocomplete_fields = (
        "category",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        ProductInventoryInline,
    ]

    fieldsets = (
        (
            "General Details",
            {
                "fields": (
                    "name_en",
                    "name_bn",
                    "sku",
                    "slug",
                    "category",
                    "brand",
                    "unit",
                ),
            },
        ),
        (
            "Pricing & Visibility",
            {
                "fields": (
                    "base_price",
                    "is_active",
                ),
            },
        ),
        (
            "Media & Description",
            {
                "fields": (
                    "image",
                    "description",
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

    ordering = (
        "-created_at",
    )

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="45" height="45" '
                'style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url,
            )

        return "No Image"

    image_thumbnail.short_description = "Image"


@admin.register(ProductInventory)
class ProductInventoryAdmin(admin.ModelAdmin):
    """
    Standalone inventory management.

    Useful when staff need to manage stock across
    multiple dark stores.
    """

    list_display = (
        "product",
        "dark_store",
        "stock_qty",
        "store_price",
        "is_available",
        "updated_at",
    )

    list_filter = (
        "dark_store",
        "is_available",
    )

    search_fields = (
        "product__name_en",
        "product__name_bn",
        "product__sku",
        "product__brand",
        "dark_store__name",
    )

    list_editable = (
        "stock_qty",
        "store_price",
        "is_available",
    )

    autocomplete_fields = (
        "product",
        "dark_store",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-updated_at",
    )