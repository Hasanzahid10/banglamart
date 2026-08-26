import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models

from .Servicearea import ServiceArea


# =========================================================
# DARK STORE
# =========================================================
class DarkStore(models.Model):
    """
    Physical dark store / fulfillment center.

    Example:

        ServiceArea: Rangpur
        DarkStore: Rangpur Central Dark Store
        Code: RGP-DS-001
    """

    service_area = models.ForeignKey(
        ServiceArea,
        on_delete=models.PROTECT,
        related_name="dark_stores",
    )

    name = models.CharField(
        max_length=255,
    )

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    address = models.TextField()

    contact_number = models.CharField(
        max_length=20,
    )

    # Optional physical location of the dark store.
    # Requires PostGIS.
    location = gis_models.PointField(
        srid=4326,
        geography=True,
        null=True,
        blank=True,
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
        ordering = ["service_area", "name"]

        indexes = [
            models.Index(
                fields=["service_area", "is_active"],
            ),
            models.Index(
                fields=["code"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.name} - "
            f"{self.service_area.name} "
            f"({self.code})"
        )


# =========================================================
# DARK STORE MANAGER
# =========================================================
class DarkStoreManager(models.Model):
    """
    Defines which users/admin/staff are allowed
    to manage a particular dark store.
    """

    dark_store = models.ForeignKey(
        DarkStore,
        on_delete=models.CASCADE,
        related_name="managers",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="managed_dark_stores",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dark_store", "user"],
                name="unique_dark_store_manager",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "is_active"],
            ),
            models.Index(
                fields=["dark_store", "is_active"],
            ),
        ]

        ordering = ["dark_store", "user"]

    def __str__(self):
        return (
            f"{self.user} -> "
            f"{self.dark_store}"
        )


# =========================================================
# DELIVERY ZONE
# =========================================================
class DeliveryZone(models.Model):
    """
    Geographic delivery boundary of a dark store.

    Example:

        Dark Store:
            Rangpur Central Dark Store

        Zone:
            Rangpur Central

        Boundary:
            GIS Polygon
    """

    dark_store = models.ForeignKey(
        DarkStore,
        on_delete=models.CASCADE,
        related_name="delivery_zones",
    )

    name = models.CharField(
        max_length=100,
    )

    # Actual delivery boundary.
    #
    # Example:
    # Rangpur Central -> polygon around the serviceable area.
    boundary = gis_models.PolygonField(
        srid=4326,
        geography=True,
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
        ordering = ["dark_store", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["dark_store", "name"],
                name="unique_delivery_zone_per_store",
            ),
        ]

        indexes = [
            models.Index(
                fields=["dark_store", "is_active"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.name} - "
            f"{self.dark_store.name}"
        )


# =========================================================
# DELIVERY SLOT
# =========================================================
class DeliverySlot(models.Model):
    """
    Delivery time window offered by a dark store.

    Example:

        10:00 - 12:00
        12:00 - 14:00
        14:00 - 16:00
    """

    dark_store = models.ForeignKey(
        DarkStore,
        on_delete=models.CASCADE,
        related_name="delivery_slots",
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    max_orders = models.PositiveIntegerField(
        default=10,
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
        ordering = ["dark_store", "start_time"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    end_time__gt=models.F("start_time")
                ),
                name="delivery_slot_end_after_start",
            ),
        ]

        indexes = [
            models.Index(
                fields=["dark_store", "is_active"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.dark_store.name}: "
            f"{self.start_time} - {self.end_time}"
        )


# =========================================================
# DELIVERY ORDER
# =========================================================
class DeliveryOrder(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Routing"
        ASSIGNED = "assigned", "Assigned to Dark Store"
        PACKING = "packing", "Packing at Dark Store"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for Delivery"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Delivery Failed"
        CANCELLED = "cancelled", "Cancelled"

    # =====================================================
    # ID
    # =====================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    tracking_number = models.CharField(
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
        on_delete=models.CASCADE,
        related_name="delivery_orders",
    )

    # =====================================================
    # DARK STORE
    # =====================================================

    dark_store = models.ForeignKey(
        DarkStore,
        on_delete=models.PROTECT,
        related_name="delivery_orders",
    )

    # =====================================================
    # DELIVERY ZONE
    # =====================================================

    delivery_zone = models.ForeignKey(
        DeliveryZone,
        on_delete=models.PROTECT,
        related_name="delivery_orders",
        null=True,
        blank=True,
    )

    # =====================================================
    # RIDER
    # =====================================================

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_delivery_orders",
        limit_choices_to={"role": "RIDER"},
    )

    # =====================================================
    # SAVED ADDRESS
    # =====================================================

    saved_address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_orders",
    )

    # =====================================================
    # ADDRESS SNAPSHOT
    # =====================================================

    recipient_name = models.CharField(
        max_length=150,
    )

    recipient_phone = models.CharField(
        max_length=20,
    )

    street_address = models.TextField()

    area = models.CharField(
        max_length=100,
    )

    city = models.CharField(
        max_length=100,
    )

    # =====================================================
    # CUSTOMER LOCATION SNAPSHOT
    # =====================================================

    location = gis_models.PointField(
        srid=4326,
        geography=True,
        null=True,
        blank=True,
    )

    # =====================================================
    # DELIVERY INFORMATION
    # =====================================================

    delivery_slot = models.ForeignKey(
        DeliverySlot,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="delivery_orders",
    )

    distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    delivery_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    # =====================================================
    # STATUS
    # =====================================================

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    picked_up_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
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
                fields=["user", "status"],
            ),
            models.Index(
                fields=["dark_store", "status"],
            ),
            models.Index(
                fields=["delivery_zone", "status"],
            ),
            models.Index(
                fields=["rider", "status"],
            ),
            models.Index(
                fields=["created_at"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.tracking_number} - "
            f"{self.dark_store.code} "
            f"({self.status})"
        )