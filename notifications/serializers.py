from rest_framework import serializers

from .models import Notification, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "body",
            "target_type",
            "target_id",
            "is_read",
            "read_at",
            "created_at",
        )

        read_only_fields = (
            "id",
            "notification_type",
            "title",
            "body",
            "target_type",
            "target_id",
            "is_read",
            "read_at",
            "created_at",
        )


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken

        fields = (
            "id",
            "token",
            "device_type",
            "is_active",
            "last_used_at",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "is_active",
            "last_used_at",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        token = validated_data["token"]

        device_token, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": user,
                "device_type": validated_data.get(
                    "device_type",
                    DeviceToken.DeviceType.ANDROID,
                ),
                "is_active": True,
            },
        )

        return device_token

    def update(self, instance, validated_data):
        """
        Re-activate an existing device token when the
        customer registers the device again.
        """

        instance.device_type = validated_data.get(
            "device_type",
            instance.device_type,
        )

        instance.is_active = True
        instance.save(
            update_fields=[
                "device_type",
                "is_active",
                "updated_at",
            ]
        )

        return instance