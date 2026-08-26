from django.contrib import admin

from .models import Notification, DeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "user",
        "notification_type",
        "target_type",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "target_type",
        "is_read",
        "created_at",
    )

    search_fields = (
        "title",
        "body",
        "target_id",
        "user__phone_number",
        "user__email",
    )

    readonly_fields = (
        "id",
        "created_at",
        "read_at",
    )

    ordering = (
        "-created_at",
    )

    list_select_related = (
        "user",
    )

    fieldsets = (
        (
            "Notification",
            {
                "fields": (
                    "id",
                    "user",
                    "notification_type",
                    "title",
                    "body",
                )
            },
        ),
        (
            "Navigation",
            {
                "fields": (
                    "target_type",
                    "target_id",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_read",
                    "read_at",
                    "created_at",
                )
            },
        ),
    )


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "device_type",
        "token_preview",
        "is_active",
        "last_used_at",
        "updated_at",
    )

    list_filter = (
        "device_type",
        "is_active",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "user__phone_number",
        "user__email",
        "token",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_used_at",
    )

    ordering = (
        "-updated_at",
    )

    list_select_related = (
        "user",
    )

    @admin.display(
        description="Device Token"
    )
    def token_preview(self, obj):
        """
        Don't display the entire FCM token in the admin list.
        """
        if not obj.token:
            return "-"

        if len(obj.token) <= 20:
            return obj.token

        return f"{obj.token[:10]}...{obj.token[-6:]}"
