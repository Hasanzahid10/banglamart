from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

from rest_framework import serializers


User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "email",
            "first_name",
            "last_name",
            "password",
            "confirm_password",
            "role",
        )

        read_only_fields = (
            "id",
            "role",
        )

    def validate_phone_number(self, value):
        if not value:
            return None

        value = value.strip()

        clean_phone = value.lstrip("+")

        if not clean_phone.isdigit():
            raise serializers.ValidationError(
                "Enter a valid phone number."
            )

        if len(clean_phone) < 8 or len(clean_phone) > 15:
            raise serializers.ValidationError(
                "Enter a valid phone number."
            )

        if User.objects.filter(
            phone_number=value
        ).exists():
            raise serializers.ValidationError(
                "This phone number is already registered."
            )

        return value

    def validate_email(self, value):
        if not value:
            return None

        value = value.strip().lower()

        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError(
                "Enter a valid email address."
            )

        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "This email address is already registered."
            )

        return value

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")
        email = attrs.get("email")
        password = attrs.get("password")
        confirm_password = attrs.get(
            "confirm_password"
        )

        # ---------------------------------------------
        # Phone OR email is required
        # ---------------------------------------------

        if not phone_number and not email:
            raise serializers.ValidationError(
                {
                    "identifier": (
                        "Either phone number or email "
                        "address must be provided."
                    )
                }
            )

        # ---------------------------------------------
        # Password confirmation
        # ---------------------------------------------

        if password != confirm_password:
            raise serializers.ValidationError(
                {
                    "confirm_password": (
                        "Password fields didn't match."
                    )
                }
            )

        # ---------------------------------------------
        # Password validation (at least 4 chars)
        # ---------------------------------------------
        if len(password) < 4:
            raise serializers.ValidationError(
                {
                    "password": ["Password must be at least 4 characters long."]
                }
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop(
            "confirm_password",
            None,
        )

        # Never allow public registration to choose
        # RIDER / WAREHOUSE_STAFF / ADMIN.
        validated_data["role"] = User.Role.CUSTOMER

        return User.objects.create_user(
            **validated_data
        )


class SendOTPSerializer(serializers.Serializer):

    recipient = serializers.CharField(
        max_length=255,
        help_text=(
            "Provide a valid phone number "
            "or email address."
        ),
    )

    def validate_recipient(self, value):
        value = value.strip()

        # ---------------------------------------------
        # Email
        # ---------------------------------------------

        if "@" in value:
            value = value.lower()

            try:
                validate_email(value)
            except DjangoValidationError:
                raise serializers.ValidationError(
                    "Enter a valid email address."
                )

            return value

        # ---------------------------------------------
        # Phone
        # ---------------------------------------------

        clean_phone = value.lstrip("+")

        if not clean_phone.isdigit():
            raise serializers.ValidationError(
                "Enter a valid phone number or email address."
            )

        if len(clean_phone) < 8 or len(clean_phone) > 15:
            raise serializers.ValidationError(
                "Enter a valid phone number or email address."
            )

        return value


class VerifyOTPSerializer(serializers.Serializer):

    recipient = serializers.CharField(
        max_length=255,
    )

    otp_code = serializers.CharField(
        min_length=6,
        max_length=6,
    )

    def validate_recipient(self, value):
        value = value.strip()

        if "@" in value:
            value = value.lower()

            try:
                validate_email(value)
            except DjangoValidationError:
                raise serializers.ValidationError(
                    "Enter a valid email address."
                )

            return value

        clean_phone = value.lstrip("+")

        if (
            not clean_phone.isdigit()
            or len(clean_phone) < 8
            or len(clean_phone) > 15
        ):
            raise serializers.ValidationError(
                "Enter a valid phone number."
            )

        return value

    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                "OTP must contain only numbers."
            )

        return value


