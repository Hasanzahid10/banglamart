from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from logistics.serializers import DeliveryOrderSerializer

from .models import RiderProfile, DeliveryTask


User = get_user_model()


# =========================================================
# RIDER USER
# =========================================================

class RiderUserSerializer(serializers.ModelSerializer):
    """
    Basic user information exposed for rider APIs.
    """

    class Meta:
        model = User

        fields = (
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
        )

        read_only_fields = fields


# =========================================================
# RIDER PROFILE
# =========================================================

class RiderProfileSerializer(serializers.ModelSerializer):
    """
    Rider profile information.

    Authentication fields remain inside User.
    Operational rider information remains here.
    """

    user = RiderUserSerializer(
        read_only=True
    )

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    has_location = serializers.BooleanField(
        read_only=True
    )

    class Meta:
        model = RiderProfile

        fields = (
            "id",
            "user",

            # Dark store
            "dark_store",
            "dark_store_name",

            # Rider information
            "vehicle_type",
            "license_number",

            # Availability
            "is_available",
            "is_on_duty",

            # Location
            "latitude",
            "longitude",
            "has_location",
            "last_location_update",

            # Timestamps
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "user",
            "is_available",
            "is_on_duty",
            "has_location",
            "last_location_update",
            "created_at",
            "updated_at",
        )


# =========================================================
# UPDATE RIDER LOCATION
# =========================================================

class UpdateRiderLocationSerializer(serializers.Serializer):
    """
    Rider sends current GPS coordinates.

    Example:

    {
        "latitude": 25.7439,
        "longitude": 89.2752
    }
    """

    latitude = serializers.FloatField(
        required=True,
        min_value=-90,
        max_value=90,
    )

    longitude = serializers.FloatField(
        required=True,
        min_value=-180,
        max_value=180,
    )

    def update_location(self, profile):
        """
        Update rider's current location.
        """

        profile.latitude = self.validated_data[
            "latitude"
        ]

        profile.longitude = self.validated_data[
            "longitude"
        ]

        profile.last_location_update = (
            timezone.now()
        )

        profile.save(
            update_fields=[
                "latitude",
                "longitude",
                "last_location_update",
                "updated_at",
            ]
        )

        return profile


# =========================================================
# DELIVERY TASK
# =========================================================

class DeliveryTaskSerializer(
    serializers.ModelSerializer
):
    """
    Delivery task representation.

    Used by:
        - Rider
        - Warehouse staff
        - Admin
    """

    delivery_order = DeliveryOrderSerializer(
        read_only=True
    )

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    rider_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryTask

        fields = (
            "id",

            # Dark store
            "dark_store",
            "dark_store_name",

            # Delivery
            "delivery_order",

            # Rider
            "rider",
            "rider_name",

            # Status
            "status",
            "failure_reason",

            # Time tracking
            "assigned_at",
            "accepted_at",
            "picked_up_at",
            "arrived_at",
            "delivered_at",
            "failed_at",
            "cancelled_at",

            # Timestamps
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",

            "dark_store",
            "dark_store_name",

            "delivery_order",

            "rider",
            "rider_name",

            "assigned_at",
            "accepted_at",
            "picked_up_at",
            "arrived_at",
            "delivered_at",
            "failed_at",
            "cancelled_at",

            "created_at",
            "updated_at",
        )

    def get_rider_name(self, obj) -> str | None:
        """
        Safely return rider's display name.
        """

        if not obj.rider:
            return None

        full_name = obj.rider.get_full_name()

        if full_name:
            return full_name

        return (
            getattr(
                obj.rider,
                "phone_number",
                None,
            )
            or getattr(
                obj.rider,
                "email",
                None,
            )
            or str(obj.rider.id)
        )


# =========================================================
# UPDATE DELIVERY TASK STATUS
# =========================================================

class UpdateTaskStatusSerializer(
    serializers.Serializer
):
    """
    Rider updates the status of a delivery task.

    Example:

    {
        "status": "accepted"
    }

    Failed:

    {
        "status": "failed",
        "failure_reason": "Customer did not answer phone."
    }
    """

    status = serializers.ChoiceField(
        choices=DeliveryTask.TaskStatus.choices
    )

    failure_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, attrs):

        new_status = attrs["status"]

        failure_reason = (
            attrs.get("failure_reason")
            or ""
        ).strip()

        # -------------------------------------------------
        # FAILED requires a reason
        # -------------------------------------------------

        if (
            new_status
            == DeliveryTask.TaskStatus.FAILED
            and not failure_reason
        ):
            raise serializers.ValidationError({
                "failure_reason":
                    "A failure reason is required "
                    "when marking a delivery as failed."
            })

        # -------------------------------------------------
        # Non-failed status should not have failure reason
        # -------------------------------------------------

        if (
            new_status
            != DeliveryTask.TaskStatus.FAILED
            and failure_reason
        ):
            raise serializers.ValidationError({
                "failure_reason":
                    "Failure reason is only allowed "
                    "when status is failed."
            })

        return attrs