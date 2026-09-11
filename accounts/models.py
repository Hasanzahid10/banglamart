from django.conf import settings
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models


class UserProfile(models.Model):
    """
    Additional user information.

    Authentication information such as:
    - phone_number
    - email
    - password
    - role
    - verification status

    remains in authentication.User.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
    )

    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
    )

    alternate_phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
    )

    # =========================================================
    # CUSTOMER METRICS
    # These should be read-only through the API.
    # =========================================================

    total_orders = models.PositiveIntegerField(
        default=0,
    )

    loyalty_points = models.PositiveIntegerField(
        default=0,
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
        identifier = (
            self.user.phone_number
            or self.user.email
        )

        return f"Profile of {identifier}"


class Address(models.Model):

    class AddressType(models.TextChoices):
        HOME = "home", "Home"
        WORK = "work", "Work"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    title = models.CharField(
        max_length=50,
        help_text="Example: Home, Office, Parents",
    )

    address_type = models.CharField(
        max_length=10,
        choices=AddressType.choices,
        default=AddressType.HOME,
    )

    # =========================================================
    # ADDRESS
    # =========================================================

    street_address = models.TextField()

    flat_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    floor = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    area = models.CharField(
        max_length=100,
    )

    city = models.CharField(
        max_length=100,
        default="Dhaka",
    )

    # =========================================================
    # LOCATION
    # =========================================================

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        default=23.8103,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        default=90.4125,
        null=True,
        blank=True,
    )

    # =========================================================
    # DELIVERY
    # =========================================================

    is_default = models.BooleanField(
        default=False,
    )

    delivery_instructions = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = [
            "-is_default",
            "-created_at",
        ]

    def save(self, *args, **kwargs):

        if self.is_default:
            Address.objects.filter(
                user=self.user,
                is_default=True,
            ).exclude(
                pk=self.pk
            ).update(
                is_default=False
            )

        super().save(*args, **kwargs)

    def __str__(self):
        identifier = (
            self.user.phone_number
            or self.user.email
        )

        return f"{self.title} - {identifier}"