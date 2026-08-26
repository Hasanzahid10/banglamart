import uuid

from django.conf import settings
from django.db import models


class Order(models.Model):

    class OrderStatus(models.TextChoices):

        PENDING_PAYMENT = (
            "pending_payment",
            "Pending Payment",
        )

        CONFIRMED = (
            "confirmed",
            "Confirmed",
        )

        PROCESSING = (
            "processing",
            "Packing at Dark Store",
        )

        OUT_FOR_DELIVERY = (
            "out_for_delivery",
            "Out for Delivery",
        )

        DELIVERED = (
            "delivered",
            "Delivered",
        )

        CANCELLED = (
            "cancelled",
            "Cancelled",
        )

    class PaymentStatus(models.TextChoices):

        UNPAID = (
            "unpaid",
            "Unpaid",
        )

        PAID = (
            "paid",
            "Paid",
        )

        REFUNDED = (
            "refunded",
            "Refunded",
        )

        FAILED = (
            "failed",
            "Failed",
        )

    # =====================================================
    # IDENTITY
    # =====================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    order_number = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        editable=False,
    )

    # =====================================================
    # CUSTOMER
    # =====================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    # =====================================================
    # FULFILLMENT DARK STORE
    # =====================================================

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.PROTECT,
        related_name="orders",
    )

    # =====================================================
    # DELIVERY ORDER
    # =====================================================

    delivery_order = models.OneToOneField(
        "logistics.DeliveryOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order",
    )

    # =====================================================
    # STATUS
    # =====================================================

    status = models.CharField(
        max_length=25,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING_PAYMENT,
        db_index=True,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )

    # =====================================================
    # FINANCIALS
    # =====================================================

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    # =====================================================
    # DELIVERY ADDRESS SNAPSHOT
    # =====================================================

    delivery_address_snapshot = models.JSONField(
        help_text=(
            "Customer delivery address captured "
            "at checkout time."
        ),
    )

    # =====================================================
    # CUSTOMER NOTE
    # =====================================================

    note = models.TextField(
        blank=True,
        null=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "user",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "dark_store",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "dark_store",
                    "payment_status",
                ],
            ),

            models.Index(
                fields=[
                    "payment_status",
                ],
            ),

            models.Index(
                fields=[
                    "created_at",
                ],
            ),
        ]

    def __str__(self):

        return (
            f"Order #{self.order_number} - "
            f"{self.status}"
        )

#====================================================
# adding order items here 
#=====================================================
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal


class OrderItem(models.Model):

    # =====================================================
    # ORDER
    # =====================================================

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    # =====================================================
    # INVENTORY
    # =====================================================

    inventory = models.ForeignKey(
        "products.ProductInventory",
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    # =====================================================
    # PRODUCT SNAPSHOT
    # =====================================================

    product_name_en = models.CharField(
        max_length=255,
    )

    product_name_bn = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    sku = models.CharField(
        max_length=100,
    )

    unit = models.CharField(
        max_length=50,
    )

    # =====================================================
    # PRICE SNAPSHOT
    # =====================================================

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
        ],
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    # =====================================================
    # STORE SNAPSHOT
    # =====================================================

    dark_store_name = models.CharField(
        max_length=255,
        blank=True,
    )

    dark_store_code = models.CharField(
        max_length=100,
        blank=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        # -------------------------------------------------
        # SUBTOTAL
        # -------------------------------------------------

        self.subtotal = (
            self.unit_price * self.quantity
        )

        # -------------------------------------------------
        # PRODUCT SNAPSHOT
        # -------------------------------------------------

        if self.inventory_id:

            inventory = self.inventory
            product = inventory.product
            dark_store = inventory.dark_store

            if not self.product_name_en:
                self.product_name_en = (
                    product.name_en
                )

            if not self.product_name_bn:
                self.product_name_bn = (
                    product.name_bn
                )

            if not self.sku:
                self.sku = product.sku

            if not self.unit:
                self.unit = product.unit

            # -------------------------------------------------
            # DARK STORE SNAPSHOT
            # -------------------------------------------------

            if not self.dark_store_name:
                self.dark_store_name = (
                    dark_store.name
                )

            if not self.dark_store_code:
                self.dark_store_code = (
                    dark_store.code
                )

        super().save(*args, **kwargs)

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return (
            f"{self.quantity}x "
            f"{self.product_name_en} "
            f"in Order #{self.order.order_number}"
        )