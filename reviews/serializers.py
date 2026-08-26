from django.db import transaction
from rest_framework import serializers

from orders.models import OrderItem
from products.models import Product

from .models import ProductReview, ReviewImage


# =========================================================
# REVIEW IMAGE
# =========================================================

class ReviewImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReviewImage

        fields = (
            "id",
            "image",
            "created_at",
        )

        read_only_fields = (
            "id",
            "created_at",
        )


# =========================================================
# PRODUCT REVIEW
# =========================================================

class ProductReviewSerializer(serializers.ModelSerializer):

    user_name = serializers.SerializerMethodField()

    images = ReviewImageSerializer(
        many=True,
        read_only=True,
    )

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
    )

    class Meta:
        model = ProductReview

        fields = (
            "id",
            "product",
            "user_name",
            "rating",
            "title",
            "comment",
            "is_verified_purchase",
            "dark_store_name",
            "images",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "user_name",
            "is_verified_purchase",
            "dark_store_name",
            "images",
            "created_at",
            "updated_at",
        )

    def get_user_name(self, obj):

        user = obj.user

        full_name = user.get_full_name()

        if full_name:
            return full_name

        return (
            getattr(user, "phone_number", None)
            or getattr(user, "email", None)
            or "Customer"
        )


# =========================================================
# CREATE REVIEW
# =========================================================

class CreateProductReviewSerializer(
    serializers.ModelSerializer
):

    order_item = serializers.PrimaryKeyRelatedField(
        queryset=(
            OrderItem.objects
            .select_related(
                "order",
                "order__user",
                "inventory",
                "inventory__product",
                "inventory__dark_store",
            )
        ),
        write_only=True,
    )

    uploaded_images = serializers.ListField(
        child=serializers.ImageField(
            max_length=5 * 1024 * 1024,
            allow_empty_file=False,
            use_url=False,
        ),
        required=False,
        write_only=True,
    )

    class Meta:
        model = ProductReview

        fields = (
            "product",
            "order_item",
            "rating",
            "title",
            "comment",
            "uploaded_images",
        )

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate(self, attrs):

        request = self.context["request"]
        user = request.user

        product = attrs["product"]
        order_item = attrs["order_item"]

        order = order_item.order
        inventory = order_item.inventory

        # -------------------------------------------------
        # 1. Order belongs to current user
        # -------------------------------------------------

        if order.user_id != user.id:

            raise serializers.ValidationError({
                "order_item": (
                    "This order item does not belong "
                    "to your account."
                )
            })

        # -------------------------------------------------
        # 2. Product must match OrderItem
        # -------------------------------------------------

        if inventory.product_id != product.id:

            raise serializers.ValidationError({
                "product": (
                    "This product does not belong "
                    "to the selected order item."
                )
            })

        # -------------------------------------------------
        # 3. Order must be delivered
        # -------------------------------------------------

        if order.status != Order.OrderStatus.DELIVERED:

            raise serializers.ValidationError({
                "order_item": (
                    "You can review a product only "
                    "after the order has been delivered."
                )
            })

        # -------------------------------------------------
        # 4. Payment must be completed
        # -------------------------------------------------

        if (
            order.payment_status
            != Order.PaymentStatus.PAID
        ):

            raise serializers.ValidationError({
                "order_item": (
                    "A product can only be reviewed "
                    "from a paid order."
                )
            })

        # -------------------------------------------------
        # 5. Prevent duplicate review for same purchase
        # -------------------------------------------------

        existing_review = (
            ProductReview.objects
            .filter(
                product=product,
                user=user,
                order=order,
            )
            .exists()
        )

        if existing_review:

            raise serializers.ValidationError({
                "product": (
                    "You have already reviewed "
                    "this product from this order."
                )
            })

        # -------------------------------------------------
        # 6. Image limit
        # -------------------------------------------------

        images = attrs.get(
            "uploaded_images",
            [],
        )

        if len(images) > 5:

            raise serializers.ValidationError({
                "uploaded_images": (
                    "You can upload a maximum "
                    "of 5 images."
                )
            })

        # -------------------------------------------------
        # 7. Optional image size validation
        # -------------------------------------------------

        max_size = 5 * 1024 * 1024

        for image in images:

            if image.size > max_size:

                raise serializers.ValidationError({
                    "uploaded_images": (
                        "Each image must be "
                        "5 MB or smaller."
                    )
                })

        # -------------------------------------------------
        # 8. Store useful objects for create()
        # -------------------------------------------------

        attrs["_order"] = order
        attrs["_inventory"] = inventory

        return attrs

    # =====================================================
    # CREATE
    # =====================================================

    @transaction.atomic
    def create(self, validated_data):

        images_data = validated_data.pop(
            "uploaded_images",
            [],
        )

        order_item = validated_data.pop(
            "order_item"
        )

        order = validated_data.pop(
            "_order"
        )

        inventory = validated_data.pop(
            "_inventory"
        )

        user = self.context["request"].user

        review = ProductReview.objects.create(
            user=user,
            product=inventory.product,
            order=order,
            dark_store=inventory.dark_store,
            is_verified_purchase=True,
            **validated_data,
        )

        ReviewImage.objects.bulk_create(
            [
                ReviewImage(
                    review=review,
                    image=image,
                )
                for image in images_data
            ]
        )

        return review