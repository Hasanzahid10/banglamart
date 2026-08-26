from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):

    def create_user(
        self,
        phone_number=None,
        email=None,
        password=None,
        **extra_fields,
    ):
        if not phone_number and not email:
            raise ValueError(
                _("Either a phone number or an email address is required.")
            )

        if email:
            email = self.normalize_email(email)

        extra_fields.setdefault("is_active", True)

        user = self.model(
            phone_number=phone_number,
            email=email,
            **extra_fields,
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        phone_number=None,
        email=None,
        password=None,
        **extra_fields,
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        if not phone_number and not email:
            raise ValueError(
                _("Superuser must have a phone number or email address.")
            )

        return self.create_user(
            phone_number=phone_number,
            email=email,
            password=password,
            **extra_fields,
        )


class User(AbstractUser):

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", _("Customer")
        RIDER = "RIDER", _("Delivery Rider")
        WAREHOUSE_STAFF = "WAREHOUSE_STAFF", _("Warehouse Staff")
        ADMIN = "ADMIN", _("Admin")

    # Remove Django's username authentication
    username = None

    phone_number = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    is_phone_verified = models.BooleanField(
        default=False,
    )

    is_email_verified = models.BooleanField(
        default=False,
    )

    # Django admin / authentication configuration
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def clean(self):
        super().clean()

        if self.role:
            self.role = self.role.upper().strip()

        if not self.phone_number and not self.email:
            raise ValidationError(
                _("User must have at least a phone number or an email address.")
            )

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()

        if self.phone_number:
            self.phone_number = self.phone_number.strip()

        if self.role:
            self.role = self.role.upper().strip()

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):
        identifier = self.phone_number or self.email
        return f"{identifier} ({self.role})"


class OTPVerification(models.Model):

    class Channel(models.TextChoices):
        SMS = "SMS", _("SMS")
        EMAIL = "EMAIL", _("Email")

    recipient = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Phone number or email address receiving the OTP.",
    )

    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
    )

    otp_code = models.CharField(
        max_length=6,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "channel"],
            ),
            models.Index(
                fields=["recipient", "is_verified"],
            ),
        ]

    def __str__(self):
        status = "Verified" if self.is_verified else "Pending"
        return f"OTP for {self.recipient} via {self.channel} ({status})"
