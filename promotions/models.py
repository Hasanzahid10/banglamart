import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Banner(models.Model):

    class TargetType(models.TextChoices):
        PRODUCT = "product", "Product"
        CATEGORY = "category", "Category"
        FLASH_SALE = "flash_sale", "Flash Sale"
        EXTERNAL = "external", "External URL"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    title = models.CharField(
        max_length=150,
    )

    subtitle = models.CharField(
        max_length=255,
        blank=True,
    )

    image = models.ImageField(
        upload_to="banners/%Y/%m/",
    )

    # --------------------------------------------------
    # CLICK / NAVIGATION
    # --------------------------------------------------

    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
        default=TargetType.PRODUCT,
    )

    target_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Product ID, Category ID, Flash Sale ID "
            "or external URL."
        ),
    )

    # --------------------------------------------------
    # REGIONAL / DARK STORE SCOPE
    # --------------------------------------------------

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="banners",
        help_text=(
            "Empty means this banner is global. "
            "Otherwise it belongs to this dark store."
        ),
    )

    display_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    start_date = models.DateTimeField(
        default=timezone.now,
    )

    end_date = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "dark_store",
                    "is_active",
                ]
            ),
            models.Index(
                fields=[
                    "start_date",
                    "end_date",
                ]
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_running_now(self):
        now = timezone.now()

        return (
            self.is_active
            and self.start_date <= now <= self.end_date
        )


class FlashSale(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    title = models.CharField(
        max_length=150,
    )

    banner_image = models.ImageField(
        upload_to="flash_sales/%Y/%m/",
        blank=True,
        null=True,
    )

    # --------------------------------------------------
    # REGIONAL / DARK STORE
    # --------------------------------------------------

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="flash_sales",
        help_text=(
            "Empty means global flash sale."
        ),
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-start_time"]

        indexes = [
            models.Index(
                fields=[
                    "dark_store",
                    "is_active",
                ]
            ),
            models.Index(
                fields=[
                    "start_time",
                    "end_time",
                ]
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_running_now(self):
        now = timezone.now()

        return (
            self.is_active
            and self.start_time <= now <= self.end_time
        )


class FlashSaleItem(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    flash_sale = models.ForeignKey(
        FlashSale,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="flash_sale_items",
    )

    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01")
            )
        ],
    )

    stock_allocated = models.PositiveIntegerField(
        default=100,
    )

    stock_sold = models.PositiveIntegerField(
        default=0,
        editable=False,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "flash_sale",
                    "product",
                ],
                name="unique_product_per_flash_sale",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "flash_sale",
                    "is_active",
                ]
            ),
            models.Index(
                fields=[
                    "product",
                    "is_active",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.product} - "
            f"{self.discount_price} BDT"
        )

    @property
    def remaining_stock(self):
        return max(
            self.stock_allocated - self.stock_sold,
            0,
        )

    @property
    def is_sold_out(self):
        return self.remaining_stock <= 0
