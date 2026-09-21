import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPVerification
from .serializers import (
    RegisterSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    CustomTokenObtainPairSerializer,
    RequestPasswordResetSerializer,
    ResetPasswordWithOTPSerializer,
)


from drf_spectacular.utils import extend_schema

User = get_user_model()


class AuthViewSet(viewsets.ViewSet):
    """
    Authentication API.

    Endpoints:

    POST /register/
    POST /login/
    POST /token/refresh/
    POST /otp/send/
    POST /otp/verify/
    POST /check-user/
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    # =========================================================
    # CHECK USER REGISTRATION STATUS
    # =========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="check-user",
    )
    def check_user(self, request):
        identity = request.data.get("identity") or request.data.get("phone_number") or request.data.get("email")
        if not identity:
            return Response({"error": "identity is required"}, status=status.HTTP_400_BAD_REQUEST)

        identity_str = str(identity).strip()
        user_exists = User.objects.filter(
            models.Q(phone_number__icontains=identity_str) | models.Q(email__iexact=identity_str)
        ).exists()

        return Response({
            "identity": identity_str,
            "is_registered": user_exists
        }, status=status.HTTP_200_OK)

    # =========================================================
    # REGISTER
    # =========================================================

    @extend_schema(request=RegisterSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path="register",
    )
    def register(self, request):
        serializer = RegisterSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Registration successful.",
                "user": {
                    "id": user.id,
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "is_phone_verified": (
                        user.is_phone_verified
                    ),
                    "is_email_verified": (
                        user.is_email_verified
                    ),
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )

    # =========================================================
    # LOGIN
    # =========================================================

    @extend_schema(request=CustomTokenObtainPairSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path="login",
    )
    def login(self, request):
        serializer = CustomTokenObtainPairSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "user": {
                    "id": user.id,
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "is_phone_verified": (
                        user.is_phone_verified
                    ),
                    "is_email_verified": (
                        user.is_email_verified
                    ),
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # REFRESH TOKEN
    # =========================================================

    @extend_schema(request=TokenRefreshSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path="token/refresh",
    )
    def token_refresh(self, request):
        serializer = TokenRefreshSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # SEND OTP
    # =========================================================

    @extend_schema(request=SendOTPSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path="otp/send",
    )
    def send_otp(self, request):
        serializer = SendOTPSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        recipient = serializer.validated_data[
            "recipient"
        ]

        # Determine channel
        if "@" in recipient:
            channel = OTPVerification.Channel.EMAIL
        else:
            channel = OTPVerification.Channel.SMS

        # -----------------------------------------------------
        # Invalidate previous OTPs
        # -----------------------------------------------------

        OTPVerification.objects.filter(
            recipient=recipient,
            channel=channel,
            is_verified=False,
        ).update(
            is_verified=True
        )

        # -----------------------------------------------------
        # Generate OTP
        # -----------------------------------------------------

        code = str(
            random.SystemRandom().randint(
                100000,
                999999,
            )
        )

        expires_at = (
            timezone.now()
            + timedelta(minutes=5)
        )

        OTPVerification.objects.create(
            recipient=recipient,
            channel=channel,
            otp_code=code,
            expires_at=expires_at,
        )

        # -----------------------------------------------------
        # TODO: Real OTP delivery
        # -----------------------------------------------------

        if channel == OTPVerification.Channel.EMAIL:
            # TODO:
            # Send email through email provider.
            pass

        else:
            # TODO:
            # Send SMS through SMS provider.
            pass

        response_data = {
            "message": (
                f"OTP sent via {channel}."
            ),
            "recipient": recipient,
            "expires_in": 300,
        }

        # Development only.
        # Remove this before production.
        if settings.DEBUG:
            response_data[
                "otp_code_dev_only"
            ] = code

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # VERIFY OTP
    # =========================================================

    @extend_schema(request=VerifyOTPSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path="otp/verify",
    )
    def verify_otp(self, request):
        serializer = VerifyOTPSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        recipient = serializer.validated_data[
            "recipient"
        ]

        otp_code = serializer.validated_data[
            "otp_code"
        ]

        # Determine channel
        if "@" in recipient:
            channel = OTPVerification.Channel.EMAIL
        else:
            channel = OTPVerification.Channel.SMS

        # -----------------------------------------------------
        # Find latest valid OTP
        # -----------------------------------------------------

        record = (
            OTPVerification.objects.filter(
                recipient=recipient,
                channel=channel,
                otp_code=otp_code,
                is_verified=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

        if not record:
            return Response(
                {
                    "detail": (
                        "Invalid or expired OTP code."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # Mark OTP verified
        # -----------------------------------------------------

        record.is_verified = True

        record.save(
            update_fields=["is_verified"]
        )

        # -----------------------------------------------------
        # Find or create user
        # -----------------------------------------------------

        if channel == OTPVerification.Channel.EMAIL:

            user = User.objects.filter(
                email__iexact=recipient
            ).first()

            if user:

                created = False

                user.is_email_verified = True

                user.save(
                    update_fields=[
                        "is_email_verified"
                    ]
                )

            else:

                user = User.objects.create_user(
                    email=recipient
                )

                user.is_email_verified = True

                user.save(
                    update_fields=[
                        "is_email_verified"
                    ]
                )
                created = True

        else:

            user = User.objects.filter(
                phone_number=recipient
            ).first()

            if user:

                created = False

                user.is_phone_verified = True

                user.save(
                    update_fields=[
                        "is_phone_verified"
                    ]
                )

            else:

                user = User.objects.create_user(
                    phone_number=recipient
                )

                user.is_phone_verified = True

                user.save(
                    update_fields=[
                        "is_phone_verified"
                    ]
                )

                created = True

        # -----------------------------------------------------
        # Generate JWT
        # -----------------------------------------------------

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": (
                    "OTP verification successful."
                ),
                "is_new_user": created,
                "user": {
                    "id": user.id,
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "is_phone_verified": (
                        user.is_phone_verified
                    ),
                    "is_email_verified": (
                        user.is_email_verified
                    ),
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # REQUEST PASSWORD RESET OTP
    # =========================================================

    @extend_schema(request=RequestPasswordResetSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path="password-reset/request",
    )
    def request_password_reset(self, request):
        """
        Step 1:
        Request a password-reset OTP for a registered
        phone number or email address.
        """

        serializer = RequestPasswordResetSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        recipient = serializer.validated_data[
            "recipient"
        ]

        # Determine OTP channel
        if "@" in recipient:
            channel = OTPVerification.Channel.EMAIL
        else:
            channel = OTPVerification.Channel.SMS

        # -----------------------------------------------------
        # Invalidate previous password-reset OTPs
        # -----------------------------------------------------

        OTPVerification.objects.filter(
            recipient=recipient,
            channel=channel,
            is_verified=False,
        ).update(
            is_verified=True
        )

        # -----------------------------------------------------
        # Generate secure 6-digit OTP
        # -----------------------------------------------------

        code = str(
            random.SystemRandom().randint(
                100000,
                999999,
            )
        )

        expires_at = (
            timezone.now()
            + timedelta(minutes=5)
        )

        OTPVerification.objects.create(
            recipient=recipient,
            channel=channel,
            otp_code=code,
            expires_at=expires_at,
        )

        # -----------------------------------------------------
        # Send OTP
        # -----------------------------------------------------

        if channel == OTPVerification.Channel.EMAIL:
            # TODO:
            # trigger_send_email_otp.delay(
            #     recipient,
            #     code,
            # )
            pass

        else:
            # TODO:
            # trigger_send_sms_otp.delay(
            #     recipient,
            #     code,
            # )
            pass

        response_data = {
            "message": (
                f"Password reset OTP sent via {channel}."
            ),
            "recipient": recipient,
            "expires_in": 300,
        }

        # Development only
        # Remove this before production.
        if settings.DEBUG:
            response_data[
                "otp_code_dev_only"
            ] = code

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # CONFIRM PASSWORD RESET
    # =========================================================

    @extend_schema(request=ResetPasswordWithOTPSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path="password-reset/confirm",
    )
    def confirm_password_reset(self, request):
        """
        Step 2:
        Verify the password-reset OTP and update
        the user's password.
        """

        serializer = ResetPasswordWithOTPSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        recipient = serializer.validated_data[
            "recipient"
        ]

        otp_code = serializer.validated_data[
            "otp_code"
        ]

        new_password = serializer.validated_data[
            "new_password"
        ]

        # Determine channel
        if "@" in recipient:
            channel = OTPVerification.Channel.EMAIL
        else:
            channel = OTPVerification.Channel.SMS

        # -----------------------------------------------------
        # Find valid OTP
        # -----------------------------------------------------

        record = (
            OTPVerification.objects.filter(
                recipient=recipient,
                channel=channel,
                otp_code=otp_code,
                is_verified=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

        if not record:
            return Response(
                {
                    "detail": (
                        "Invalid or expired OTP code."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # Find user
        # -----------------------------------------------------

        if channel == OTPVerification.Channel.EMAIL:

            user = User.objects.filter(
                email__iexact=recipient
            ).first()

        else:

            user = User.objects.filter(
                phone_number=recipient
            ).first()

        if not user:
            return Response(
                {
                    "detail": (
                        "User account no longer exists."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # -----------------------------------------------------
        # Update password
        # -----------------------------------------------------

        user.set_password(
            new_password
        )

        user.save(
            update_fields=["password"]
        )

        # -----------------------------------------------------
        # Consume OTP
        # -----------------------------------------------------

        record.is_verified = True

        record.save(
            update_fields=["is_verified"]
        )

        # -----------------------------------------------------
        # Invalidate any remaining OTPs
        # -----------------------------------------------------

        OTPVerification.objects.filter(
            recipient=recipient,
            channel=channel,
            is_verified=False,
        ).update(
            is_verified=True
        )

        return Response(
            {
                "message": (
                    "Password reset successful. "
                    "You can now log in with your "
                    "new password."
                )
            },
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # ME (GET & UPDATE CURRENT USER PROFILE)
    # =========================================================

    @action(
        detail=False,
        methods=["get", "patch", "put"],
        url_path="me",
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        user = request.user

        # Auto-promote superuser to ADMIN role if currently CUSTOMER
        if (user.is_superuser or user.is_staff) and user.role == User.Role.CUSTOMER:
            user.role = User.Role.ADMIN
            user.save(update_fields=["role"])

        if request.method == "GET":
            return Response(
                {
                    "id": user.id,
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "is_superuser": user.is_superuser,
                    "is_staff": user.is_staff,
                    "created_at": getattr(user, "created_at", None),
                },
                status=status.HTTP_200_OK,
            )

        data = request.data
        email = data.get("email")
        phone_number = data.get("phone_number")
        first_name = data.get("first_name")
        last_name = data.get("last_name")

        if email is not None:
            email_clean = email.strip().lower() if str(email).strip() else None
            if email_clean and User.objects.filter(email__iexact=email_clean).exclude(id=user.id).exists():
                return Response(
                    {"email": ["This email address is already in use by another account."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.email = email_clean

        if phone_number is not None:
            phone_clean = phone_number.strip() if str(phone_number).strip() else None
            if phone_clean and User.objects.filter(phone_number=phone_clean).exclude(id=user.id).exists():
                return Response(
                    {"phone_number": ["This phone number is already registered by another account."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.phone_number = phone_clean

        if first_name is not None:
            user.first_name = str(first_name).strip()

        if last_name is not None:
            user.last_name = str(last_name).strip()

        user.save()

        return Response(
            {
                "message": "Profile updated successfully.",
                "user": {
                    "id": user.id,
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "is_superuser": user.is_superuser,
                    "is_staff": user.is_staff,
                },
            },
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # CHANGE PASSWORD
    # =========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="change-password",
        permission_classes=[permissions.IsAuthenticated],
    )
    def change_password(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not old_password or not new_password:
            return Response(
                {"detail": "Both old password and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(old_password):
            return Response(
                {"old_password": ["Current password is incorrect."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {"confirm_password": ["New password and confirm password do not match."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 4:
            return Response(
                {"new_password": ["New password must be at least 4 characters long."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {"message": "Password updated successfully. Please use your new password next time you log in."},
            status=status.HTTP_200_OK,
        )


