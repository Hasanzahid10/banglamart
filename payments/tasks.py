import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from orders.models import Order
from .models import PaymentTransaction


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cancel_expired_payment_transactions(
    self,
    expiry_minutes=30,
):
    """
    Cancel payment transactions that have remained PENDING
    beyond the allowed payment window.

    COD transactions are excluded.

    If the order has no successful payment transaction and is
    still waiting for payment, cancel the order as well.
    """

    now = timezone.now()

    threshold_time = (
        now - timedelta(minutes=expiry_minutes)
    )

    expired_ids = list(
        PaymentTransaction.objects.filter(
            status=PaymentTransaction.TransactionStatus.PENDING,
            created_at__lte=threshold_time,
        )
        .exclude(
            gateway=PaymentTransaction.Gateway.COD
        )
        .values_list("id", flat=True)
    )

    cancelled_count = 0

    for payment_id in expired_ids:

        try:
            with transaction.atomic():

                payment = (
                    PaymentTransaction.objects
                    .select_for_update()
                    .select_related("order")
                    .get(pk=payment_id)
                )

                # Another process may already have handled it.
                if (
                    payment.status
                    != PaymentTransaction.TransactionStatus.PENDING
                ):
                    continue

                payment.status = (
                    PaymentTransaction.TransactionStatus.CANCELLED
                )

                payment.cancelled_at = now

                payment.gateway_response = {
                    "reason": (
                        "Payment automatically cancelled "
                        "because the payment window expired."
                    ),
                    "expired_at": now.isoformat(),
                }

                payment.save(
                    update_fields=[
                        "status",
                        "cancelled_at",
                        "gateway_response",
                        "updated_at",
                    ]
                )

                order = (
                    Order.objects
                    .select_for_update()
                    .get(pk=payment.order_id)
                )

                has_successful_payment = (
                    PaymentTransaction.objects.filter(
                        order_id=order.id,
                        status=(
                            PaymentTransaction
                            .TransactionStatus
                            .SUCCESS
                        ),
                    ).exists()
                )

                if (
                    not has_successful_payment
                    and order.status
                    == Order.OrderStatus.PENDING_PAYMENT
                ):
                    order.status = (
                        Order.OrderStatus.CANCELLED
                    )

                    order.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

                    logger.info(
                        "Order %s cancelled because payment "
                        "transaction %s expired.",
                        order.id,
                        payment.id,
                    )

                cancelled_count += 1

                logger.info(
                    "Payment transaction %s expired.",
                    payment.id,
                )

        except PaymentTransaction.DoesNotExist:
            continue

        except Exception:
            logger.exception(
                "Failed to expire payment transaction %s",
                payment_id,
            )
            raise

    return {
        "cancelled_count": cancelled_count,
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def reconcile_pending_payments(self):
    """
    Reconcile pending digital payments with the payment gateway.

    This task should query the appropriate gateway API and update
    the local PaymentTransaction state.

    COD transactions are excluded.
    """

    pending_payments = (
        PaymentTransaction.objects
        .filter(
            status=PaymentTransaction.TransactionStatus.PENDING
        )
        .exclude(
            gateway=PaymentTransaction.Gateway.COD
        )
    )

    processed_count = 0
    success_count = 0
    failed_count = 0

    for payment in pending_payments.iterator():

        try:
            logger.info(
                "Reconciling payment %s via %s",
                payment.transaction_id,
                payment.gateway,
            )

            # --------------------------------------------------
            # Gateway-specific implementation goes here.
            # --------------------------------------------------
            #
            # Example:
            #
            # gateway_status = query_gateway_status(payment)
            #
            # if gateway_status == "SUCCESS":
            #     payment.mark_success(...)
            #     success_count += 1
            #
            # elif gateway_status == "FAILED":
            #     payment.mark_failed(...)
            #     failed_count += 1
            #
            # else:
            #     pass

            processed_count += 1

        except Exception:
            logger.exception(
                "Payment reconciliation failed for %s",
                payment.id,
            )

    return {
        "processed_count": processed_count,
        "success_count": success_count,
        "failed_count": failed_count,
    }