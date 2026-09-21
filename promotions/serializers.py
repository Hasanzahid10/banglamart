from rest_framework import serializers

from products.models import Product
from .models import Banner, FlashSale, FlashSaleItem


import datetime
from django.utils import timezone

class BannerSerializer(serializers.ModelSerializer):

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    start_date = serializers.DateTimeField(required=False, default=timezone.now)
    end_date = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = Banner

        fields = (
            "id",
            "title",
            "subtitle",
            "image",

            "target_type",
            "target_id",

            "dark_store",
            "dark_store_name",

            "display_order",
            "is_active",

            "start_date",
            "end_date",
            "is_running_now",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "dark_store_name",
            "is_running_now",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        if not validated_data.get("end_date"):
            start = validated_data.get("start_date") or timezone.now()
            validated_data["end_date"] = start + datetime.timedelta(days=365)
        return super().create(validated_data)


class FlashSaleItemSerializer(serializers.ModelSerializer):

    product_id = serializers.IntegerField(
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

    original_price = serializers.DecimalField(
        source="product.base_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    product_image = serializers.ImageField(
        source="product.image",
        read_only=True,
    )

    remaining_stock = serializers.IntegerField(
        read_only=True,
    )

    is_sold_out = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = FlashSaleItem

        fields = (
            "id",
            "product_id",
            "product_name",
            "product_name_bn",
            "original_price",
            "discount_price",
            "product_image",

            "stock_allocated",
            "stock_sold",
            "remaining_stock",
            "is_sold_out",

            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "product_id",
            "product_name",
            "product_name_bn",
            "original_price",
            "product_image",
            "stock_sold",
            "remaining_stock",
            "is_sold_out",
            "created_at",
            "updated_at",
        )


class FlashSaleSerializer(serializers.ModelSerializer):

    items = FlashSaleItemSerializer(
        many=True,
        read_only=True,
    )

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    is_running = serializers.BooleanField(
        source="is_running_now",
        read_only=True,
    )

    class Meta:
        model = FlashSale

        fields = (
            "id",
            "title",
            "banner_image",

            "dark_store",
            "dark_store_name",

            "start_time",
            "end_time",

            "is_active",
            "is_running",

            "items",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "dark_store_name",
            "is_running",
            "created_at",
            "updated_at",
        )