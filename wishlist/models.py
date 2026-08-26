import uuid

from django.conf import settings
from django.db import models


class Wishlist(models.Model):
    """
    One wishlist per customer.

    Wishlist is global to the customer and does not depend
    on a DarkStore. Store-specific availability is checked
    when the product is added to cart.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        name = (
            self.user.get_full_name()
            or getattr(
                self.user,
                "phone_number",
                None,
            )
            or getattr(
                self.user,
                "email",
                None,
            )
            or str(self.user.id)
        )

        return f"Wishlist of {name}"

    @property
    def total_items(self):
        return self.items.count()


class WishlistItem(models.Model):
    """
    Product saved in a customer's wishlist.

    Product is global. DarkStore availability/pricing
    should be checked when the customer adds it to cart.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="wishlist_items",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "wishlist",
                    "product",
                ],
                name="unique_product_per_wishlist",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "wishlist",
                    "product",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.product.name_en} "
            f"in Wishlist {self.wishlist_id}"
        )