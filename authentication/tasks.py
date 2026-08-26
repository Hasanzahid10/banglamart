import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import OTPVerification


logger = logging.getLogger(__name__)


# ============================================================
# SEND OTP
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_otp(
    self,
    otp_id,
):
    """
    Send an existing OTP through SMS or Email.

    OTP must already exist in the database before
    this task is called.
    """

    try:
        otp = OTPVerification.objects.get(
            pk=otp_id
        )

    except OTPVerification.DoesNotExist:

        logger.error(
            "OTP %s does not exist.",
            otp_id,
        )

        return {
            "success": False,
            "message": "OTP not found.",
        }

    # --------------------------------------------------------
    # Don't send already verified OTP
    # --------------------------------------------------------

    if otp.is_verified:

        return {
            "success": False,
            "message": "OTP has already been verified.",
        }

    # --------------------------------------------------------
    # Don't send expired OTP
    # --------------------------------------------------------

    if timezone.now() >= otp.expires_at:

        return {
            "success": False,
            "message": "OTP has expired.",
        }

    # --------------------------------------------------------
    # SMS
    # --------------------------------------------------------

    if otp.channel == OTPVerification.Channel.SMS:

        return send_otp_sms(
            otp.recipient,
            otp.otp_code,
        )

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    if otp.channel == OTPVerification.Channel.EMAIL:

        return send_otp_email(
            otp.recipient,
            otp.otp_code,
        )

    logger.error(
        "Unsupported OTP channel: %s",
        otp.channel,
    )

    return {
        "success": False,
        "message": "Unsupported OTP channel.",
    }


# ============================================================
# SEND OTP SMS
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_otp_sms(
    self,
    phone_number,
    otp_code,
):
    """
    Send OTP through Bangladesh SMS provider.

    Replace the placeholder with your actual SMS gateway.
    """

    if not phone_number:
        return {
            "success": False,
            "message": "Phone number is empty.",
        }

    if not otp_code:
        return {
            "success": False,
            "message": "OTP code is empty.",
        }

    logger.info(
        "Sending OTP SMS."
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
    #         "message": (
    #             f"Your BanglaMart verification code "
    #             f"is {otp_code}."
    #         ),
    #     },
    #     timeout=10,
    # )
    #
    # response.raise_for_status()
    #
    # --------------------------------------------------------

    return {
        "success": True,
        "channel": "SMS",
        "recipient": phone_number,
        "sent": False,
        "message": "SMS provider not configured yet.",
    }


# ============================================================
# SEND OTP EMAIL
# ============================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_otp_email(
    self,
    email,
    otp_code,
):
    """
    Send OTP through Django email backend.
    """

    if not email:
        return {
            "success": False,
            "message": "Email address is empty.",
        }

    if not otp_code:
        return {
            "success": False,
            "message": "OTP code is empty.",
        }

    try:

        send_mail(
            subject="BanglaMart Verification Code",
            message=(
                "Your BanglaMart verification code is: "
                f"{otp_code}\n\n"
                "This code will expire soon. "
                "Do not share this code with anyone."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(
            "OTP email sent successfully."
        )

        return {
            "success": True,
            "channel": "EMAIL",
            "recipient": email,
        }

    except Exception:

        logger.exception(
            "Failed to send OTP email."
        )

        raise


# ============================================================
# DELETE EXPIRED OTPs
# ============================================================

@shared_task
def cleanup_expired_otps():
    """
    Delete expired OTP records.

    Run this task periodically using Celery Beat.
    """

    deleted_count, _ = (
        OTPVerification.objects
        .filter(
            expires_at__lt=timezone.now(),
            is_verified=False,
        )
        .delete()
    )

    logger.info(
        "Deleted %d expired OTP records.",
        deleted_count,
    )

    return {
        "success": True,
        "deleted_count": deleted_count,
    }


# ============================================================
# DELETE OLD VERIFIED OTPs
# ============================================================

@shared_task
def cleanup_old_verified_otps(
    days_to_keep=1,
):
    """
    Delete old OTP records that have already been verified.
    """

    threshold = (
        timezone.now()
        - timezone.timedelta(days=days_to_keep)
    )

    deleted_count, _ = (
        OTPVerification.objects
        .filter(
            is_verified=True,
            created_at__lt=threshold,
        )
        .delete()
    )

    logger.info(
        "Deleted %d old verified OTP records.",
        deleted_count,
    )

    return {
        "success": True,
        "deleted_count": deleted_count,
    }