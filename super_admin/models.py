import uuid

from django.db import models


class GlobalPlatformConfig(models.Model):
    """
    Global platform configuration.

    Managed only by Super Admin.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    platform_name = models.CharField(
        max_length=100,
        default="BanglaMart",
    )

    maintenance_mode = models.BooleanField(
        default=False,
        help_text="Disable customer checkout during maintenance.",
    )

    # =========================================================
    # DELIVERY / FINANCIAL RULES
    # =========================================================

    base_delivery_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=30.00,
    )

    free_delivery_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.00,
    )

    # =========================================================
    # SUPPORT
    # =========================================================

    support_phone = models.CharField(
        max_length=20,
        default="+8801700000000",
    )

    support_email = models.EmailField(
        default="support@banglamart.com",
    )

    # =========================================================
    # TIMESTAMP
    # =========================================================

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def save(self, *args, **kwargs):
        # Singleton configuration
        self.pk = uuid.UUID(
            "00000000-0000-0000-0000-000000000001"
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.platform_name} Global Config "
            f"({'MAINTENANCE' if self.maintenance_mode else 'OPERATIONAL'})"
        )


class SystemFeatureFlag(models.Model):
    """
    Global feature switches.

    Managed only by Super Admin.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Example: ENABLE_BKASH_PAYMENT",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    description = models.TextField(
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return (
            f"{self.name} -> "
            f"{'ENABLED' if self.is_enabled else 'DISABLED'}"
        )