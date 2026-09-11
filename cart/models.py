import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cart(models.Model):
    """
    One active shopping cart per customer.

    A cart belongs to one DarkStore.

    The DarkStore is selected based on the customer's
    delivery/service location.

    Example:

        Customer
            ↓
        Cart
            ↓
        Rangpur Dark Store #1
            ↓
        CartItems
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # =========================================================
    # CUSTOMER
    # =========================================================

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    # =========================================================
    # DARK STORE
    # =========================================================

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="carts",
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

    class Meta:
        ordering = ["-updated_at"]

        indexes = [
            models.Index(
                fields=[
                    "dark_store",
                    "updated_at",
                ]
            ),
        ]

    def __str__(self):
        if self.dark_store:
            return (
                f"Cart of {self.user} "
                f"- {self.dark_store.name}"
            )

        return f"Cart of {self.user}"

    # =========================================================
    # TOTALS
    # =========================================================

    @property
    def total_price(self):
        return sum(
            item.subtotal
            for item in self.items.all()
        )

    @property
    def total_items(self):
        return sum(
            item.quantity
            for item in self.items.all()
        )

    @property
    def is_empty(self):
        return not self.items.exists()


class CartItem(models.Model):
    """
    Product inside a customer's cart.

    IMPORTANT:

    CartItem points to ProductInventory rather than only
    Product.

    ProductInventory tells us:

        Product
        +
        DarkStore
        +
        stock
        +
        store-specific selling price

    Example:

        Rice 5kg
            ↓
        Rangpur Dark Store #1
            ↓
        stock = 50
            ↓
        selling price = 450 BDT
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # =========================================================
    # CART
    # =========================================================

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    # =========================================================
    # INVENTORY
    # =========================================================

    inventory = models.ForeignKey(
        "products.ProductInventory",
        on_delete=models.PROTECT,
        related_name="cart_items",
        null=True,
        blank=True,
    )

    # =========================================================
    # QUANTITY
    # =========================================================

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
        ],
    )

    # =========================================================
    # PRICE SNAPSHOT
    # =========================================================

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
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

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "cart",
                    "inventory",
                ],
                name="unique_inventory_per_cart",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "cart",
                    "inventory",
                ]
            ),
            models.Index(
                fields=[
                    "inventory",
                    "cart",
                ]
            ),
        ]

    # =========================================================
    # PRODUCT
    # =========================================================

    @property
    def product(self):
        """
        Access the global Product through inventory.
        """
        if not self.inventory:
            return None
        return self.inventory.product

    # =========================================================
    # DARK STORE
    # =========================================================

    @property
    def dark_store(self):
        """
        DarkStore that owns this inventory.
        """
        if not self.inventory:
            return None
        return self.inventory.dark_store

    # =========================================================
    # CURRENT SELLING PRICE
    # =========================================================

    @property
    def current_selling_price(self):
        """
        Current price from ProductInventory.

        This can be different from unit_price because
        unit_price is the price captured when the item
        was added/updated in the cart.
        """
        if not self.inventory:
            return self.unit_price
        return self.inventory.selling_price

    # =========================================================
    # SUBTOTAL
    # =========================================================

    @property
    def subtotal(self):
        if self.unit_price is None or self.quantity is None:
            return 0.00
        return (
            self.unit_price *
            self.quantity
        )

    # =========================================================
    # STOCK
    # =========================================================

    @property
    def in_stock(self):
        if not self.inventory:
            return False
        return (
            self.inventory.stock_qty
            >= self.quantity
            and
            self.inventory.is_available
        )

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        product_name = self.inventory.product.name_en if self.inventory else "Unknown Product"
        return (
            f"{self.quantity}x "
            f"{product_name} "
            f"in Cart {self.cart.id}"
        )


class GuestCart(models.Model):
    """
    Tracks Guest sessions, cart activity, and guest to registered user conversion.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active Guest Cart'),
        ('CONVERTED', 'Converted to Registered User'),
        ('ABANDONED', 'Abandoned Cart'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guest_id = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guest_carts"
    )
    city = models.CharField(max_length=100, default='Dhaka')
    ip_address = models.CharField(max_length=100, null=True, blank=True)
    device_info = models.CharField(max_length=255, null=True, blank=True)
    browser = models.CharField(max_length=100, null=True, blank=True)
    os = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Guest Cart ({self.guest_id}) - {self.status}"

    @property
    def total_price(self):
        return sum(float(item.subtotal) for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class GuestCartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guest_cart = models.ForeignKey(GuestCart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        related_name="guest_cart_items",
        null=True,
        blank=True
    )
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        if self.unit_price is None or self.quantity is None:
            return 0.00
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product_name} in Guest Cart {self.guest_cart.guest_id}"