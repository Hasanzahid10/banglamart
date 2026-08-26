from django.db import models
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey


class Category(MPTTModel):
    """
    Hierarchical product category.

    Example:

    Fruits & Vegetables
    ├── Fresh Fruits
    │   ├── Mango
    │   └── Banana
    └── Fresh Vegetables
        ├── Potato
        └── Tomato
    """

    name_en = models.CharField(
        max_length=150,
        help_text="Example: Fruits & Vegetables",
    )

    name_bn = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Example: ফল ও সবজি",
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        db_index=True,
        blank=True,
    )

    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        db_index=True,
    )

    # =========================================================
    # UI / DISPLAY
    # =========================================================

    icon = models.ImageField(
        upload_to="categories/icons/",
        blank=True,
        null=True,
    )

    banner = models.ImageField(
        upload_to="categories/banners/",
        blank=True,
        null=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    is_featured = models.BooleanField(
        default=False,
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
    # MPTT
    # =========================================================

    class MPTTMeta:
        order_insertion_by = [
            "display_order",
            "name_en",
        ]

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = [
            "tree_id",
            "lft",
        ]

    # =========================================================
    # SAVE
    # =========================================================

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name_en)

        super().save(*args, **kwargs)

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        if self.parent:
            return (
                f"{self.parent.name_en} -> "
                f"{self.name_en}"
            )

        return self.name_en