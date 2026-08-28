from decimal import Decimal
from rest_framework import serializers

from products.models import Product, ProductInventory

from .models import Wishlist, WishlistItem


# ============================================================
# WISHLIST ITEM
# ============================================================

class WishlistItemSerializer(serializers.ModelSerializer):

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

    product_image = serializers.ImageField(
        source="product.image",
        read_only=True,
    )

    is_in_stock = serializers.SerializerMethodField()

    current_price = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem

        fields = (
            "id",
            "product_id",
            "product_name",
            "product_name_bn",
            "product_image",
            "current_price",
            "is_in_stock",
            "created_at",
        )

        read_only_fields = (
            "id",
            "product_id",
            "product_name",
            "product_name_bn",
            "product_image",
            "current_price",
            "is_in_stock",
            "created_at",
        )

    # --------------------------------------------------------
    # CURRENT DARK STORE
    # --------------------------------------------------------

    def _get_dark_store(self):

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        # Customer's current cart determines selected store.
        cart = getattr(
            request.user,
            "cart",
            None,
        )

        if cart:
            return cart.dark_store

        return None

    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    def get_is_in_stock(self, obj) -> bool:

        dark_store = self._get_dark_store()

        if not dark_store:
            return False

        return ProductInventory.objects.filter(
            product=obj.product,
            dark_store=dark_store,
            is_available=True,
            stock_qty__gt=0,
        ).exists()

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    def get_current_price(self, obj) -> Decimal | None:

        dark_store = self._get_dark_store()

        if not dark_store:
            return None

        inventory = (
            ProductInventory.objects
            .filter(
                product=obj.product,
                dark_store=dark_store,
                is_available=True,
            )
            .first()
        )

        if not inventory:
            return None

        return inventory.selling_price


# ============================================================
# TOGGLE WISHLIST
# ============================================================

class ToggleWishlistSerializer(serializers.Serializer):

    product_id = serializers.IntegerField()

    def validate_product_id(self, value):

        if not Product.objects.filter(
            id=value,
            is_active=True,
        ).exists():

            raise serializers.ValidationError(
                "Product not found or unavailable."
            )

        return value


# ============================================================
# WISHLIST
# ============================================================

class WishlistSerializer(serializers.ModelSerializer):

    items = WishlistItemSerializer(
        many=True,
        read_only=True,
    )

    total_items = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = Wishlist

        fields = (
            "id",
            "total_items",
            "items",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "total_items",
            "items",
            "updated_at",
        )