from rest_framework import serializers

from orders.models import Order
from .models import PaymentTransaction


class InitiatePaymentSerializer(serializers.Serializer):
    """
    Start a payment for an existing Order.

    Supported gateways:

        - bKash
        - Nagad
        - SSLCommerz
        - Cash on Delivery

    The amount is NEVER accepted from the client.
    It always comes from Order.total_amount.
    """

    order_id = serializers.UUIDField()

    gateway = serializers.ChoiceField(
        choices=PaymentTransaction.Gateway.choices
    )

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    def validate(self, attrs):

        user = self.context["request"].user

        order_id = attrs["order_id"]
        gateway = attrs["gateway"]

        # ==================================================
        # 1. GET ORDER
        # ==================================================

        try:
            order = (
                Order.objects
                .select_related(
                    "user",
                    "dark_store",
                )
                .get(
                    id=order_id,
                    user=user,
                )
            )

        except Order.DoesNotExist:

            raise serializers.ValidationError({
                "order_id": (
                    "Invalid order ID or this order "
                    "does not belong to you."
                )
            })

        # ==================================================
        # 2. PAYMENT ALREADY COMPLETED
        # ==================================================

        if (
            order.payment_status
            == Order.PaymentStatus.PAID
        ):

            raise serializers.ValidationError({
                "order_id":
                    "This order has already been paid."
            })

        # ==================================================
        # 3. REFUNDED
        # ==================================================

        if (
            order.payment_status
            == Order.PaymentStatus.REFUNDED
        ):

            raise serializers.ValidationError({
                "order_id":
                    "This order has already been refunded."
            })

        # ==================================================
        # 4. CANCELLED ORDER
        # ==================================================

        if (
            order.status
            == Order.OrderStatus.CANCELLED
        ):

            raise serializers.ValidationError({
                "order_id":
                    "Cancelled orders cannot be paid."
            })

        # ==================================================
        # 5. CHECK ORDER IS PAYABLE
        # ==================================================

        allowed_order_statuses = {
            Order.OrderStatus.PENDING_PAYMENT,
        }

        if order.status not in allowed_order_statuses:

            raise serializers.ValidationError({
                "order_id": (
                    "This order is not currently "
                    "available for payment."
                )
            })

        # ==================================================
        # 6. CHECK ORDER AMOUNT
        # ==================================================

        if order.total_amount <= 0:

            raise serializers.ValidationError({
                "order_id":
                    "This order has an invalid payment amount."
            })

        # ==================================================
        # 7. COD
        # ==================================================

        if (
            gateway
            == PaymentTransaction.Gateway.COD
        ):

            if (
                order.payment_status
                != Order.PaymentStatus.UNPAID
            ):

                raise serializers.ValidationError({
                    "gateway": (
                        "Cash on Delivery is only "
                        "available for unpaid orders."
                    )
                })

        # ==================================================
        # 8. FIND EXISTING PENDING TRANSACTION
        # ==================================================

        pending_payment = (
            PaymentTransaction.objects
            .filter(
                order=order,
                gateway=gateway,
                status=(
                    PaymentTransaction
                    .TransactionStatus
                    .PENDING
                ),
            )
            .order_by("-created_at")
            .first()
        )

        if pending_payment:

            attrs["existing_transaction"] = (
                pending_payment
            )

        # ==================================================
        # 9. STORE RESOLVED OBJECTS
        # ==================================================

        attrs["order"] = order

        return attrs