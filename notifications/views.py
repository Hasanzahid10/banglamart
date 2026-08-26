from django.db.models import Q
from django.utils import timezone

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification, DeviceToken
from .serializers import (
    NotificationSerializer,
    DeviceTokenSerializer,
)


class NotificationViewSet(viewsets.GenericViewSet):
    """
    Customer notification API.

    Customers can:
        - View their notifications
        - View unread count
        - Mark a notification as read
        - Mark all their notifications as read

    Customers cannot:
        - Create notifications
        - Delete notifications
        - Change notification content
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(
            Q(user=self.request.user) |
            Q(user__isnull=True)
        ).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        notification = self.get_object()

        serializer = self.get_serializer(notification)

        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="unread-count",
    )
    def unread_count(self, request):
        """
        GET /api/notifications/unread-count/
        """

        count = self.get_queryset().filter(
            is_read=False
        ).count()

        return Response(
            {
                "unread_count": count
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="mark-all-read",
    )
    def mark_all_as_read(self, request):
        """
        POST /api/notifications/mark-all-read/
        """

        now = timezone.now()

        updated = self.get_queryset().filter(
            user=request.user,
            is_read=False,
        ).update(
            is_read=True,
            read_at=now,
        )

        return Response(
            {
                "message": "All notifications marked as read.",
                "updated_count": updated,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="mark-read",
    )
    def mark_as_read(self, request, pk=None):
        """
        POST /api/notifications/{id}/mark-read/
        """

        notification = self.get_object()

        # Only update the user's own notification.
        if notification.user_id != request.user.id:
            return Response(
                {
                    "detail": "This notification cannot be modified."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()

            notification.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )

        return Response(
            {
                "message": "Notification marked as read."
            },
            status=status.HTTP_200_OK,
        )


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    Register and manage FCM device tokens.

    A customer can have multiple devices:
        Android
        iOS
        Web
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeviceTokenSerializer

    def get_queryset(self):
        return DeviceToken.objects.filter(
            user=self.request.user
        ).order_by("-updated_at")

    def create(self, request, *args, **kwargs):
        """
        Register or refresh a device token.
        """

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        device_token = serializer.save()

        return Response(
            self.get_serializer(device_token).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
    )
    def deactivate(self, request, pk=None):
        """
        POST /api/notifications/device-tokens/{id}/deactivate/
        """

        device_token = self.get_object()

        device_token.is_active = False

        device_token.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": "Device token deactivated."
            },
            status=status.HTTP_200_OK,
        )