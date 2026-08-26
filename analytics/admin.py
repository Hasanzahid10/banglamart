from django.contrib import admin

from .models import (
    DailySalesSummary,
    ProductSalesMetric,
    DailyProductSales,
)


@admin.register(DailySalesSummary)
class DailySalesSummaryAdmin(admin.ModelAdmin):

    list_display = (
        "date",
        "dark_store",
        "total_orders",
        "completed_orders",
        "cancelled_orders",
        "total_revenue",
        "delivery_fees_collected",
        "discounts_given",
        "net_revenue",
    )

    list_filter = (
        "dark_store",
        "date",
    )

    search_fields = (
        "dark_store__name",
        "dark_store__code",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-date",
        "dark_store",
    )

    list_select_related = (
        "dark_store",
    )


@admin.register(ProductSalesMetric)
class ProductSalesMetricAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "total_units_sold",
        "total_orders",
        "total_revenue_generated",
        "last_sold_at",
        "updated_at",
    )

    list_filter = (
        "last_sold_at",
    )

    search_fields = (
        "product__name_en",
        "product__name_bn",
        "product__sku",
    )

    readonly_fields = (
        "id",
        "updated_at",
    )

    ordering = (
        "-total_units_sold",
    )

    list_select_related = (
        "product",
    )


@admin.register(DailyProductSales)
class DailyProductSalesAdmin(admin.ModelAdmin):

    list_display = (
        "date",
        "dark_store",
        "product",
        "units_sold",
        "orders_count",
        "revenue",
    )

    list_filter = (
        "dark_store",
        "date",
    )

    search_fields = (
        "dark_store__name",
        "dark_store__code",
        "product__name_en",
        "product__name_bn",
        "product__sku",
    )

    readonly_fields = (
        "id",
    )

    ordering = (
        "-date",
        "-units_sold",
    )

    list_select_related = (
        "dark_store",
        "product",
    )