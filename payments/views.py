import uuid

from django.db import transaction as db_transaction
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from orders.models import Order

from .models import PaymentTransaction
from .serializers import InitiatePaymentSerializer


class PaymentViewSet(viewsets.ViewSet):
    """
    Payment API for BanglaMart.

    Supported payment methods:

        - bKash
        - Nagad
        - SSLCommerz
        - Cash on Delivery

    Payment flow:

        Digital:
            initiate
                ↓
            gateway
                ↓
            webhook
                ↓
            SUCCESS
                ↓
            Order = CONFIRMED
            Payment = PAID

        COD:
            initiate
                ↓
            Order = CONFIRMED
            Payment = UNPAID
                ↓
            Rider delivers
                ↓
            Order = DELIVERED
            Payment = PAID
    """

    permission_classes = [
        permissions.IsAuthenticated
    ]

    serializer_class = InitiatePaymentSerializer

    # ==========================================================
    # INITIATE PAYMENT
    # ==========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="initiate",
    )
    def initiate_payment(self, request):
        """
        POST /api/payments/initiate/

        Request:

        {
            "order_id": "UUID",
            "gateway": "bkash"
        }
        """

        serializer = InitiatePaymentSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        order = serializer.validated_data["order"]
        gateway = serializer.validated_data["gateway"]

        existing_transaction = (
            serializer.validated_data.get(
                "existing_transaction"
            )
        )

        # ======================================================
        # EXISTING PENDING PAYMENT
        # ======================================================

        if existing_transaction:

            return Response(
                {
                    "message": (
                        "A payment transaction is "
                        "already pending."
                    ),
                    "transaction_id": (
                        existing_transaction.transaction_id
                    ),
                    "gateway": (
                        existing_transaction.gateway
                    ),
                    "status": (
                        existing_transaction.status
                    ),
                    "amount": str(
                        existing_transaction.amount
                    ),
                    "currency": (
                        existing_transaction.currency
                    ),
                },
                status=status.HTTP_200_OK,
            )

        # ======================================================
        # LOCK ORDER
        # ======================================================

        with db_transaction.atomic():

            locked_order = (
                Order.objects
                .select_for_update()
                .get(
                    id=order.id,
                    user=request.user,
                )
            )

            # --------------------------------------------------
            # Re-check payment status
            # --------------------------------------------------

            if (
                locked_order.payment_status
                == Order.PaymentStatus.PAID
            ):
                return Response(
                    {
                        "error":
                            "This order is already paid."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # --------------------------------------------------
            # Re-check order status
            # --------------------------------------------------

            if (
                locked_order.status
                == Order.OrderStatus.CANCELLED
            ):
                return Response(
                    {
                        "error":
                            "Cancelled orders cannot be paid."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ==================================================
            # CREATE INTERNAL TRANSACTION ID
            # ==================================================

            transaction_id = self._generate_transaction_id()

            payment = PaymentTransaction.objects.create(
                transaction_id=transaction_id,

                order=locked_order,

                user=request.user,

                gateway=gateway,

                amount=locked_order.total_amount,

                currency="BDT",

                status=(
                    PaymentTransaction
                    .TransactionStatus
                    .PENDING
                ),
            )

            # ==================================================
            # CASH ON DELIVERY
            # ==================================================

            if (
                gateway
                == PaymentTransaction.Gateway.COD
            ):

                # ------------------------------------------------
                # COD is NOT paid at this point.
                #
                # Customer pays the rider after delivery.
                # ------------------------------------------------

                locked_order.status = (
                    Order.OrderStatus.CONFIRMED
                )

                locked_order.payment_status = (
                    Order.PaymentStatus.UNPAID
                )

                locked_order.save(
                    update_fields=[
                        "status",
                        "payment_status",
                        "updated_at",
                    ]
                )

                return Response(
                    {
                        "message": (
                            "COD order confirmed successfully."
                        ),

                        "transaction_id": (
                            payment.transaction_id
                        ),

                        "gateway": (
                            payment.gateway
                        ),

                        "transaction_status": (
                            payment.status
                        ),

                        "order_status": (
                            locked_order.status
                        ),

                        "payment_status": (
                            locked_order.payment_status
                        ),

                        "amount": str(
                            payment.amount
                        ),

                        "currency": (
                            payment.currency
                        ),

                        "payment_due": (
                            "ON_DELIVERY"
                        ),
                    },
                    status=status.HTTP_201_CREATED,
                )

            # ==================================================
            # DIGITAL PAYMENT
            # ==================================================

            return self._build_digital_payment_response(
                payment
            )

    # ==========================================================
    # GENERATE TRANSACTION ID
    # ==========================================================

    @staticmethod
    def _generate_transaction_id():
        """
        Generate a unique internal transaction ID.

        Example:
            TRX-A91F27D4B8C2
        """

        return (
            f"TRX-"
            f"{uuid.uuid4().hex[:12].upper()}"
        )

    # ==========================================================
    # DIGITAL PAYMENT RESPONSE
    # ==========================================================

    @staticmethod
    def _build_digital_payment_response(payment):
        """
        Return the information required by the frontend
        to continue with a real payment gateway.

        The actual gateway integration should replace the
        placeholder gateway_redirect_url.
        """

        gateway_redirect_url = (
            f"/api/payments/gateway/"
            f"{payment.transaction_id}/"
        )

        return Response(
            {
                "message": (
                    "Payment transaction created successfully."
                ),

                "transaction_id": (
                    payment.transaction_id
                ),

                "gateway": (
                    payment.gateway
                ),

                "status": (
                    payment.status
                ),

                "amount": str(
                    payment.amount
                ),

                "currency": (
                    payment.currency
                ),

                "gateway_redirect_url": (
                    gateway_redirect_url
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    # ==========================================================
    # WEBHOOK / CALLBACK
    # ==========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="webhook-callback",
        permission_classes=[
            permissions.AllowAny
        ],
    )
    def webhook_callback(
        self,
        request,
    ):
        """
        POST /api/payments/webhook-callback/

        Example development payload:

        {
            "trx_id": "TRX-ABC123",
            "status": "SUCCESS",
            "gateway_transaction_id": "BKASH123456"
        }

        IMPORTANT:

        Production gateways must be verified using their
        official signature / validation API.

        Never trust only:

            {"status": "SUCCESS"}
        """

        trx_id = (
            request.data.get("trx_id")
            or request.query_params.get("trx_id")
        )

        gateway_status = (
            request.data.get("status")
            or request.query_params.get("status")
        )

        gateway_transaction_id = (
            request.data.get(
                "gateway_transaction_id"
            )
            or request.query_params.get(
                "gateway_transaction_id"
            )
        )

        # ======================================================
        # VALIDATE TRANSACTION ID
        # ======================================================

        if not trx_id:

            return Response(
                {
                    "error":
                        "Transaction ID is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ======================================================
        # VALIDATE STATUS
        # ======================================================

        if not gateway_status:

            return Response(
                {
                    "error":
                        "Payment status is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        gateway_status = str(
            gateway_status
        ).upper()

        # ======================================================
        # FIND PAYMENT
        # ======================================================

        try:

            payment = (
                PaymentTransaction.objects
                .select_related(
                    "order",
                    "user",
                )
                .get(
                    transaction_id=trx_id
                )
            )

        except PaymentTransaction.DoesNotExist:

            return Response(
                {
                    "error":
                        "Payment transaction not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ======================================================
        # IDEMPOTENCY
        # ======================================================

        if (
            payment.status
            == PaymentTransaction
            .TransactionStatus
            .SUCCESS
        ):

            return Response(
                {
                    "message":
                        "Payment has already been processed.",

                    "transaction_id":
                        payment.transaction_id,

                    "payment_status":
                        payment.status,

                    "order_status":
                        payment.order.status,
                },
                status=status.HTTP_200_OK,
            )

        # ======================================================
        # CAPTURE GATEWAY RESPONSE
        # ======================================================

        gateway_response = {}

        if request.data:

            gateway_response = dict(
                request.data
            )

        elif request.query_params:

            gateway_response = {
                key: values
                for key, values in
                request.query_params.lists()
            }

        # ======================================================
        # SUCCESS
        # ======================================================

        if gateway_status in [
            "SUCCESS",
            "PAID",
            "COMPLETED",
        ]:

            return self._process_success(
                payment_id=payment.id,
                gateway_transaction_id=(
                    gateway_transaction_id
                ),
                gateway_response=(
                    gateway_response
                ),
            )

        # ======================================================
        # CANCELLED
        # ======================================================

        if gateway_status in [
            "CANCELLED",
            "CANCELED",
        ]:

            return self._process_cancelled(
                payment_id=payment.id,
                gateway_response=(
                    gateway_response
                ),
            )

        # ======================================================
        # FAILED
        # ======================================================

        if gateway_status in [
            "FAILED",
            "FAIL",
            "ERROR",
        ]:

            return self._process_failed(
                payment_id=payment.id,
                gateway_response=(
                    gateway_response
                ),
            )

        # ======================================================
        # UNKNOWN STATUS
        # ======================================================

        return Response(
            {
                "error":
                    "Unsupported payment status.",

                "received_status":
                    gateway_status,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ==========================================================
    # PROCESS SUCCESS
    # ==========================================================

    @staticmethod
    def _process_success(
        payment_id,
        gateway_transaction_id,
        gateway_response,
    ):

        with db_transaction.atomic():

            payment = (
                PaymentTransaction.objects
                .select_for_update()
                .select_related("order")
                .get(
                    id=payment_id
                )
            )

            # --------------------------------------------------
            # Idempotency after row lock
            # --------------------------------------------------

            if (
                payment.status
                == PaymentTransaction
                .TransactionStatus
                .SUCCESS
            ):

                return Response(
                    {
                        "message":
                            "Payment already processed.",

                        "transaction_id":
                            payment.transaction_id,

                        "payment_status":
                            payment.status,
                    },
                    status=status.HTTP_200_OK,
                )

            # --------------------------------------------------
            # Do not process cancelled transaction
            # --------------------------------------------------

            if (
                payment.status
                in [
                    PaymentTransaction
                    .TransactionStatus
                    .CANCELLED,
                ]
            ):

                return Response(
                    {
                        "error":
                            "This payment transaction "
                            "has already been cancelled."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            now = timezone.now()

            # --------------------------------------------------
            # Update PaymentTransaction
            # --------------------------------------------------

            payment.status = (
                PaymentTransaction
                .TransactionStatus
                .SUCCESS
            )

            payment.gateway_transaction_id = (
                gateway_transaction_id
            )

            payment.gateway_response = (
                gateway_response
            )

            payment.paid_at = now

            payment.save(
                update_fields=[
                    "status",
                    "gateway_transaction_id",
                    "gateway_response",
                    "paid_at",
                    "updated_at",
                ]
            )

            # --------------------------------------------------
            # Update Order
            # --------------------------------------------------

            order = payment.order

            order.payment_status = (
                Order.PaymentStatus.PAID
            )

            # Only move the order forward if it is waiting
            # for payment.
            if (
                order.status
                == Order.OrderStatus.PENDING_PAYMENT
            ):

                order.status = (
                    Order.OrderStatus.CONFIRMED
                )

                order.save(
                    update_fields=[
                        "payment_status",
                        "status",
                        "updated_at",
                    ]
                )

            else:

                order.save(
                    update_fields=[
                        "payment_status",
                        "updated_at",
                    ]
                )

        return Response(
            {
                "message":
                    "Payment verified successfully.",

                "transaction_id":
                    payment.transaction_id,

                "gateway_transaction_id":
                    payment.gateway_transaction_id,

                "payment_status":
                    payment.status,

                "order_id":
                    str(order.id),

                "order_number":
                    order.order_number,

                "order_status":
                    order.status,
            },
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # PROCESS FAILED
    # ==========================================================

    @staticmethod
    def _process_failed(
        payment_id,
        gateway_response,
    ):

        with db_transaction.atomic():

            payment = (
                PaymentTransaction.objects
                .select_for_update()
                .select_related("order")
                .get(
                    id=payment_id
                )
            )

            # Already successful payment must never
            # become failed.
            if (
                payment.status
                == PaymentTransaction
                .TransactionStatus
                .SUCCESS
            ):

                return Response(
                    {
                        "message":
                            "Payment was already successful.",

                        "transaction_id":
                            payment.transaction_id,

                        "payment_status":
                            payment.status,
                    },
                    status=status.HTTP_200_OK,
                )

            payment.status = (
                PaymentTransaction
                .TransactionStatus
                .FAILED
            )

            payment.gateway_response = (
                gateway_response
            )

            payment.failed_at = timezone.now()

            payment.save(
                update_fields=[
                    "status",
                    "gateway_response",
                    "failed_at",
                    "updated_at",
                ]
            )

            order = payment.order

            # --------------------------------------------------
            # IMPORTANT:
            #
            # Do NOT automatically cancel the order here.
            #
            # The customer may retry payment.
            # --------------------------------------------------

        return Response(
            {
                "message":
                    "Payment failed. You may retry payment.",

                "transaction_id":
                    payment.transaction_id,

                "payment_status":
                    payment.status,

                "order_id":
                    str(order.id),

                "order_status":
                    order.status,
            },
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # PROCESS CANCELLED
    # ==========================================================

    @staticmethod
    def _process_cancelled(
        payment_id,
        gateway_response,
    ):

        with db_transaction.atomic():

            payment = (
                PaymentTransaction.objects
                .select_for_update()
                .select_related("order")
                .get(
                    id=payment_id
                )
            )

            # --------------------------------------------------
            # Cannot cancel successful transaction
            # --------------------------------------------------

            if (
                payment.status
                == PaymentTransaction
                .TransactionStatus
                .SUCCESS
            ):

                return Response(
                    {
                        "error":
                            "A successful payment "
                            "cannot be cancelled."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment.status = (
                PaymentTransaction
                .TransactionStatus
                .CANCELLED
            )

            payment.gateway_response = (
                gateway_response
            )

            payment.save(
                update_fields=[
                    "status",
                    "gateway_response",
                    "updated_at",
                ]
            )

            order = payment.order

        return Response(
            {
                "message":
                    "Payment transaction cancelled.",

                "transaction_id":
                    payment.transaction_id,

                "payment_status":
                    payment.status,

                "order_id":
                    str(order.id),

                "order_status":
                    order.status,
            },
            status=status.HTTP_200_OK,
        )