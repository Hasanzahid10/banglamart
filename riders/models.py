import uuid

from django.conf import settings
from django.db import models


class RiderProfile(models.Model):
    """
    Profile for a delivery rider.

    Authentication information stays in the custom User model.

    A rider is assigned to a DarkStore, but the rider can later
    be reassigned to another DarkStore.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rider_profile",
    )

    # --------------------------------------------------
    # DARK STORE
    # --------------------------------------------------

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rider_profiles",
    )

    # --------------------------------------------------
    # RIDER INFORMATION
    # --------------------------------------------------

    vehicle_type = models.CharField(
        max_length=50,
        default="Bicycle",
        help_text="Example: Bicycle, Bike, Scooter",
    )

    license_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    # --------------------------------------------------
    # AVAILABILITY
    # --------------------------------------------------

    is_available = models.BooleanField(
        default=True,
        db_index=True,
    )

    is_on_duty = models.BooleanField(
        default=False,
        db_index=True,
    )

    # --------------------------------------------------
    # CURRENT LOCATION
    # --------------------------------------------------

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    last_location_update = models.DateTimeField(
        null=True,
        blank=True,
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
                    "dark_store",
                    "is_available",
                    "is_on_duty",
                ],
            ),
            models.Index(
                fields=[
                    "dark_store",
                    "is_on_duty",
                ],
            ),
        ]

    def __str__(self):
        name = self.user.get_full_name()

        if not name:
            name = (
                getattr(
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

        duty_status = (
            "On Duty"
            if self.is_on_duty
            else "Off Duty"
        )

        return (
            f"Rider: {name} "
            f"({duty_status})"
        )

    @property
    def has_location(self):
        return (
            self.latitude is not None
            and self.longitude is not None
        )
    

class DeliveryTask(models.Model):

    class TaskStatus(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        ACCEPTED = "accepted", "Accepted by Rider"
        PICKED_UP = "picked_up", "Picked Up from Dark Store"
        ARRIVED = "arrived", "Arrived at Destination"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Delivery Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # --------------------------------------------------
    # DELIVERY ORDER
    # --------------------------------------------------

    delivery_order = models.OneToOneField(
        "logistics.DeliveryOrder",
        on_delete=models.CASCADE,
        related_name="delivery_task",
    )

    # --------------------------------------------------
    # DARK STORE
    # --------------------------------------------------

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.PROTECT,
        related_name="delivery_tasks",
    )

    # --------------------------------------------------
    # RIDER
    # --------------------------------------------------

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="delivery_tasks",
        limit_choices_to={
            "role": "RIDER",
        },
    )

    # --------------------------------------------------
    # STATUS
    # --------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.ASSIGNED,
        db_index=True,
    )

    failure_reason = models.TextField(
        blank=True,
        null=True,
    )

    # --------------------------------------------------
    # TIME TRACKING
    # --------------------------------------------------

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    picked_up_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    arrived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
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
                    "rider",
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
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "assigned_at",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"Delivery Task "
            f"{self.delivery_order.tracking_number} "
            f"-> {self.rider} "
            f"({self.status})"
        )