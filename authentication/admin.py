from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, OTPVerification


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_display = (
        "id",
        "phone_number",
        "email",
        "role",
        "is_phone_verified",
        "is_email_verified",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "is_phone_verified",
        "is_email_verified",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "phone_number",
        "email",
    )

    ordering = ("-id",)

    readonly_fields = (
        "last_login",
        "date_joined",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "phone_number",
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Verification",
            {
                "fields": (
                    "is_phone_verified",
                    "is_email_verified",
                )
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "recipient",
        "channel",
        "otp_code",
        "is_verified",
        "created_at",
        "expires_at",
    )

    list_filter = (
        "channel",
        "is_verified",
    )

    search_fields = (
        "recipient",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("-created_at",)