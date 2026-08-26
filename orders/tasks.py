import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from products.models import ProductInventory

from .models import Order

logger = logging.getLogger(__name__)


# ============================================================
# CANCEL EXPIRED UNPAID ORDERS
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cancel_unpaid_orders(self, expiry_minutes=30):
    """
    Automatically cancel orders that remain unpaid for longer
    than expiry_minutes.

    Also releases their reserved inventory.
    """

    threshold_time = (
        timezone.now()
        - timedelta(minutes=expiry_minutes)
    )

    order_ids = list(
        Order.objects.filter(
            status=Order.OrderStatus.PENDING_PAYMENT,
            payment_status=Order.PaymentStatus.UNPAID,
            created_at__lte=threshold_time,
        ).values_list(
            "id",
            flat=True,
        )
    )

    cancelled_count = 0

    for order_id in order_ids:

        try:

            with transaction.atomic():

                # ------------------------------------------------
                # Lock order
                # ------------------------------------------------

                order = (
                    Order.objects
                    .select_for_update()
                    .get(pk=order_id)
                )

                # ------------------------------------------------
                # Double-check status
                # ------------------------------------------------

                if (
                    order.status
                    != Order.OrderStatus.PENDING_PAYMENT
                ):
                    continue

                if (
                    order.payment_status
                    != Order.PaymentStatus.UNPAID
                ):
                    continue

                # ------------------------------------------------
                # Release reserved inventory
                # ------------------------------------------------

                release_reserved_stock(order)

                # ------------------------------------------------
                # Cancel order
                # ------------------------------------------------

                order.status = Order.OrderStatus.CANCELLED

                order.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                cancelled_count += 1

                logger.info(
                    "Automatically cancelled unpaid order %s.",
                    order.order_number,
                )

        except Order.DoesNotExist:

            logger.warning(
                "Order %s no longer exists.",
                order_id,
            )

        except Exception:

            logger.exception(
                "Failed to cancel order %s.",
                order_id,
            )

            raise

    return {
        "cancelled_count": cancelled_count,
    }


# ============================================================
# RELEASE RESERVED STOCK
# ============================================================

def release_reserved_stock(order):
    """
    Release reserved inventory for an order.

    IMPORTANT:
    This function must be called inside transaction.atomic().
    """

    for item in (
        order.items
        .select_related("inventory")
        .all()
    ):

        inventory = (
            ProductInventory.objects
            .select_for_update()
            .get(
                pk=item.inventory_id
            )
        )

        # ------------------------------------------------
        # Release reservation
        # ------------------------------------------------

        if hasattr(inventory, "reserved_qty"):

            inventory.reserved_qty = max(
                0,
                inventory.reserved_qty - item.quantity,
            )

            inventory.save(
                update_fields=[
                    "reserved_qty",
                    "updated_at",
                ]
            )

        else:

            logger.warning(
                "ProductInventory %s does not have reserved_qty.",
                inventory.pk,
            )


# ============================================================
# MANUAL ORDER STOCK RELEASE
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def release_order_stock(
    self,
    order_id,
):
    """
    Release reserved stock for a cancelled order.

    Use this when an order is manually cancelled.
    """

    try:

        with transaction.atomic():

            order = (
                Order.objects
                .select_for_update()
                .get(pk=order_id)
            )

            # ------------------------------------------------
            # Only cancelled orders
            # ------------------------------------------------

            if (
                order.status
                != Order.OrderStatus.CANCELLED
            ):

                logger.warning(
                    "Order %s is not cancelled.",
                    order.order_number,
                )

                return {
                    "success": False,
                    "message": "Order is not cancelled.",
                }

            # ------------------------------------------------
            # Release stock
            # ------------------------------------------------

            release_reserved_stock(order)

            logger.info(
                "Released reserved stock for order %s.",
                order.order_number,
            )

            return {
                "success": True,
                "order_id": str(order.id),
                "message": "Reserved stock released.",
            }

    except Order.DoesNotExist:

        logger.error(
            "Order %s not found.",
            order_id,
        )

        return {
            "success": False,
            "message": "Order not found.",
        }

    except Exception:

        logger.exception(
            "Failed to release stock for order %s.",
            order_id,
        )

        raise


