from django.core.exceptions import ValidationError
from django.db import transaction

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from products.models import ProductInventory

from .models import Cart, CartItem
from .serializers import (
    AddToCartSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)


class CartViewSet(viewsets.ViewSet):
    """
    Customer cart management.

    Cart belongs to one DarkStore.

    Product is global.

    Inventory is resolved using:

        cart.dark_store + product
    """

    permission_classes = [
        permissions.IsAuthenticated
    ]

    # =========================================================
    # GET /api/cart/
    # =========================================================

    def _get_or_create_cart(self, user):

        cart, _ = (
            Cart.objects
            .select_related("dark_store")
            .prefetch_related(
                "items__product"
            )
            .get_or_create(
                user=user
            )
        )

        return cart

    # =========================================================
    # LIST CART
    # =========================================================

    def list(self, request):

        cart = self._get_or_create_cart(
            request.user
        )

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # ADD ITEM
    # =========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="add",
    )
    @transaction.atomic
    def add_item(self, request):

        serializer = AddToCartSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        product_id = (
            serializer.validated_data["product_id"]
        )

        quantity = (
            serializer.validated_data["quantity"]
        )

        cart = self._get_or_create_cart(
            request.user
        )

        # -----------------------------------------------------
        # CART MUST HAVE DARK STORE
        # -----------------------------------------------------

        if not cart.dark_store:

            return Response(
                {
                    "error": (
                        "No DarkStore is selected "
                        "for your cart. Please select "
                        "your delivery location first."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # FIND INVENTORY
        # -----------------------------------------------------

        try:

            inventory = (
                ProductInventory.objects
                .select_for_update()
                .select_related(
                    "product",
                    "dark_store",
                )
                .get(
                    product_id=product_id,
                    dark_store_id=cart.dark_store_id,
                    product__is_active=True,
                    is_available=True,
                )
            )

        except ProductInventory.DoesNotExist:

            return Response(
                {
                    "error": (
                        "This product is not available "
                        "at your selected DarkStore."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # STOCK
        # -----------------------------------------------------

        if inventory.stock_qty <= 0:

            return Response(
                {
                    "error": (
                        "This product is currently "
                        "out of stock."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # EXISTING CART ITEM
        # -----------------------------------------------------

        cart_item, created = (
            CartItem.objects.get_or_create(
                cart=cart,
                product=inventory.product,
                defaults={
                    "quantity": quantity,
                    "unit_price": (
                        inventory.selling_price
                    ),
                },
            )
        )

        # -----------------------------------------------------
        # NEW ITEM
        # -----------------------------------------------------

        if created:

            if quantity > inventory.stock_qty:

                cart_item.delete()

                return Response(
                    {
                        "error": (
                            f"Only "
                            f"{inventory.stock_qty} "
                            f"units are available."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # -----------------------------------------------------
        # EXISTING ITEM
        # -----------------------------------------------------

        else:

            new_quantity = (
                cart_item.quantity + quantity
            )

            if new_quantity > inventory.stock_qty:

                return Response(
                    {
                        "error": (
                            f"Only "
                            f"{inventory.stock_qty} "
                            f"units are available."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_item.quantity = new_quantity

            # Refresh store-specific price.
            cart_item.unit_price = (
                inventory.selling_price
            )

            cart_item.save(
                update_fields=[
                    "quantity",
                    "unit_price",
                    "updated_at",
                ]
            )

        # -----------------------------------------------------
        # RETURN CART
        # -----------------------------------------------------

        cart.refresh_from_db()

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # UPDATE QUANTITY
    # =========================================================

    @action(
        detail=False,
        methods=["patch"],
        url_path=r"items/(?P<item_id>[^/.]+)",
    )
    @transaction.atomic
    def update_item_quantity(
        self,
        request,
        item_id=None,
    ):

        serializer = UpdateCartItemSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        new_quantity = (
            serializer.validated_data["quantity"]
        )

        cart = self._get_or_create_cart(
            request.user
        )

        try:

            cart_item = (
                CartItem.objects
                .select_related(
                    "product",
                )
                .get(
                    id=item_id,
                    cart=cart,
                )
            )

        except (CartItem.DoesNotExist, ValidationError):

            return Response(
                {
                    "error":
                        "Item not found in cart."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # -----------------------------------------------------
        # REMOVE
        # -----------------------------------------------------

        if new_quantity == 0:

            cart_item.delete()

            cart.refresh_from_db()

            return Response(
                CartSerializer(cart).data,
                status=status.HTTP_200_OK,
            )

        # -----------------------------------------------------
        # FIND CURRENT INVENTORY
        # -----------------------------------------------------

        try:

            inventory = (
                ProductInventory.objects
                .select_for_update()
                .get(
                    product_id=cart_item.product_id,
                    dark_store_id=cart.dark_store_id,
                    is_available=True,
                )
            )

        except ProductInventory.DoesNotExist:

            return Response(
                {
                    "error": (
                        "This product is no longer "
                        "available at your DarkStore."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # STOCK
        # -----------------------------------------------------

        if new_quantity > inventory.stock_qty:

            return Response(
                {
                    "error": (
                        f"Only "
                        f"{inventory.stock_qty} "
                        f"units are available."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # UPDATE
        # -----------------------------------------------------

        cart_item.quantity = new_quantity

        cart_item.unit_price = (
            inventory.selling_price
        )

        cart_item.save(
            update_fields=[
                "quantity",
                "unit_price",
                "updated_at",
            ]
        )

        cart.refresh_from_db()

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # REMOVE ITEM
    # =========================================================

    @action(
        detail=False,
        methods=["delete"],
        url_path=r"items/(?P<item_id>[^/.]+)/remove",
    )
    @transaction.atomic
    def remove_item(
        self,
        request,
        item_id=None,
    ):

        cart = self._get_or_create_cart(
            request.user
        )

        try:

            cart_item = CartItem.objects.get(
                id=item_id,
                cart=cart,
            )

        except (CartItem.DoesNotExist, ValidationError):

            return Response(
                {
                    "error":
                        "Item not found in cart."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        cart_item.delete()

        cart.refresh_from_db()

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # CLEAR CART
    # =========================================================

    @action(
        detail=False,
        methods=["delete"],
        url_path="clear",
    )
    @transaction.atomic
    def clear_cart(self, request):

        cart = self._get_or_create_cart(
            request.user
        )

        cart.items.all().delete()

        cart.refresh_from_db()

        return Response(
            {
                "message":
                    "Cart cleared successfully.",

                "cart":
                    CartSerializer(cart).data,
            },
            status=status.HTTP_200_OK,
        )