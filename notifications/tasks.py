import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification, DeviceToken


logger = logging.getLogger(__name__)

User = get_user_model()


# ============================================================
# PUSH NOTIFICATION
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_push_notification(
    self,
    user_id,
    title,
    body,
    notification_type=Notification.NotificationType.SYSTEM,
    target_type=Notification.TargetType.NONE,
    target_id=None,
):
    """
    Create an in-app notification and send a push notification
    to all active devices belonging to the user.

    FCM integration can be added where indicated below.
    """

    # --------------------------------------------------------
    # Validate notification type
    # --------------------------------------------------------

    valid_notification_types = dict(
        Notification.NotificationType.choices
    )

    if notification_type not in valid_notification_types:
        notification_type = (
            Notification.NotificationType.SYSTEM
        )

    # --------------------------------------------------------
    # Validate target type
    # --------------------------------------------------------

    valid_target_types = dict(
        Notification.TargetType.choices
    )

    if target_type not in valid_target_types:
        target_type = Notification.TargetType.NONE

    # --------------------------------------------------------
    # Get user
    # --------------------------------------------------------

    try:
        user = User.objects.get(pk=user_id)

    except User.DoesNotExist:
        logger.error(
            "User %s not found for notification.",
            user_id,
        )

        return {
            "success": False,
            "message": "User not found.",
        }

    # --------------------------------------------------------
    # Create in-app notification
    # --------------------------------------------------------

    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
    )

    # --------------------------------------------------------
    # Get active device tokens
    # --------------------------------------------------------

    device_tokens = DeviceToken.objects.filter(
        user=user,
        is_active=True,
    )

    token_strings = list(
        device_tokens.values_list(
            "token",
            flat=True,
        )
    )

    # --------------------------------------------------------
    # No devices
    # --------------------------------------------------------

    if not token_strings:

        logger.info(
            "No active device tokens for user %s. "
            "Notification stored in database only.",
            user_id,
        )

        return {
            "success": True,
            "notification_id": str(notification.id),
            "tokens_sent": 0,
        }

    # --------------------------------------------------------
    # FCM PUSH NOTIFICATION
    # --------------------------------------------------------
    #
    # Install:
    #
    # pip install firebase-admin
    #
    # Then initialize Firebase in a separate service/module.
    #
    # Example:
    #
    # from firebase_admin import messaging
    #
    # message = messaging.MulticastMessage(
    #
    #     notification=messaging.Notification(
    #         title=title,
    #         body=body,
    #     ),
    #
    #     data={
    #         "notification_id": str(notification.id),
    #         "notification_type": notification_type,
    #         "target_type": target_type,
    #         "target_id": str(target_id or ""),
    #     },
    #
    #     tokens=token_strings,
    # )
    #
    # response = messaging.send_each_for_multicast(message)
    #
    # --------------------------------------------------------

    logger.info(
        "Prepared push notification for %d device(s) "
        "of user %s.",
        len(token_strings),
        user_id,
    )

    # --------------------------------------------------------
    # TEMPORARY DEVELOPMENT BEHAVIOR
    # --------------------------------------------------------
    #
    # Until FCM is implemented, don't pretend the push
    # was actually delivered.
    #

    return {
        "success": True,
        "notification_id": str(notification.id),
        "tokens_found": len(token_strings),
        "push_sent": False,
        "message": "Notification stored; FCM not configured yet.",
    }


# ============================================================
# MARK INVALID FCM TOKEN
# ============================================================

@shared_task
def deactivate_device_token(token):
    """
    Deactivate an invalid/expired FCM token.
    """

    updated = DeviceToken.objects.filter(
        token=token,
    ).update(
        is_active=False,
        updated_at=timezone.now(),
    )

    if updated:
        logger.info(
            "Device token deactivated."
        )

    return {
        "success": True,
        "deactivated": bool(updated),
    }


# ============================================================
# SMS NOTIFICATION
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_sms_notification(
    self,
    phone_number,
    message,
):
    """
    Send SMS notification through your Bangladesh SMS provider.

    Provider integration should be added here later.
    """

    if not phone_number:
        return {
            "success": False,
            "message": "Phone number is empty.",
        }

    if not message:
        return {
            "success": False,
            "message": "SMS message is empty.",
        }

    logger.info(
        "SMS notification requested."
    )

    # --------------------------------------------------------
    # REAL SMS PROVIDER
    # --------------------------------------------------------
    #
    # Example:
    #
    # import requests
    #
    # response = requests.post(
    #     settings.SMS_API_URL,
    #     data={
    #         "api_token": settings.SMS_API_TOKEN,
    #         "sender_id": settings.SMS_SENDER_ID,
    #         "phone": phone_number,
    #         "message": message,
    #     },
    #     timeout=10,
    # )
    #
    # response.raise_for_status()
    #
    # --------------------------------------------------------

    return {
        "success": True,
        "recipient": phone_number,
        "sent": False,
        "message": "SMS provider not configured yet.",
    }


# ============================================================
# EMAIL NOTIFICATION
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_email_notification(
    self,
    recipient_email,
    subject,
    message_body,
):
    """
    Send an email notification using Django's email backend.
    """

    if not recipient_email:
        return {
            "success": False,
            "message": "Recipient email is empty.",
        }

    if not subject:
        return {
            "success": False,
            "message": "Email subject is empty.",
        }

    if not message_body:
        return {
            "success": False,
            "message": "Email body is empty.",
        }

    try:

        send_mail(
            subject=subject,
            message=message_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[
                recipient_email
            ],
            fail_silently=False,
        )

        logger.info(
            "Email notification sent successfully."
        )

        return {
            "success": True,
            "recipient": recipient_email,
        }

    except Exception:
        logger.exception(
            "Failed to send email notification."
        )
        raise


# ============================================================
# MARK SINGLE NOTIFICATION AS READ
# ============================================================

@shared_task
def mark_notification_as_read(notification_id):
    """
    Mark one notification as read.

    Useful when notification processing happens asynchronously.
    """

    try:

        notification = Notification.objects.get(
            pk=notification_id
        )

    except Notification.DoesNotExist:

        return {
            "success": False,
            "message": "Notification not found.",
        }

    if not notification.is_read:

        notification.is_read = True
        notification.read_at = timezone.now()

        notification.save(
            update_fields=[
                "is_read",
                "read_at",
            ]
        )

    return {
        "success": True,
        "notification_id": str(notification.id),
    }


# ============================================================
# CLEAN OLD NOTIFICATIONS
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def cleanup_old_notifications(
    self,
    days_to_keep=30,
):
    """
    Delete old notifications that have already been read.
    """

    try:
        days_to_keep = int(days_to_keep)

    except (TypeError, ValueError):

        return {
            "success": False,
            "message": "days_to_keep must be an integer.",
        }

    if days_to_keep < 1:

        return {
            "success": False,
            "message": "days_to_keep must be greater than 0.",
        }

    threshold = (
        timezone.now()
        - timedelta(days=days_to_keep)
    )

    deleted_count, _ = (
        Notification.objects
        .filter(
            is_read=True,
            read_at__lte=threshold,
        )
        .delete()
    )

    logger.info(
        "Deleted %d old read notifications.",
        deleted_count,
    )

    return {
        "success": True,
        "deleted_count": deleted_count,
    }