# ============================================================
# DEDUCT STOCK AFTER PAYMENT
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def deduct_order_stock(
    self,
    order_id,
):
    """
    Convert reserved stock into actual stock deduction.

    This should happen after successful payment / order
    confirmation.
    """

    try:

        with transaction.atomic():

            order = (
                Order.objects
                .select_for_update()
                .get(pk=order_id)
            )

            # ------------------------------------------------
            # Payment check
            # ------------------------------------------------

            if (
                order.payment_status
                != Order.PaymentStatus.PAID
            ):

                logger.warning(
                    "Cannot deduct stock for unpaid order %s.",
                    order.order_number,
                )

                return {
                    "success": False,
                    "message": "Order is not paid.",
                }

            # ------------------------------------------------
            # Prevent deduction for cancelled order
            # ------------------------------------------------

            if (
                order.status
                == Order.OrderStatus.CANCELLED
            ):

                logger.warning(
                    "Cannot deduct stock for cancelled order %s.",
                    order.order_number,
                )

                return {
                    "success": False,
                    "message": "Order is cancelled.",
                }

            # ------------------------------------------------
            # Process each order item
            # ------------------------------------------------

            for item in (
                order.items
                .select_related("inventory")
                .all()
            ):

                inventory = (
                    ProductInventory.objects
                    .select_for_update()
                    .get(
                        pk=item.inventory_id
                    )
                )

                # --------------------------------------------
                # Validate reservation
                # --------------------------------------------

                if not hasattr(
                    inventory,
                    "reserved_qty",
                ):

                    raise ValueError(
                        "ProductInventory must have "
                        "reserved_qty."
                    )

                if (
                    inventory.reserved_qty
                    < item.quantity
                ):

                    raise ValueError(
                        f"Insufficient reserved stock "
                        f"for {item.product_name_en}."
                    )

                # --------------------------------------------
                # Validate physical stock
                # --------------------------------------------

                if (
                    inventory.stock_qty
                    < item.quantity
                ):

                    raise ValueError(
                        f"Insufficient stock for "
                        f"{item.product_name_en}."
                    )

                # --------------------------------------------
                # Deduct physical stock
                # --------------------------------------------

                inventory.stock_qty -= item.quantity

                # --------------------------------------------
                # Remove reservation
                # --------------------------------------------

                inventory.reserved_qty -= item.quantity

                inventory.save(
                    update_fields=[
                        "stock_qty",
                        "reserved_qty",
                        "updated_at",
                    ]
                )

            logger.info(
                "Stock successfully deducted for order %s.",
                order.order_number,
            )

            return {
                "success": True,
                "order_id": str(order.id),
                "message": "Order stock deducted.",
            }

    except Order.DoesNotExist:

        logger.error(
            "Order %s not found.",
            order_id,
        )

        return {
            "success": False,
            "message": "Order not found.",
        }

    except Exception:

        logger.exception(
            "Failed to deduct stock for order %s.",
            order_id,
        )

        raise


# ============================================================
# CONFIRM PAID ORDER
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def confirm_paid_order(
    self,
    order_id,
):
    """
    Confirm a successfully paid order and deduct its stock.

    Flow:

        PENDING_PAYMENT
              ↓
            PAID
              ↓
          CONFIRMED
              ↓
          stock deducted
    """

    try:

        with transaction.atomic():

            order = (
                Order.objects
                .select_for_update()
                .get(pk=order_id)
            )

            # ------------------------------------------------
            # Payment must be successful
            # ------------------------------------------------

            if (
                order.payment_status
                != Order.PaymentStatus.PAID
            ):

                return {
                    "success": False,
                    "message": "Order is not paid.",
                }

            # ------------------------------------------------
            # Don't confirm cancelled order
            # ------------------------------------------------

            if (
                order.status
                == Order.OrderStatus.CANCELLED
            ):

                return {
                    "success": False,
                    "message": "Order is cancelled.",
                }

            # ------------------------------------------------
            # Confirm order
            # ------------------------------------------------

            if (
                order.status
                == Order.OrderStatus.PENDING_PAYMENT
            ):

                order.status = Order.OrderStatus.CONFIRMED

                order.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            logger.info(
                "Order %s confirmed.",
                order.order_number,
            )

        # ----------------------------------------------------
        # Deduct stock outside the previous lock
        # ----------------------------------------------------

        return deduct_order_stock.delay(
            str(order.id)
        ).id

    except Order.DoesNotExist:

        logger.error(
            "Order %s not found.",
            order_id,
        )

        return {
            "success": False,
            "message": "Order not found.",
        }

    except Exception:

        logger.exception(
            "Failed to confirm order %s.",
            order_id,
        )

        raise