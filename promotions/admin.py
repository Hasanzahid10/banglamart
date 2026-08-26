from django.contrib import admin
from .models import Banner, FlashSale, FlashSaleItem


class FlashSaleItemInline(admin.TabularInline):
    model = FlashSaleItem
    extra = 1
    raw_id_fields = ("product",)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "target_type",
        "target_id",
        "dark_store",
        "display_order",
        "is_active",
        "start_date",
        "end_date",
    )

    list_filter = (
        "target_type",
        "is_active",
        "dark_store",
        "start_date",
        "end_date",
    )

    search_fields = (
        "title",
        "subtitle",
        "target_id",
    )

    ordering = (
        "display_order",
        "-created_at",
    )


@admin.register(FlashSale)
class FlashSaleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "dark_store",
        "start_time",
        "end_time",
        "is_active",
    )

    list_filter = (
        "is_active",
        "dark_store",
        "start_time",
        "end_time",
    )

    search_fields = (
        "title",
    )

    inlines = [
        FlashSaleItemInline,
    ]


@admin.register(FlashSaleItem)
class FlashSaleItemAdmin(admin.ModelAdmin):
    list_display = (
        "flash_sale",
        "product",
        "discount_price",
        "stock_allocated",
        "stock_sold",
        "is_active",
    )

    list_filter = (
        "is_active",
        "flash_sale__dark_store",
    )

    search_fields = (
        "product__name",
        "flash_sale__title",
    )

    raw_id_fields = (
        "product",
        "flash_sale",
    )
