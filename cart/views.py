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


from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


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

    serializer_class = CartSerializer

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

    @extend_schema(
        request=AddToCartSerializer,
        responses={200: CartSerializer}
    )
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

    @extend_schema(
        parameters=[
            OpenApiParameter("item_id", OpenApiTypes.UUID, OpenApiParameter.PATH, description="The UUID of the cart item to update.")
        ],
        request=UpdateCartItemSerializer,
        responses={200: CartSerializer}
    )
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

    @extend_schema(
        parameters=[
            OpenApiParameter("item_id", OpenApiTypes.UUID, OpenApiParameter.PATH, description="The UUID of the cart item to remove.")
        ],
        responses={200: CartSerializer}
    )
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

    @extend_schema(
        responses={200: CartSerializer}
    )
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


from rest_framework.views import APIView
from products.models import Product
from .models import GuestCart, GuestCartItem
from .serializers import GuestCartSerializer


class GuestCartSyncView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        guest_id = request.data.get('guest_id')
        if not guest_id:
            return Response({'error': 'guest_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        city = request.data.get('city', 'Dhaka')
        device_info = request.data.get('device_info', '')
        browser = request.data.get('browser', '')
        os_info = request.data.get('os', '')
        cart_items_data = request.data.get('cart_items', [])

        # Extract client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')

        guest_cart, _ = GuestCart.objects.get_or_create(
            guest_id=guest_id,
            defaults={'city': city, 'ip_address': ip_address, 'device_info': device_info, 'browser': browser, 'os': os_info}
        )

        guest_cart.city = city
        guest_cart.ip_address = ip_address
        if device_info:
            guest_cart.device_info = device_info
        if browser:
            guest_cart.browser = browser
        if os_info:
            guest_cart.os = os_info
        guest_cart.save()

        # Update cart items
        guest_cart.items.all().delete()
        new_items = []
        for item in cart_items_data:
            p_id = item.get('id') or item.get('product_id')
            p_name = item.get('name', 'Product')
            price = item.get('price', 0)
            qty = item.get('quantity', 1)

            prod = None
            if p_id:
                try:
                    prod = Product.objects.filter(id=p_id).first()
                except Exception:
                    pass

            new_items.append(
                GuestCartItem(
                    guest_cart=guest_cart,
                    product=prod,
                    product_name=p_name,
                    quantity=qty,
                    unit_price=price
                )
            )

        if new_items:
            GuestCartItem.objects.bulk_create(new_items)

        return Response(GuestCartSerializer(guest_cart).data, status=status.HTTP_200_OK)


class GuestCartFetchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        guest_id = request.query_params.get('guest_id')
        if not guest_id:
            return Response({'error': 'guest_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        guest_cart = GuestCart.objects.filter(guest_id=guest_id).prefetch_related('items').first()
        if not guest_cart:
            return Response({'message': 'No saved cart found for this guest_id', 'items': []}, status=status.HTTP_200_OK)

        return Response(GuestCartSerializer(guest_cart).data, status=status.HTTP_200_OK)


class GuestCartConvertView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        guest_id = request.data.get('guest_id')
        email = request.data.get('email')
        phone = request.data.get('phone')

        if not guest_id:
            return Response({'error': 'guest_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        guest_cart = GuestCart.objects.filter(guest_id=guest_id).first()
        if guest_cart:
            guest_cart.status = 'CONVERTED'
            user = None
            if request.user and request.user.is_authenticated:
                user = request.user
            elif email:
                user = User.objects.filter(email__iexact=email).first()
            elif phone:
                user = User.objects.filter(phone_number=phone).first()

            if user:
                guest_cart.user = user

            guest_cart.save()
            return Response(GuestCartSerializer(guest_cart).data, status=status.HTTP_200_OK)

        return Response({'message': 'Guest cart converted'}, status=status.HTTP_200_OK)


class AdminGuestCartViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = GuestCartSerializer
    queryset = GuestCart.objects.all().prefetch_related('items')

    def list(self, request, *args, **kwargs):
        status_filter = request.query_params.get('status')
        qs = self.get_queryset()
        if status_filter:
            qs = qs.filter(status=status_filter)

        serialized = GuestCartSerializer(qs, many=True).data

        # Metrics calculation
        total_active_carts = GuestCart.objects.filter(status='ACTIVE').count()
        active_value = sum(c.total_price for c in GuestCart.objects.filter(status='ACTIVE'))
        total_converted = GuestCart.objects.filter(status='CONVERTED').count()
        total_abandoned = GuestCart.objects.filter(status='ABANDONED').count()
        total_guests = GuestCart.objects.count()

        return Response({
            'metrics': {
                'total_guests': total_guests,
                'total_active_carts': total_active_carts,
                'active_cart_value': active_value,
                'total_converted': total_converted,
                'total_abandoned': total_abandoned,
                'conversion_rate': round((total_converted / total_guests * 100), 1) if total_guests > 0 else 0,
            },
            'carts': serialized
        }, status=status.HTTP_200_OK)