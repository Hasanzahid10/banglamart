import uuid
from django.conf import settings
from django.db import models


class DeviceToken(models.Model):
    class DeviceType(models.TextChoices):
        ANDROID = "ANDROID", "Android"
        IOS = "IOS", "iOS"
        WEB = "WEB", "Web"

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
        serialize=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    token = models.TextField(unique=True)
    device_type = models.CharField(
        max_length=10,
        choices=DeviceType.choices,
        default=DeviceType.ANDROID,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="notificatio_user_id_f0e72c_idx",
            ),
            models.Index(
                fields=["device_type", "is_active"],
                name="notificatio_device__3cd68e_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.device_type}"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        ORDER_STATUS = "order_status", "Order Update"
        PAYMENT = "payment", "Payment Notice"
        PROMOTION = "promotion", "Promotional / Deal"
        DELIVERY = "delivery", "Delivery Update"
        SYSTEM = "system", "System Notice"

    class TargetType(models.TextChoices):
        ORDER = "order", "Order"
        PRODUCT = "product", "Product"
        PROMOTION = "promotion", "Promotion"
        PAYMENT = "payment", "Payment"
        DELIVERY = "delivery", "Delivery"
        NONE = "none", "None"

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
        serialize=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True,
    )
    title = models.CharField(max_length=150)
    body = models.TextField()
    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
        default=TargetType.NONE,
    )
    target_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    is_read = models.BooleanField(
        default=False,
        db_index=True,
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "created_at"],
                name="notificatio_user_id_8a7c6b_idx",
            ),
            models.Index(
                fields=["user", "notification_type", "created_at"],
                name="notificatio_user_id_ef3643_idx",
            ),
        ]

    def __str__(self):
        return self.title