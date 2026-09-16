from django.db import models

from catalog.models import Category


# =========================================================
# GLOBAL PRODUCT
# =========================================================

class Product(models.Model):
    """
    Global product/catalog information.

    A Product is NOT tied to a specific dark store.

    Example:

        Product:
            Rice 5kg

        Inventory:
            Rangpur DS-001 -> 50
            Rangpur DS-002 -> 20
            Bogura DS-001  -> 10
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )

    name_en = models.CharField(
        max_length=255,
        db_index=True,
    )

    name_bn = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Globally unique product SKU.",
    )

    brand = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
    )

    unit = models.CharField(
        max_length=50,
        help_text="Example: 1 kg, 500 ml, 1 pc.",
    )

    # -----------------------------------------------------
    # GLOBAL BASE PRICE
    # -----------------------------------------------------

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=(
            "Default product price. "
            "A dark store may override this price."
        ),
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )

    description = models.TextField(
        blank=True,
        null=True,
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

        indexes = [
            models.Index(
                fields=[
                    "category",
                    "is_active",
                ],
            ),
            models.Index(
                fields=[
                    "brand",
                    "is_active",
                ],
            ),
            models.Index(
                fields=[
                    "base_price",
                ],
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name_en) if self.name_en else "product"
            slug = base_slug
            count = 1
            qs = Product.objects.filter(slug=slug)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.exists():
                slug = f"{base_slug}-{count}"
                count += 1
                qs = Product.objects.filter(slug=slug)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
            self.slug = slug

        if not self.sku:
            import uuid
            self.sku = f"SKU-MB-{uuid.uuid4().hex[:8].upper()}"

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.name_en} ({self.unit})"
        )


# =========================================================
# PRODUCT GALLERY IMAGES
# =========================================================

class ProductImage(models.Model):
    """
    Multiple gallery images for a Product.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="products/gallery/",
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"Gallery Image for {self.product.name_en}"


# =========================================================
# DARK STORE INVENTORY
# =========================================================

class ProductInventory(models.Model):
    """
    Store-specific inventory.

    One product can exist in many dark stores.

    The inventory controls:

        - stock
        - store-specific price
        - availability
        - low-stock threshold

    Example:

        Coca-Cola 1L

            Rangpur DS-001
                stock = 50
                price = 80

            Rangpur DS-002
                stock = 20
                price = 82

            Bogura DS-001
                stock = 0
                price = 80
    """

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.CASCADE,
        related_name="inventories",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventories",
    )

    # -----------------------------------------------------
    # STOCK
    # -----------------------------------------------------

    stock_qty = models.PositiveIntegerField(
        default=0,
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        help_text=(
            "Admin/store manager receives a low-stock "
            "warning when stock reaches this amount."
        ),
    )

    # -----------------------------------------------------
    # STORE PRICE
    # -----------------------------------------------------

    store_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Store-specific selling price. "
            "Leave empty to use Product.base_price."
        ),
    )

    # -----------------------------------------------------
    # AVAILABILITY
    # -----------------------------------------------------

    is_available = models.BooleanField(
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
        ordering = ["-updated_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dark_store",
                    "product",
                ],
                name="unique_product_per_dark_store",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "dark_store",
                    "product",
                ],
            ),
            models.Index(
                fields=[
                    "product",
                    "is_available",
                ],
            ),
            models.Index(
                fields=[
                    "dark_store",
                    "is_available",
                ],
            ),
            models.Index(
                fields=[
                    "dark_store",
                    "stock_qty",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.product.name_en} - "
            f"{self.dark_store.name} "
            f"(Qty: {self.stock_qty})"
        )

    # =====================================================
    # SELLING PRICE
    # =====================================================

    @property
    def selling_price(self):
        """
        Return the actual selling price for this store.
        """

        if self.store_price is not None:
            return self.store_price

        return self.product.base_price

    # =====================================================
    # STOCK STATUS
    # =====================================================

    @property
    def in_stock(self):
        """
        True when the product can currently be sold.
        """

        return (
            self.is_available
            and self.stock_qty > 0
        )

    @property
    def is_low_stock(self):
        """
        True when stock reaches the configured
        low-stock threshold.
        """

        return (
            self.stock_qty <=
            self.low_stock_threshold
        )