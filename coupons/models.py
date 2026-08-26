import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Coupon(models.Model):

    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "Percentage Discount"
        FLAT = "FLAT", "Flat Amount Discount"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # --------------------------------------------------
    # BASIC
    # --------------------------------------------------

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    # --------------------------------------------------
    # DISCOUNT
    # --------------------------------------------------

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.FLAT,
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    # --------------------------------------------------
    # ORDER CONDITIONS
    # --------------------------------------------------

    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    # --------------------------------------------------
    # USAGE LIMITS
    # --------------------------------------------------

    total_usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    per_user_limit = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
        ],
    )

    times_used = models.PositiveIntegerField(
        default=0,
        editable=False,
    )

    # --------------------------------------------------
    # REGIONAL / DARK STORE
    # --------------------------------------------------
    # Keep NULL = platform-wide coupon.
    # Later you can assign a coupon to a specific
    # DarkStore or region.

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coupons",
    )

    # --------------------------------------------------
    # VALIDITY
    # --------------------------------------------------

    start_date = models.DateTimeField(
        default=timezone.now,
    )

    end_date = models.DateTimeField()

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    # --------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "code",
                    "is_active",
                ],
            ),
            models.Index(
                fields=[
                    "dark_store",
                    "is_active",
                ],
            ),
            models.Index(
                fields=[
                    "start_date",
                    "end_date",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.code} "
            f"({self.get_discount_type_display()})"
        )

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError({
                "end_date": (
                    "End date must be later than start date."
                )
            })

        if (
            self.discount_type
            == self.DiscountType.PERCENTAGE
            and self.discount_value > Decimal("100")
        ):
            raise ValidationError({
                "discount_value": (
                    "Percentage discount cannot exceed 100%."
                )
            })

        if (
            self.max_discount_amount is not None
            and self.discount_type
            != self.DiscountType.PERCENTAGE
        ):
            raise ValidationError({
                "max_discount_amount": (
                    "Maximum discount amount is only "
                    "applicable to percentage coupons."
                )
            })

    # --------------------------------------------------
    # CURRENT VALIDITY
    # --------------------------------------------------

    @property
    def is_valid_now(self):
        now = timezone.now()

        if not self.is_active:
            return False, "Coupon is inactive."

        if self.start_date > now:
            return False, "Coupon is not yet active."

        if self.end_date <= now:
            return False, "Coupon has expired."

        if (
            self.total_usage_limit is not None
            and self.times_used >= self.total_usage_limit
        ):
            return False, "Coupon usage limit reached."

        return True, "Coupon is valid."

    # --------------------------------------------------
    # DISCOUNT CALCULATION
    # --------------------------------------------------

    def calculate_discount(self, order_amount):
        order_amount = Decimal(str(order_amount))

        if order_amount <= Decimal("0.00"):
            return Decimal("0.00")

        if order_amount < self.min_order_amount:
            return Decimal("0.00")

        if self.discount_type == self.DiscountType.FLAT:
            discount = min(
                self.discount_value,
                order_amount,
            )

        else:
            discount = (
                order_amount
                * self.discount_value
                / Decimal("100")
            )

            if self.max_discount_amount is not None:
                discount = min(
                    discount,
                    self.max_discount_amount,
                )

        return discount.quantize(
            Decimal("0.01")
        )


class CouponUsage(models.Model):
    """
    Records each successful coupon redemption.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.PROTECT,
        related_name="usages",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coupon_usages",
    )

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="coupon_redemption",
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    used_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-used_at"]

        indexes = [
            models.Index(
                fields=[
                    "coupon",
                    "user",
                ],
            ),
            models.Index(
                fields=[
                    "user",
                    "used_at",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.user} used "
            f"{self.coupon.code}"
        )