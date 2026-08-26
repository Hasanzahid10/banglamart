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
        permissions.IsAuthenticated
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

        queryset = self.queryset

        # -----------------------------------------------------
        # ADMIN
        # -----------------------------------------------------

        if user.role == "ADMIN":
            return queryset

        # -----------------------------------------------------
        # WAREHOUSE STAFF
        # -----------------------------------------------------
        #
        # Staff can ONLY see orders from DarkStores
        # assigned through DarkStoreManager.
        #
        # -----------------------------------------------------

        if user.role == "WAREHOUSE_STAFF":

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

            return queryset.filter(
                dark_store_id__in=managed_store_ids
            )

        # -----------------------------------------------------
        # CUSTOMER
        # -----------------------------------------------------

        return queryset.filter(
            user=user
        )

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