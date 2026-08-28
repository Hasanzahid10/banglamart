from decimal import Decimal, ROUND_HALF_UP
import uuid

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from rest_framework import serializers

from accounts.models import Address

from .models import (
    DarkStore,
    DeliveryOrder,
    DeliverySlot,
    DeliveryZone,
)


class CreateDeliveryOrderSerializer(serializers.Serializer):
    """
    Create a DeliveryOrder using either:

    1. A saved account address
    2. A custom delivery address

    Routing flow:

        Customer GPS
             ↓
        DeliveryZone Polygon
             ↓
        DarkStore
             ↓
        Distance
             ↓
        Delivery Fee
             ↓
        Delivery Slot
             ↓
        DeliveryOrder
    """

    # =========================================================
    # SAVED ADDRESS
    # =========================================================

    address_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    # =========================================================
    # CUSTOM ADDRESS
    # =========================================================

    recipient_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )

    recipient_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    street_address = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    area = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    latitude = serializers.FloatField(
        required=False,
        min_value=-90.0,
        max_value=90.0,
    )

    longitude = serializers.FloatField(
        required=False,
        min_value=-180.0,
        max_value=180.0,
    )

    # =========================================================
    # DELIVERY SLOT
    # =========================================================

    delivery_slot_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    # =========================================================
    # VALIDATION
    # =========================================================

    def validate(self, attrs):

        user = self.context["request"].user

        address_id = attrs.get("address_id")

        # =====================================================
        # OPTION A: SAVED ADDRESS
        # =====================================================

        if address_id:

            try:
                saved_address = Address.objects.get(
                    id=address_id,
                    user=user,
                )
            except Address.DoesNotExist:

                raise serializers.ValidationError({
                    "address_id": (
                        "Invalid address ID or this address "
                        "does not belong to you."
                    )
                })

            # -------------------------------------------------
            # Make sure saved address has coordinates
            # -------------------------------------------------

            if (
                saved_address.latitude is None
                or saved_address.longitude is None
            ):
                raise serializers.ValidationError({
                    "address_id": (
                        "This saved address does not have "
                        "valid GPS coordinates."
                    )
                })

            # -------------------------------------------------
            # Address -> GIS Point
            # -------------------------------------------------

            location_point = Point(
                float(saved_address.longitude),
                float(saved_address.latitude),
                srid=4326,
            )

            attrs["resolved_address_obj"] = saved_address

            attrs["location_point"] = location_point

            # -------------------------------------------------
            # Customer information
            # -------------------------------------------------

            full_name = (
                f"{user.first_name} {user.last_name}"
            ).strip()

            attrs["recipient_name"] = (
                full_name or "Customer"
            )

            attrs["recipient_phone"] = (
                getattr(user, "phone_number", "") or ""
            )

            attrs["street_address"] = (
                saved_address.street_address
            )

            attrs["area"] = (
                saved_address.area
            )

            attrs["city"] = (
                saved_address.city
                or "Dhaka"
            )

        # =====================================================
        # OPTION B: CUSTOM ADDRESS
        # =====================================================

        else:

            required_fields = [
                "street_address",
                "area",
                "latitude",
                "longitude",
            ]

            missing_fields = []

            for field in required_fields:

                if field not in attrs:
                    missing_fields.append(field)
                    continue

                value = attrs.get(field)

                if value is None:
                    missing_fields.append(field)

                elif isinstance(value, str) and not value.strip():
                    missing_fields.append(field)

            if missing_fields:

                raise serializers.ValidationError({
                    "address": (
                        "Please provide either address_id "
                        "or all required custom address fields."
                    ),
                    "missing_fields": missing_fields,
                })

            # -------------------------------------------------
            # GIS Point
            # -------------------------------------------------

            location_point = Point(
                attrs["longitude"],
                attrs["latitude"],
                srid=4326,
            )

            attrs["location_point"] = location_point

            # -------------------------------------------------
            # Customer information
            # -------------------------------------------------

            full_name = (
                f"{user.first_name} {user.last_name}"
            ).strip()

            if not attrs.get("recipient_name"):
                attrs["recipient_name"] = (
                    full_name or "Customer"
                )

            if not attrs.get("recipient_phone"):
                attrs["recipient_phone"] = (
                    getattr(user, "phone_number", "") or ""
                )

            if not attrs.get("city"):
                attrs["city"] = "Dhaka"

        # =====================================================
        # CUSTOMER LOCATION
        # =====================================================

        user_point = attrs["location_point"]

        # =====================================================
        # FIND DELIVERY ZONE
        # =====================================================

        matching_zone = (
            DeliveryZone.objects
            .filter(
                boundary__contains=user_point,
                is_active=True,
                dark_store__is_active=True,
                dark_store__service_area__is_active=True,
            )
            .select_related(
                "dark_store",
                "dark_store__service_area",
            )
            .first()
        )

        # =====================================================
        # NO DELIVERY ZONE
        # =====================================================

        if not matching_zone:

            raise serializers.ValidationError({
                "location": (
                    "Sorry, this address is currently "
                    "outside our delivery coverage area."
                )
            })

        dark_store = matching_zone.dark_store

        # =====================================================
        # CHECK DARK STORE LOCATION
        # =====================================================

        if not dark_store.location:

            raise serializers.ValidationError({
                "dark_store": (
                    "The selected dark store does not have "
                    "a valid GPS location."
                )
            })

        # =====================================================
        # CALCULATE DISTANCE
        # =====================================================

        store_obj = (
            DarkStore.objects
            .filter(
                id=dark_store.id,
                is_active=True,
                service_area__is_active=True,
                location__isnull=False,
            )
            .annotate(
                distance=Distance(
                    "location",
                    user_point,
                )
            )
            .first()
        )

        if not store_obj:

            raise serializers.ValidationError({
                "location": (
                    "Unable to determine the serving "
                    "dark store."
                )
            })

        # -----------------------------------------------------
        # Distance in KM
        # -----------------------------------------------------

        distance_km = Decimal(
            str(store_obj.distance.km)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # =====================================================
        # DELIVERY FEE
        # =====================================================

        base_fee = Decimal("20.00")

        per_km_fee = Decimal("5.00")

        delivery_fee = (
            base_fee
            + (distance_km * per_km_fee)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # =====================================================
        # DELIVERY SLOT
        # =====================================================

        delivery_slot = None

        delivery_slot_id = attrs.get(
            "delivery_slot_id"
        )

        if delivery_slot_id:

            try:

                delivery_slot = (
                    DeliverySlot.objects.get(
                        id=delivery_slot_id,
                        dark_store=dark_store,
                        is_active=True,
                    )
                )

            except DeliverySlot.DoesNotExist:

                raise serializers.ValidationError({
                    "delivery_slot_id": (
                        "Invalid delivery slot for "
                        "the selected dark store."
                    )
                })

        # =====================================================
        # STORE RESOLVED VALUES
        # =====================================================

        attrs["resolved_dark_store"] = store_obj

        attrs["resolved_delivery_zone"] = (
            matching_zone
        )

        attrs["resolved_delivery_slot"] = (
            delivery_slot
        )

        attrs["calculated_distance_km"] = (
            distance_km
        )

        attrs["calculated_delivery_fee"] = (
            delivery_fee
        )

        return attrs

    # =========================================================
    # CREATE ORDER
    # =========================================================

    def create(self, validated_data):

        user = self.context["request"].user

        dark_store = validated_data[
            "resolved_dark_store"
        ]

        delivery_zone = validated_data[
            "resolved_delivery_zone"
        ]

        saved_address = validated_data.get(
            "resolved_address_obj"
        )

        delivery_slot = validated_data.get(
            "resolved_delivery_slot"
        )

        # =====================================================
        # TRACKING NUMBER
        # =====================================================

        tracking_number = (
            f"TRK-{uuid.uuid4().hex[:12].upper()}"
        )

        # =====================================================
        # CREATE DELIVERY ORDER
        # =====================================================

        delivery_order = DeliveryOrder.objects.create(

            tracking_number=tracking_number,

            # Customer
            user=user,

            # Routing
            dark_store=dark_store,

            delivery_zone=delivery_zone,

            # Rider is assigned later
            rider=None,

            # Saved address reference
            saved_address=saved_address,

            # Address snapshot
            recipient_name=validated_data[
                "recipient_name"
            ],

            recipient_phone=validated_data[
                "recipient_phone"
            ],

            street_address=validated_data[
                "street_address"
            ],

            area=validated_data[
                "area"
            ],

            city=validated_data[
                "city"
            ],

            # GPS snapshot
            location=validated_data[
                "location_point"
            ],

            # Delivery
            delivery_slot=delivery_slot,

            distance_km=validated_data[
                "calculated_distance_km"
            ],

            delivery_fee=validated_data[
                "calculated_delivery_fee"
            ],

            # Initial state
            status=DeliveryOrder.Status.PENDING,
        )

        return delivery_order


# =============================================================
# DELIVERY ORDER RESPONSE SERIALIZER
# =============================================================

class DeliveryOrderSerializer(
    serializers.ModelSerializer
):

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    service_area_name = serializers.CharField(
        source="dark_store.service_area.name",
        read_only=True,
    )

    delivery_zone_name = serializers.CharField(
        source="delivery_zone.name",
        read_only=True,
        allow_null=True,
    )

    rider_name = serializers.SerializerMethodField()

    latitude = serializers.SerializerMethodField()

    longitude = serializers.SerializerMethodField()

    class Meta:

        model = DeliveryOrder

        fields = (
            "id",
            "tracking_number",

            # Store
            "dark_store",
            "dark_store_name",
            "service_area_name",

            # Delivery zone
            "delivery_zone",
            "delivery_zone_name",

            # Rider
            "rider",
            "rider_name",

            # Address
            "saved_address",
            "recipient_name",
            "recipient_phone",
            "street_address",
            "area",
            "city",

            # GPS
            "latitude",
            "longitude",

            # Delivery
            "delivery_slot",
            "distance_km",
            "delivery_fee",

            # Status
            "status",

            # Timestamp
            "created_at",
        )

        read_only_fields = fields

    # =========================================================
    # RIDER NAME
    # =========================================================

    def get_rider_name(self, obj) -> str | None:

        if not obj.rider:
            return None

        return obj.rider.get_full_name()

    # =========================================================
    # LATITUDE
    # =========================================================

    def get_latitude(self, obj) -> float | None:

        if not obj.location:
            return None

        return obj.location.y

    # =========================================================
    # LONGITUDE
    # =========================================================

    def get_longitude(self, obj) -> float | None:

        if not obj.location:
            return None

        return obj.location.x