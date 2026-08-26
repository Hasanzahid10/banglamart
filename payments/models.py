import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class PaymentTransaction(models.Model):
    """
    Payment transaction for an Order.

    One Order can have multiple payment transactions.

    Example:

        Order
          ├── PaymentTransaction (failed)
          ├── PaymentTransaction (failed)
          └── PaymentTransaction (success)

    This is useful when a customer retries an online payment.
    """

    # =========================================================
    # GATEWAYS
    # =========================================================

    class Gateway(models.TextChoices):

        BKASH = (
            "bkash",
            "bKash",
        )

        NAGAD = (
            "nagad",
            "Nagad",
        )

        SSLCOMMERZ = (
            "sslcommerz",
            "SSLCommerz",
        )

        COD = (
            "cod",
            "Cash on Delivery",
        )

    # =========================================================
    # STATUS
    # =========================================================

    class TransactionStatus(models.TextChoices):

        PENDING = (
            "pending",
            "Pending",
        )

        SUCCESS = (
            "success",
            "Success",
        )

        FAILED = (
            "failed",
            "Failed",
        )

        CANCELLED = (
            "cancelled",
            "Cancelled",
        )

        REFUNDED = (
            "refunded",
            "Refunded",
        )

        PARTIALLY_REFUNDED = (
            "partially_refunded",
            "Partially Refunded",
        )

    # =========================================================
    # PRIMARY KEY
    # =========================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # =========================================================
    # INTERNAL TRANSACTION ID
    # =========================================================

    transaction_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
    )

    # =========================================================
    # ORDER
    # =========================================================

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )

    # =========================================================
    # CUSTOMER
    # =========================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )

    # =========================================================
    # PAYMENT METHOD
    # =========================================================

    gateway = models.CharField(
        max_length=20,
        choices=Gateway.choices,
        db_index=True,
    )

    # =========================================================
    # TRANSACTION STATUS
    # =========================================================

    status = models.CharField(
        max_length=30,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
        db_index=True,
    )

    # =========================================================
    # AMOUNT
    # =========================================================

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
    )

    currency = models.CharField(
        max_length=10,
        default="BDT",
    )

    # =========================================================
    # GATEWAY REFERENCE
    # =========================================================

    gateway_transaction_id = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        db_index=True,
    )

    gateway_reference = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        db_index=True,
    )

    # =========================================================
    # GATEWAY RESPONSE
    # =========================================================

    gateway_response = models.JSONField(
        blank=True,
        null=True,
    )

    # Raw callback/request data if required
    callback_data = models.JSONField(
        blank=True,
        null=True,
    )

    # =========================================================
    # PAYMENT TIMESTAMPS
    # =========================================================

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =========================================================
    # REFUND
    # =========================================================

    refunded_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
        ],
    )

    refund_reference = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    refund_reason = models.TextField(
        blank=True,
        null=True,
    )

    # =========================================================
    # TIMESTAMPS
    # =========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "order",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "user",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "gateway",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "created_at",
                ],
            ),

            models.Index(
                fields=[
                    "gateway_transaction_id",
                ],
            ),
        ]

        constraints = [

            models.CheckConstraint(
                condition=models.Q(
                    amount__gte=0
                ),
                name="payment_amount_gte_zero",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    refunded_amount__gte=0
                ),
                name="refunded_amount_gte_zero",
            ),
        ]

    # =========================================================
    # SAVE
    # =========================================================

    def save(self, *args, **kwargs):

        if not self.transaction_id:

            self.transaction_id = (
                f"TXN-{uuid.uuid4().hex.upper()}"
            )

        super().save(
            *args,
            **kwargs,
        )

    # =========================================================
    # HELPERS
    # =========================================================

    def mark_success(
        self,
        gateway_transaction_id=None,
        gateway_response=None,
    ):
        """
        Mark payment as successful.

        This should only be called after the real
        payment gateway has been verified.
        """

        self.status = (
            self.TransactionStatus.SUCCESS
        )

        self.paid_at = timezone.now()

        if gateway_transaction_id:
            self.gateway_transaction_id = (
                gateway_transaction_id
            )

        if gateway_response is not None:
            self.gateway_response = (
                gateway_response
            )

        self.save(
            update_fields=[
                "status",
                "paid_at",
                "gateway_transaction_id",
                "gateway_response",
                "updated_at",
            ]
        )

    def mark_failed(
        self,
        gateway_response=None,
    ):
        """
        Mark payment as failed.
        """

        self.status = (
            self.TransactionStatus.FAILED
        )

        self.failed_at = timezone.now()

        if gateway_response is not None:
            self.gateway_response = (
                gateway_response
            )

        self.save(
            update_fields=[
                "status",
                "failed_at",
                "gateway_response",
                "updated_at",
            ]
        )

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):

        return (
            f"{self.gateway} | "
            f"{self.transaction_id} | "
            f"{self.amount} {self.currency} | "
            f"{self.status}"
        )