class CustomTokenObtainPairSerializer(
    serializers.Serializer
):
    """
    Password login using either:

    - Phone number
    - Email address
    """

    identifier = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=(
            "Enter your registered phone number "
            "or email address."
        )
    )

    identity = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        raw_id = attrs.get("identifier") or attrs.get("identity") or attrs.get("email") or attrs.get("phone_number") or ""
        identifier = str(raw_id).strip()

        password = attrs.get("password")

        if not identifier or not password:
            raise serializers.ValidationError(
                {
                    "detail": "Both phone/email and password are required."
                }
            )

        # ---------------------------------------------
        # Find by phone or email
        # ---------------------------------------------

        user = User.objects.filter(
            phone_number=identifier
        ).first()

        if not user:
            user = User.objects.filter(
                email__iexact=identifier
            ).first()

        # ---------------------------------------------
        # Credentials
        # ---------------------------------------------

        if not user or not user.check_password(
            password
        ):
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Invalid credentials. Please check your phone/email and password."
                    )
                }
            )

        attrs["user"] = user
        return attrs

        # ---------------------------------------------
        # Account status
        # ---------------------------------------------

        if not user.is_active:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "User account is disabled."
                    )
                }
            )

        attrs["user"] = user

        return attrs

class RequestPasswordResetSerializer(serializers.Serializer):
    """
    Request a password-reset OTP using either:
    - Phone number
    - Email address
    """

    recipient = serializers.CharField(
        max_length=255,
        help_text=(
            "Enter your registered phone number "
            "or email address."
        ),
    )

    def validate_recipient(self, value):
        value = value.strip()

        # -------------------------------------------------
        # Email
        # -------------------------------------------------

        if "@" in value:
            value = value.lower()

            try:
                validate_email(value)
            except DjangoValidationError:
                raise serializers.ValidationError(
                    "Enter a valid email address."
                )

            user_exists = User.objects.filter(
                email__iexact=value
            ).exists()

            if not user_exists:
                raise serializers.ValidationError(
                    "No account found with this email address."
                )

            return value

        # -------------------------------------------------
        # Phone
        # -------------------------------------------------

        clean_phone = value.lstrip("+")

        if (
            not clean_phone.isdigit()
            or len(clean_phone) < 8
            or len(clean_phone) > 15
        ):
            raise serializers.ValidationError(
                "Enter a valid phone number."
            )

        user_exists = User.objects.filter(
            phone_number=value
        ).exists()

        if not user_exists:
            raise serializers.ValidationError(
                "No account found with this phone number."
            )

        return value


class ResetPasswordWithOTPSerializer(serializers.Serializer):
    """
    Reset password using an OTP sent to:
    - Phone number
    - Email address
    """

    recipient = serializers.CharField(
        max_length=255,
    )

    otp_code = serializers.CharField(
        min_length=6,
        max_length=6,
    )

    new_password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={"input_type": "password"},
    )

    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    def validate_recipient(self, value):
        value = value.strip()

        # -------------------------------------------------
        # Email
        # -------------------------------------------------

        if "@" in value:
            value = value.lower()

            try:
                validate_email(value)
            except DjangoValidationError:
                raise serializers.ValidationError(
                    "Enter a valid email address."
                )

            return value

        # -------------------------------------------------
        # Phone
        # -------------------------------------------------

        clean_phone = value.lstrip("+")

        if (
            not clean_phone.isdigit()
            or len(clean_phone) < 8
            or len(clean_phone) > 15
        ):
            raise serializers.ValidationError(
                "Enter a valid phone number."
            )

        return value

    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                "OTP must contain only numbers."
            )

        return value

    def validate(self, attrs):
        new_password = attrs.get(
            "new_password"
        )

        confirm_password = attrs.get(
            "confirm_password"
        )

        # -------------------------------------------------
        # Password confirmation
        # -------------------------------------------------

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {
                    "confirm_password": (
                        "Passwords do not match."
                    )
                }
            )

        # -------------------------------------------------
        # Django password validation
        # -------------------------------------------------

        try:
            validate_password(
                new_password,
                user=None,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {
                    "new_password": list(
                        error.messages
                    )
                }
            )

        return attrs
#=======================================
##Your password-reset flow will then be:
#=======================================

"""
POST /api/auth/password-reset/request/
        ↓
Phone OR Email
        ↓
OTP generated
        ↓
SMS / Email
        ↓
POST /api/auth/password-reset/confirm/
        ↓
Recipient + OTP + New Password
        ↓
Password changed
"""