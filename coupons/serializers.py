from decimal import Decimal
from rest_framework import serializers

from .models import Coupon, CouponUsage


class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Coupon

        fields = (
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "min_order_amount",
            "max_discount_amount",
            "start_date",
            "end_date",
            "is_active",
            "dark_store",
            "is_valid",
        )

        read_only_fields = (
            "id",
            "is_valid",
        )

    def get_is_valid(self, obj):
        valid, _ = obj.is_valid_now
        return valid


class ApplyCouponSerializer(serializers.Serializer):

    code = serializers.CharField(
        max_length=50,
    )

    order_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    def validate(self, attrs):

        request = self.context["request"]
        user = request.user

        code = attrs["code"].strip().upper()
        order_amount = attrs["order_amount"]

        # --------------------------------------------------
        # GET COUPON
        # --------------------------------------------------

        try:
            coupon = (
                Coupon.objects
                .select_related("dark_store")
                .get(code=code)
            )

        except Coupon.DoesNotExist:
            raise serializers.ValidationError({
                "code": "Invalid coupon code."
            })

        # --------------------------------------------------
        # BASIC VALIDITY
        # --------------------------------------------------

        is_valid, message = coupon.is_valid_now

        if not is_valid:
            raise serializers.ValidationError({
                "code": message
            })

        # --------------------------------------------------
        # MINIMUM ORDER
        # --------------------------------------------------

        if order_amount < coupon.min_order_amount:

            raise serializers.ValidationError({
                "order_amount": (
                    f"Minimum order amount is "
                    f"{coupon.min_order_amount} BDT."
                )
            })

        # --------------------------------------------------
        # USER USAGE LIMIT
        # --------------------------------------------------

        user_usage_count = (
            CouponUsage.objects
            .filter(
                coupon=coupon,
                user=user,
            )
            .count()
        )

        if user_usage_count >= coupon.per_user_limit:

            raise serializers.ValidationError({
                "code": (
                    "You have reached the usage limit "
                    "for this coupon."
                )
            })

        # --------------------------------------------------
        # DARK STORE VALIDATION
        # --------------------------------------------------

        cart = getattr(
            user,
            "cart",
            None,
        )

        if coupon.dark_store:

            if not cart or not cart.dark_store:

                raise serializers.ValidationError({
                    "code": (
                        "Please select your delivery "
                        "location before using this coupon."
                    )
                })

            if cart.dark_store_id != coupon.dark_store_id:

                raise serializers.ValidationError({
                    "code": (
                        "This coupon is not available "
                        "at your selected DarkStore."
                    )
                })

            if not coupon.dark_store.is_active:

                raise serializers.ValidationError({
                    "code": (
                        "This coupon's DarkStore is "
                        "currently unavailable."
                    )
                })

        # --------------------------------------------------
        # CALCULATE DISCOUNT
        # --------------------------------------------------

        discount_amount = coupon.calculate_discount(
            order_amount
        )

        if discount_amount <= 0:

            raise serializers.ValidationError({
                "code": (
                    "This coupon cannot be applied "
                    "to this order."
                )
            })

        # --------------------------------------------------
        # STORE RESOLVED DATA
        # --------------------------------------------------

        attrs["coupon"] = coupon
        attrs["code"] = code
        attrs["discount_amount"] = discount_amount

        return attrs