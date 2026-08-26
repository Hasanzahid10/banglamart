import uuid

from django.conf import settings
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models


class ProductReview(models.Model):
    """
    Customer review for a product.

    Reviews are linked to the actual order used for
    verification and optionally to the Dark Store
    from which the product was purchased.

    The Product itself is global, while the Dark Store
    represents the customer's fulfillment location.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # =========================================================
    # PRODUCT
    # =========================================================

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    # =========================================================
    # CUSTOMER
    # =========================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_reviews",
    )

    # =========================================================
    # ORDER
    # =========================================================

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_reviews",
    )

    # =========================================================
    # DARK STORE
    # =========================================================
    # Historical fulfillment store.
    #
    # Product is global, but the customer may purchase
    # it from different Dark Stores.

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_reviews",
    )

    # =========================================================
    # RATING
    # =========================================================

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        help_text="Rating from 1 to 5 stars.",
    )

    # =========================================================
    # REVIEW CONTENT
    # =========================================================

    title = models.CharField(
        max_length=150,
        blank=True,
    )

    comment = models.TextField(
        blank=True,
    )

    # =========================================================
    # VERIFICATION / MODERATION
    # =========================================================

    is_verified_purchase = models.BooleanField(
        default=False,
        db_index=True,
    )

    is_approved = models.BooleanField(
        default=True,
        db_index=True,
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
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "product",
                    "is_approved",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "user",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "dark_store",
                    "is_approved",
                ]
            ),
            models.Index(
                fields=[
                    "rating",
                ]
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "product",
                    "user",
                    "order",
                ],
                name="unique_product_review_per_order",
            ),
        ]

    def __str__(self):
        return (
            f"{self.rating}★ "
            f"Review for {self.product.name_en}"
        )


class ReviewImage(models.Model):
    """
    Images uploaded by a customer with a review.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="reviews/%Y/%m/",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"Photo for review {self.review_id}"
        )