from rest_framework import serializers

from .models import Product, ProductInventory


# =========================================================
# PRODUCT INVENTORY SERIALIZER
# =========================================================

class ProductInventorySerializer(
    serializers.ModelSerializer
):

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    service_area_name = serializers.CharField(
        source="dark_store.service_area.name",
        read_only=True,
    )

    selling_price = serializers.SerializerMethodField()

    in_stock = serializers.SerializerMethodField()

    is_low_stock = serializers.SerializerMethodField()

    class Meta:

        model = ProductInventory

        fields = [
            "dark_store",
            "dark_store_name",
            "service_area_name",

            "stock_qty",
            "low_stock_threshold",

            "store_price",
            "selling_price",

            "is_available",
            "in_stock",
            "is_low_stock",

            "updated_at",
        ]

        read_only_fields = [
            "dark_store",
            "dark_store_name",
            "service_area_name",
            "selling_price",
            "in_stock",
            "is_low_stock",
            "updated_at",
        ]

    # =====================================================
    # SELLING PRICE
    # =====================================================

    def get_selling_price(self, obj):

        return obj.selling_price

    # =====================================================
    # STOCK
    # =====================================================

    def get_in_stock(self, obj):

        return obj.in_stock

    # =====================================================
    # LOW STOCK
    # =====================================================

    def get_is_low_stock(self, obj):

        return obj.is_low_stock


# =========================================================
# PRODUCT SERIALIZER
# =========================================================

class ProductSerializer(
    serializers.ModelSerializer
):

    category_name = serializers.CharField(
        source="category.name_en",
        read_only=True,
    )

    inventories = ProductInventorySerializer(
        many=True,
        read_only=True,
    )

    # -----------------------------------------------------
    # PRODUCT PRICE
    # -----------------------------------------------------

    selling_price = serializers.SerializerMethodField()

    class Meta:

        model = Product

        fields = [
            "id",

            # Category
            "category",
            "category_name",

            # Product information
            "name_en",
            "name_bn",
            "slug",
            "sku",
            "brand",
            "unit",

            # Price
            "base_price",
            "selling_price",

            # Media
            "image",
            "description",

            # Status
            "is_active",

            # Store inventory
            "inventories",

            # Timestamps
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "selling_price",
            "created_at",
            "updated_at",
        ]

    # =====================================================
    # SELLING PRICE
    # =====================================================

    def get_selling_price(self, obj):

        """
        Return the price for the currently selected
        dark store.

        If no dark store has been selected, fall back
        to the global base price.
        """

        dark_store = self.context.get(
            "dark_store"
        )
        dark_store_id = None
        if dark_store:
            dark_store_id = dark_store.id
        else:
            request = self.context.get("request")
            if request:
                dark_store_id = request.query_params.get("dark_store_id")

        if not dark_store_id:
            return obj.base_price

        inventory = next(
            (
                inventory
                for inventory in obj.inventories.all()
                if str(inventory.dark_store_id)
                == str(dark_store_id)
            ),
            None,
        )

        if not inventory:
            return obj.base_price

        return inventory.selling_price


# =========================================================
# CUSTOMER PRODUCT SERIALIZER
# =========================================================

class CustomerProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name_en",
        read_only=True,
    )
    selling_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    stock_qty = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "category_name",
            "name_en",
            "name_bn",
            "slug",
            "sku",
            "brand",
            "unit",
            "base_price",
            "selling_price",
            "image",
            "description",
            "in_stock",
            "stock_qty",
        ]
        read_only_fields = fields

    def _get_local_inventory(self, obj):
        dark_store = self.context.get("dark_store")
        dark_store_id = None
        if dark_store:
            dark_store_id = dark_store.id
        else:
            request = self.context.get("request")
            if request:
                dark_store_id = request.query_params.get("dark_store_id")

        if dark_store_id:
            return next(
                (
                    inventory
                    for inventory in obj.inventories.all()
                    if str(inventory.dark_store_id) == str(dark_store_id)
                ),
                None,
            )
        return obj.inventories.first()

    def get_selling_price(self, obj):
        inventory = self._get_local_inventory(obj)
        if inventory:
            return inventory.selling_price
        return obj.base_price

    def get_in_stock(self, obj):
        inventory = self._get_local_inventory(obj)
        if inventory:
            return inventory.in_stock
        return False

    def get_stock_qty(self, obj):
        inventory = self._get_local_inventory(obj)
        if inventory:
            return inventory.stock_qty
        return 0