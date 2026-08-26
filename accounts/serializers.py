from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

from rest_framework import serializers

from .models import UserProfile, Address


User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):

    phone_number = serializers.CharField(
        source="user.phone_number",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    email = serializers.EmailField(
        source="user.email",
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    first_name = serializers.CharField(
        source="user.first_name",
        required=False,
        allow_blank=True,
    )

    last_name = serializers.CharField(
        source="user.last_name",
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = UserProfile

        fields = (
            "id",
            "phone_number",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "date_of_birth",
            "alternate_phone",
            "total_orders",
            "loyalty_points",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "total_orders",
            "loyalty_points",
            "created_at",
            "updated_at",
        )

    def validate_phone_number(self, value):

        if not value:
            return value

        value = value.strip()

        clean_phone = value.lstrip("+")

        if (
            not clean_phone.isdigit()
            or len(clean_phone) < 8
            or len(clean_phone) > 15
        ):
            raise serializers.ValidationError(
                "Enter a valid phone number."
            )

        user = self.context["request"].user

        if User.objects.filter(
            phone_number=value
        ).exclude(
            pk=user.pk
        ).exists():

            raise serializers.ValidationError(
                "This phone number is already registered "
                "to another account."
            )

        return value

    def validate_email(self, value):

        if not value:
            return value

        value = value.strip().lower()

        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError(
                "Enter a valid email address."
            )

        user = self.context["request"].user

        if User.objects.filter(
            email__iexact=value
        ).exclude(
            pk=user.pk
        ).exists():

            raise serializers.ValidationError(
                "This email address is already registered "
                "to another account."
            )

        return value

    def validate_alternate_phone(self, value):

        if not value:
            return value

        value = value.strip()

        clean_phone = value.lstrip("+")

        if (
            not clean_phone.isdigit()
            or len(clean_phone) < 8
            or len(clean_phone) > 15
        ):
            raise serializers.ValidationError(
                "Enter a valid alternate phone number."
            )

        return value

    def update(self, instance, validated_data):

        user_data = validated_data.pop(
            "user",
            {}
        )

        user = instance.user

        if "phone_number" in user_data:

            new_phone = user_data["phone_number"]

            if new_phone != user.phone_number:
                user.phone_number = new_phone
                user.is_phone_verified = False

        if "email" in user_data:

            new_email = user_data["email"]

            if new_email != user.email:
                user.email = new_email
                user.is_email_verified = False

        if "first_name" in user_data:
            user.first_name = user_data["first_name"]

        if "last_name" in user_data:
            user.last_name = user_data["last_name"]

        user.save()

        return super().update(
            instance,
            validated_data
        )


class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address

        fields = (
            "id",
            "title",
            "address_type",
            "street_address",
            "flat_no",
            "floor",
            "area",
            "city",
            "latitude",
            "longitude",
            "is_default",
            "delivery_instructions",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):

        validated_data["user"] = (
            self.context["request"].user
        )

        return super().create(
            validated_data
        )

    def update(self, instance, validated_data):

        # Never allow client to change ownership.
        validated_data.pop("user", None)

        return super().update(
            instance,
            validated_data
        )