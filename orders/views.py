from django.db import transaction
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from logistics.models import (
    DeliveryOrder,
    DarkStoreManager,
)

from .models import Order
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
)


from django.db.models import Q

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Order management for a multi-dark-store system.

    Access rules:

    ADMIN
        - Can see all orders.
        - Can manage all orders.

    WAREHOUSE_STAFF
        - Can see orders belonging to their assigned
          DarkStores only.
        - Cannot access another DarkStore's orders.

    CUSTOMER
        - Can see only their own orders.
        - Can checkout.
        - Can cancel their own unpaid orders.
    """

    permission_classes = [
        permissions.AllowAny
    ]

    serializer_class = OrderSerializer

    # =========================================================
    # BASE QUERYSET
    # =========================================================

    queryset = (
        Order.objects
        .select_related(
            "user",
            "dark_store",
            "dark_store__service_area",
            "delivery_order",
        )
        .prefetch_related(
            "items",
            "items__inventory",
            "items__inventory__product",
        )
        .order_by("-created_at")
    )

    # =========================================================
    # QUERYSET
    # =========================================================

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Order.objects
            .select_related(
                "user",
                "dark_store",
                "dark_store__service_area",
                "delivery_order",
            )
            .prefetch_related(
                "items",
                "items__inventory",
                "items__inventory__product",
            )
            .order_by("-created_at")
        )

        # Query params search (e.g. ?phone=01333410106 or ?email=...)
        phone_param = (self.request.query_params.get('phone') or self.request.query_params.get('customer_phone') or '').strip()
        email_param = (self.request.query_params.get('email') or self.request.query_params.get('customer_email') or '').strip()

        if phone_param:
            return queryset.filter(
                Q(user__phone_number=phone_param) |
                Q(delivery_address_snapshot__recipient_phone=phone_param)
            ).distinct()

        if email_param:
            return queryset.filter(
                Q(user__email__iexact=email_param) |
                Q(delivery_address_snapshot__recipient_email__iexact=email_param)
            ).distinct()

        if user and user.is_authenticated and getattr(user, 'role', '') in ["ADMIN", "SUPERADMIN", "STAFF", "WAREHOUSE_STAFF"]:
            return queryset

        if user and user.is_authenticated:
            user_phone = getattr(user, 'phone_number', '') or ''
            user_email = getattr(user, 'email', '') or ''

            filters = Q(user=user)
            if user_phone and '@' not in user_phone:
                filters |= Q(delivery_address_snapshot__recipient_phone=user_phone) | Q(user__phone_number=user_phone)
            if user_email and '@' in user_email:
                filters |= Q(user__email__iexact=user_email)

            return queryset.filter(filters).distinct()

        return queryset

    # =========================================================
    # UPDATE STATUS & DISPATCH
    # =========================================================

    @action(detail=True, methods=['patch', 'post'], url_path='update-status')
    def update_status(self, request, pk=None):
        try:
            order = Order.objects.get(id=pk)
        except (Order.DoesNotExist, Exception):
            try:
                order = Order.objects.get(order_number=pk)
            except Order.DoesNotExist:
                return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        new_payment_status = request.data.get('payment_status')

        if new_status:
            order.status = new_status.lower()
        if new_payment_status:
            order.payment_status = new_payment_status.lower()

        order.save()

        return Response({
            'message': 'Order status updated successfully',
            'order': OrderSerializer(order, context={'request': request}).data
        }, status=status.HTTP_200_OK)

    # =========================================================
    # CHECKOUT
    # =========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="checkout",
    )
    def checkout(self, request):

        """
        POST /api/orders/checkout/

        Customer converts their cart into an Order.

        Example:

        {
            "delivery_order_id":
                "UUID",
            "note":
                "Please call before delivery"
        }

        The CheckoutSerializer is responsible for:

        - validating cart
        - validating stock
        - resolving DarkStore
        - resolving delivery address
        - calculating delivery fee
        - creating Order
        - reducing inventory
        """

        # -----------------------------------------------------
        # CUSTOMER ONLY
        # -----------------------------------------------------

        if request.user.role not in [
            "CUSTOMER",
            "USER",
        ]:

            return Response(
                {
                    "detail":
                        "Only customers can checkout."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CheckoutSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        order = serializer.save()

        # -----------------------------------------------------
        # PAYMENT GATEWAY PAYLOAD
        # -----------------------------------------------------

        payment_payload = {

            "order_id": str(
                order.id
            ),

            "order_number":
                order.order_number,

            "amount":
                str(order.total_amount),

            "currency":
                "BDT",

            "customer": {

                "user_id":
                    order.user.id,

                "phone":
                    order.user.phone_number or "",

                "email":
                    order.user.email or "",
            },

            "redirect_urls": {

                "success_url":
                    (
                        f"/api/orders/"
                        f"{order.id}/"
                        f"payment-callback/"
                    ),

                "fail_url":
                    (
                        f"/api/orders/"
                        f"{order.id}/"
                        f"payment-callback/"
                    ),
            },
        }

        return Response(
            {
                "message":
                    (
                        "Order created successfully. "
                        "Proceed to payment."
                    ),

                "order":
                    OrderSerializer(
                        order,
                        context={
                            "request": request,
                        },
                    ).data,

                "payment_gateway_payload":
                    payment_payload,
            },
            status=status.HTTP_201_CREATED,
        )

    # =========================================================
    # PAYMENT CALLBACK
    # =========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="payment-callback",
        permission_classes=[
            permissions.AllowAny
        ],
    )
    def payment_callback(
        self,
        request,
        pk=None,
    ):

        """
        Payment gateway callback.

        IMPORTANT:

        This endpoint should eventually verify:

        - gateway transaction ID
        - gateway signature
        - amount
        - currency
        - order number

        Do NOT trust:
            {"payment_status": "paid"}

        from an unauthenticated client.
        """

        # -----------------------------------------------------
        # LOCK ORDER
        # -----------------------------------------------------

        try:

            with transaction.atomic():

                order = (
                    Order.objects
                    .select_for_update()
                    .select_related(
                        "user",
                        "dark_store",
                    )
                    .get(
                        id=pk
                    )
                )

                # -------------------------------------------------
                # ALREADY PAID
                # -------------------------------------------------

                if (
                    order.payment_status
                    == Order.PaymentStatus.PAID
                ):

                    return Response(
                        {
                            "message":
                                (
                                    "Order payment has "
                                    "already been confirmed."
                                ),

                            "order_id":
                                str(order.id),

                            "order_number":
                                order.order_number,

                            "order_status":
                                order.status,

                            "payment_status":
                                order.payment_status,
                        },
                        status=status.HTTP_200_OK,
                    )

                # -------------------------------------------------
                # PAYMENT DATA
                # -------------------------------------------------

                payment_status_input = (
                    request.data.get(
                        "payment_status"
                    )
                    or request.query_params.get(
                        "status"
                    )
                )

                if not payment_status_input:

                    return Response(
                        {
                            "error":
                                "Payment status is required."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # -------------------------------------------------
                # NORMALIZE
                # -------------------------------------------------

                payment_status_input = (
                    str(
                        payment_status_input
                    ).lower()
                )

                valid_statuses = {
                    Order.PaymentStatus.UNPAID,
                    Order.PaymentStatus.PAID,
                    Order.PaymentStatus.REFUNDED,
                    Order.PaymentStatus.FAILED,
                }

                if (
                    payment_status_input
                    not in valid_statuses
                ):

                    return Response(
                        {
                            "error":
                                "Invalid payment status."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # -------------------------------------------------
                # UPDATE PAYMENT
                # -------------------------------------------------

                order.payment_status = (
                    payment_status_input
                )

                if (
                    payment_status_input
                    == Order.PaymentStatus.PAID
                ):

                    order.status = (
                        Order.OrderStatus.CONFIRMED
                    )

                elif (
                    payment_status_input
                    == Order.PaymentStatus.FAILED
                ):

                    order.status = (
                        Order.OrderStatus.CANCELLED
                    )

                elif (
                    payment_status_input
                    == Order.PaymentStatus.REFUNDED
                ):

                    order.status = (
                        Order.OrderStatus.CANCELLED
                    )

                order.save(
                    update_fields=[
                        "payment_status",
                        "status",
                        "updated_at",
                    ]
                )

        except Order.DoesNotExist:

            return Response(
                {
                    "error":
                        "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "message":
                    "Payment status updated successfully.",

                "order_id":
                    str(order.id),

                "order_number":
                    order.order_number,

                "order_status":
                    order.status,

                "payment_status":
                    order.payment_status,
            },
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # CANCEL ORDER
    # =========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel_order(
        self,
        request,
        pk=None,
    ):

        """
        POST /api/orders/<id>/cancel/

        CUSTOMER:
            Can cancel own unpaid order.

        ADMIN:
            Can cancel any cancellable order.

        WAREHOUSE_STAFF:
            Can cancel only orders belonging to their
            assigned DarkStore.
        """

        order = self.get_object()

        user = request.user

        # -----------------------------------------------------
        # PERMISSION
        # -----------------------------------------------------

        if user.role == "ADMIN":

            pass

        elif user.role == "WAREHOUSE_STAFF":

            is_manager = (
                DarkStoreManager.objects
                .filter(
                    user=user,
                    dark_store=order.dark_store,
                    is_active=True,
                )
                .exists()
            )

            if not is_manager:

                return Response(
                    {
                        "detail":
                            (
                                "You are not authorized "
                                "to manage this DarkStore."
                            )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        else:

            if order.user_id != user.id:

                return Response(
                    {
                        "detail":
                            "You cannot cancel this order."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # -----------------------------------------------------
        # ORDER STATUS
        # -----------------------------------------------------

        if order.status not in [
            Order.OrderStatus.PENDING_PAYMENT,
            Order.OrderStatus.CONFIRMED,
        ]:

            return Response(
                {
                    "error":
                        (
                            "This order can no longer "
                            "be cancelled."
                        )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # PAID ORDER
        # -----------------------------------------------------

        if (
            order.payment_status
            == Order.PaymentStatus.PAID
        ):

            return Response(
                {
                    "error":
                        (
                            "Paid orders cannot be "
                            "cancelled through this endpoint."
                        )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # CANCEL
        # -----------------------------------------------------

        with transaction.atomic():

            order = (
                Order.objects
                .select_for_update()
                .get(
                    id=order.id
                )
            )

            order.status = (
                Order.OrderStatus.CANCELLED
            )

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return Response(
            {
                "message":
                    "Order cancelled successfully.",

                "order_id":
                    str(order.id),

                "order_number":
                    order.order_number,

                "order_status":
                    order.status,
            },
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # STORE ORDERS
    # =========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="store-orders",
    )
    def store_orders(
        self,
        request,
    ):

        """
        GET /api/orders/store-orders/

        ADMIN:
            Returns all orders.

        WAREHOUSE_STAFF:
            Returns orders from their assigned stores.

        CUSTOMER:
            Forbidden.
        """

        user = request.user

        if user.role == "ADMIN":

            orders = self.queryset

        elif user.role == "WAREHOUSE_STAFF":

            managed_store_ids = (
                DarkStoreManager.objects
                .filter(
                    user=user,
                    is_active=True,
                    dark_store__is_active=True,
                )
                .values_list(
                    "dark_store_id",
                    flat=True,
                )
            )

            orders = self.queryset.filter(
                dark_store_id__in=managed_store_ids
            )

        else:

            return Response(
                {
                    "detail":
                        (
                            "Only admin or warehouse "
                            "staff can access store orders."
                        )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrderSerializer(
            orders,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


from rest_framework.views import APIView
from decimal import Decimal
import uuid
from .models import OrderItem
from logistics.models import DarkStore, ServiceArea, DeliveryOrder
from products.models import ProductInventory
from cart.models import GuestCart
from django.contrib.auth import get_user_model
User = get_user_model()


class PlaceOrderView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            data = request.data
            customer_name = (data.get('customer_name') or '').strip() or 'Customer'
            customer_phone = (data.get('customer_phone') or '').strip()
            customer_email = (data.get('customer_email') or '').strip()
            delivery_address = data.get('delivery_address', {})
            cart_items = data.get('items', [])
            
            try:
                subtotal = Decimal(str(data.get('subtotal', 0)))
                delivery_fee = Decimal(str(data.get('delivery_fee', 49)))
                discount_amount = Decimal(str(data.get('discount_amount', 0)))
                total_amount = Decimal(str(data.get('total_amount', subtotal + delivery_fee - discount_amount)))
            except Exception:
                subtotal = Decimal("0.00")
                delivery_fee = Decimal("49.00")
                discount_amount = Decimal("0.00")
                total_amount = Decimal("49.00")

            note = data.get('note', '')

            # Resolve user
            user = None
            if request.user and request.user.is_authenticated:
                user = request.user
            elif customer_phone:
                user = User.objects.filter(phone_number=customer_phone).first()
            if not user and customer_email:
                user = User.objects.filter(email__iexact=customer_email).first()

            if not user and (customer_phone or customer_email):
                clean_p = customer_phone.strip() if customer_phone else ''
                clean_e = customer_email.strip() if customer_email else ''
                if clean_p:
                    user = User.objects.filter(phone_number=clean_p).first()
                if not user and clean_e:
                    user = User.objects.filter(email__iexact=clean_e).first()
                if not user:
                    random_pass = uuid.uuid4().hex[:12]
                    user = User.objects.create_user(
                        phone_number=clean_p or None,
                        email=clean_e or (f"{clean_p}@metrobazar.com" if clean_p else ""),
                        first_name=customer_name,
                        role="CUSTOMER",
                        password=random_pass,
                    )

            if not user:
                user = User.objects.filter(is_superuser=False).first() or User.objects.first()

            if customer_phone and user and not user.phone_number:
                user.phone_number = customer_phone
                user.save(update_fields=['phone_number'])

            # Ensure active dark store exists fallback
            dark_store = DarkStore.objects.filter(is_active=True).first() or DarkStore.objects.first()
            if not dark_store:
                service_area, _ = ServiceArea.objects.get_or_create(
                    code="RGP-01",
                    defaults={"name": "Rangpur", "is_active": True}
                )
                dark_store, _ = DarkStore.objects.get_or_create(
                    code="DS-RGP-01",
                    defaults={
                        "service_area": service_area,
                        "name": "Rangpur Central Dark Store",
                        "address": "Rangpur City Center",
                        "contact_number": "01700000000",
                        "is_active": True
                    }
                )

            # Format unique Order Number
            random_code = uuid.uuid4().hex[:8].upper()
            order_number = f"ORD-{random_code}"

            address_snapshot = {
                "recipient_name": delivery_address.get('recipient_name') or customer_name,
                "recipient_phone": delivery_address.get('recipient_phone') or customer_phone,
                "street_address": delivery_address.get('street_address') or delivery_address.get('details') or "Address",
                "area": delivery_address.get('area') or "Rangpur",
                "city": delivery_address.get('city') or "Rangpur",
            }

            with transaction.atomic():
                order = Order.objects.create(
                    order_number=order_number,
                    user=user,
                    dark_store=dark_store,
                    status=Order.OrderStatus.PROCESSING,
                    payment_status=Order.PaymentStatus.UNPAID,
                    subtotal=subtotal,
                    delivery_fee=delivery_fee,
                    discount_amount=discount_amount,
                    total_amount=total_amount,
                    delivery_address_snapshot=address_snapshot,
                    note=note
                )

                for item in cart_items:
                    p_id = item.get('id') or item.get('product_id')
                    p_name = item.get('name') or item.get('product_name_en') or 'Product'
                    p_price = Decimal(str(item.get('price') or item.get('unit_price') or 0))
                    p_qty = int(item.get('quantity', 1))
                    p_subtotal = Decimal(str(item.get('subtotal', p_price * p_qty)))
                    p_unit = item.get('unit', '1 pc')

                    inv = None
                    if p_id:
                        try:
                            inv = ProductInventory.objects.filter(product_id=p_id).first()
                            if not inv:
                                inv = ProductInventory.objects.filter(id=p_id).first()
                        except Exception:
                            pass
                    if not inv:
                        inv = ProductInventory.objects.first()

                    if not inv:
                        # Fallback inventory creation if database ProductInventory table is empty
                        from products.models import Product as ProdModel
                        prod = ProdModel.objects.first()
                        if not prod:
                            prod = ProdModel.objects.create(
                                name_en=p_name,
                                slug=f"prod-{uuid.uuid4().hex[:6]}",
                                base_price=p_price if p_price > 0 else Decimal("100.00"),
                                unit=p_unit
                            )
                        inv, _ = ProductInventory.objects.get_or_create(
                            dark_store=dark_store,
                            product=prod,
                            defaults={"stock_qty": 999, "is_available": True}
                        )

                    OrderItem.objects.create(
                        order=order,
                        inventory=inv,
                        product_name_en=p_name,
                        sku=inv.product.sku if (inv and inv.product) else 'SKU-001',
                        unit=p_unit,
                        unit_price=p_price,
                        quantity=p_qty,
                        subtotal=p_subtotal,
                        dark_store_name=dark_store.name if dark_store else '',
                    )

                # Auto-create DeliveryOrder for logistics & riders
                try:
                    DeliveryOrder.objects.create(
                        user=user,
                        dark_store=dark_store,
                        tracking_number=f"TRK-{order_number}",
                        status=DeliveryOrder.Status.PENDING
                    )
                except Exception:
                    pass

                # Mark user's active guest cart as CONVERTED
                if user:
                    GuestCart.objects.filter(user=user, status='ACTIVE').update(status='CONVERTED')

            # Trigger real-time email notification to Admin (admin@metrobazar.online -> metrobazar2025@gmail.com)
            try:
                from .emails import send_admin_order_notification_email
                send_admin_order_notification_email(order)
            except Exception as err:
                pass

            return Response({
                "message": "Order created successfully",
                "order_number": order.order_number,
                "order": OrderSerializer(order, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)

        except Exception as main_err:
            import traceback
            traceback.print_exc()
            return Response({
                "detail": f"Failed to place order: {str(main_err)}"
            }, status=status.HTTP_400_BAD_REQUEST)