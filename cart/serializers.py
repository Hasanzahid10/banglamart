from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from products.models import ProductInventory

from .models import Cart, CartItem


# ============================================================
# CART ITEM
# ============================================================

class CartItemSerializer(serializers.ModelSerializer):

    product_id = serializers.ReadOnlyField(
        source="inventory.product.id"
    )

    product_name = serializers.ReadOnlyField(
        source="inventory.product.name_en"
    )

    product_name_bn = serializers.ReadOnlyField(
        source="inventory.product.name_bn"
    )

    product_image = serializers.ImageField(
        source="inventory.product.image",
        read_only=True,
    )

    unit = serializers.ReadOnlyField(
        source="inventory.product.unit"
    )

    brand = serializers.ReadOnlyField(
        source="inventory.product.brand"
    )

    sku = serializers.ReadOnlyField(
        source="inventory.product.sku"
    )

    dark_store_id = serializers.ReadOnlyField(
        source="inventory.dark_store.id"
    )

    dark_store_name = serializers.ReadOnlyField(
        source="inventory.dark_store.name"
    )

    unit_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = CartItem

        fields = (
            "id",

            # Product
            "product_id",
            "product_name",
            "product_name_bn",
            "product_image",
            "sku",
            "brand",
            "unit",

            # Store
            "dark_store_id",
            "dark_store_name",

            # Cart
            "quantity",
            "unit_price",
            "subtotal",
            "in_stock",
        )

        read_only_fields = fields


# ============================================================
# ADD TO CART
# ============================================================

class AddToCartSerializer(serializers.Serializer):
    """
    Add a product to the customer's cart.

    IMPORTANT:

    Product is global.

    But the cart must contain ProductInventory,
    because inventory belongs to a specific DarkStore.

    Example:

        Product:
            Rice 5kg

        DarkStore:
            Rangpur Store #1

        ProductInventory:
            Rice 5kg + Rangpur Store #1
    """

    product_id = serializers.IntegerField()

    quantity = serializers.IntegerField(
        min_value=1,
        default=1,
    )

    def validate(self, attrs):

        request = self.context["request"]
        user = request.user

        product_id = attrs["product_id"]

        # ----------------------------------------------------
        # Get customer's cart
        # ----------------------------------------------------

        try:
            cart = (
                Cart.objects
                .select_related("dark_store")
                .get(user=user)
            )

        except Cart.DoesNotExist:

            raise serializers.ValidationError({
                "cart": (
                    "Cart not found. "
                    "Please create/select a delivery "
                    "location first."
                )
            })

        # ----------------------------------------------------
        # DarkStore is required
        # ----------------------------------------------------

        if not cart.dark_store:

            raise serializers.ValidationError({
                "dark_store": (
                    "No DarkStore has been selected "
                    "for your cart. "
                    "Please select your delivery location "
                    "first."
                )
            })

        # ----------------------------------------------------
        # Find inventory for this DarkStore
        # ----------------------------------------------------

        try:

            inventory = (
                ProductInventory.objects
                .select_related(
                    "product",
                    "dark_store",
                )
                .get(
                    product_id=product_id,
                    dark_store=cart.dark_store,
                )
            )

        except ProductInventory.DoesNotExist:

            raise serializers.ValidationError({
                "product_id": (
                    "This product is not available "
                    "at your selected DarkStore."
                )
            })

        # ----------------------------------------------------
        # Product active?
        # ----------------------------------------------------

        if not inventory.product.is_active:

            raise serializers.ValidationError({
                "product_id": (
                    "This product is currently unavailable."
                )
            })

        # ----------------------------------------------------
        # Inventory available?
        # ----------------------------------------------------

        if not inventory.is_available:

            raise serializers.ValidationError({
                "product_id": (
                    "This product is currently unavailable "
                    "at your selected DarkStore."
                )
            })

        # ----------------------------------------------------
        # Stock validation
        # ----------------------------------------------------

        if inventory.stock_qty < attrs["quantity"]:

            raise serializers.ValidationError({
                "quantity": (
                    f"Only {inventory.stock_qty} "
                    f"unit(s) available."
                )
            })

        # ----------------------------------------------------
        # Store resolved inventory
        # ----------------------------------------------------

        attrs["cart"] = cart
        attrs["inventory"] = inventory

        return attrs

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    @transaction.atomic
    def create(self, validated_data):

        cart = validated_data["cart"]
        inventory = validated_data["inventory"]
        quantity = validated_data["quantity"]

        # ----------------------------------------------------
        # Lock inventory
        # ----------------------------------------------------

        inventory = (
            ProductInventory.objects
            .select_for_update()
            .select_related(
                "product",
                "dark_store",
            )
            .get(
                id=inventory.id
            )
        )

        # ----------------------------------------------------
        # Re-check stock
        # ----------------------------------------------------

        if not inventory.is_available:

            raise serializers.ValidationError({
                "product_id": (
                    "This product is no longer available."
                )
            })

        # ----------------------------------------------------
        # Existing cart item
        # ----------------------------------------------------

        cart_item = (
            CartItem.objects
            .select_for_update()
            .filter(
                cart=cart,
                inventory=inventory,
            )
            .first()
        )

        if cart_item:

            new_quantity = (
                cart_item.quantity +
                quantity
            )

            if inventory.stock_qty < new_quantity:

                raise serializers.ValidationError({
                    "quantity": (
                        f"Only {inventory.stock_qty} "
                        f"unit(s) available. "
                        f"You already have "
                        f"{cart_item.quantity} "
                        f"in your cart."
                    )
                })

            cart_item.quantity = new_quantity

        else:

            if inventory.stock_qty < quantity:

                raise serializers.ValidationError({
                    "quantity": (
                        f"Only {inventory.stock_qty} "
                        f"unit(s) available."
                    )
                })

            cart_item = CartItem(
                cart=cart,
                inventory=inventory,
                quantity=quantity,
            )

        # ----------------------------------------------------
        # Capture current store selling price
        # ----------------------------------------------------

        cart_item.unit_price = (
            inventory.selling_price
        )

        cart_item.save()

        # Touch cart updated_at
        cart.save(
            update_fields=[
                "updated_at"
            ]
        )

        return cart_item


# ============================================================
# UPDATE CART ITEM
# ============================================================

class UpdateCartItemSerializer(serializers.Serializer):

    quantity = serializers.IntegerField(
        min_value=0,
        help_text=(
            "Set to 0 to remove the item "
            "from the cart."
        ),
    )


# ============================================================
# CART
# ============================================================

class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    total_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    total_items = serializers.IntegerField(
        read_only=True,
    )

    total_unique_items = serializers.SerializerMethodField()

    dark_store_name = serializers.ReadOnlyField(
        source="dark_store.name"
    )

    class Meta:
        model = Cart

        fields = (
            "id",

            # Store
            "dark_store",
            "dark_store_name",

            # Items
            "items",

            # Totals
            "total_items",
            "total_unique_items",
            "total_price",

            "updated_at",
        )

        read_only_fields = fields

    def get_total_unique_items(self, obj) -> int:

        return obj.items.count()