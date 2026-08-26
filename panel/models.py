import uuid

from django.conf import settings
from django.db import models


class Region(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Example: Rangpur Region",
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Example: RGP-01",
    )

    city = models.CharField(
        max_length=100,
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
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class RegionAdminProfile(models.Model):
    """
    Regional Admin profile.

    Each Admin belongs to exactly ONE region.
    Super Admin is handled separately.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="region_profile",
    )

    assigned_region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="regional_admins",
    )

    can_manage_stock = models.BooleanField(
        default=True,
    )

    can_assign_riders = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.phone_number or self.user.email} "
            f"-> {self.assigned_region.name}"
        )