from rest_framework import serializers

from .models import (
    DailySalesSummary,
    ProductSalesMetric,
    DailyProductSales,
)


class DailySalesSummarySerializer(serializers.ModelSerializer):
    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    dark_store_code = serializers.CharField(
        source="dark_store.code",
        read_only=True,
    )

    class Meta:
        model = DailySalesSummary

        fields = (
            "id",
            "date",
            "dark_store_name",
            "dark_store_code",
            "total_orders",
            "completed_orders",
            "cancelled_orders",
            "total_revenue",
            "delivery_fees_collected",
            "discounts_given",
            "net_revenue",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields


class ProductSalesMetricSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(
        source="product.id",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="product.name_en",
        read_only=True,
    )

    product_name_bn = serializers.CharField(
        source="product.name_bn",
        read_only=True,
    )

    product_sku = serializers.CharField(
        source="product.sku",
        read_only=True,
    )

    product_price = serializers.DecimalField(
        source="product.base_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = ProductSalesMetric

        fields = (
            "product_id",
            "product_name",
            "product_name_bn",
            "product_sku",
            "product_price",
            "total_units_sold",
            "total_orders",
            "total_revenue_generated",
            "last_sold_at",
            "updated_at",
        )

        read_only_fields = fields


class DailyProductSalesSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(
        source="product.id",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="product.name_en",
        read_only=True,
    )

    product_name_bn = serializers.CharField(
        source="product.name_bn",
        read_only=True,
    )

    product_sku = serializers.CharField(
        source="product.sku",
        read_only=True,
    )

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    dark_store_code = serializers.CharField(
        source="dark_store.code",
        read_only=True,
    )

    class Meta:
        model = DailyProductSales

        fields = (
            "id",
            "date",
            "dark_store_name",
            "dark_store_code",
            "product_id",
            "product_name",
            "product_name_bn",
            "product_sku",
            "units_sold",
            "revenue",
            "orders_count",
        )

        read_only_fields = fields


class DashboardOverviewSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    total_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()

    total_gross_revenue = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    total_delivery_fees = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    total_discounts = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    total_net_revenue = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    average_order_value = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )