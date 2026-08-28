from rest_framework import serializers

from .models import Category
from drf_spectacular.utils import extend_schema_field


class SubCategorySerializer(serializers.ModelSerializer):
    """
    Recursive serializer for child categories.
    """

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category

        fields = [
            "id",
            "name_en",
            "name_bn",
            "slug",
            "icon",
            "display_order",
            "is_active",
            "children",
        ]

        read_only_fields = [
            "id",
        ]

    def get_children(self, obj):
        """
        Return only active child categories.
        """

        children = obj.get_children().filter(
            is_active=True
        )

        return SubCategorySerializer(
            children,
            many=True,
            context=self.context,
        ).data


SubCategorySerializer.get_children = extend_schema_field(SubCategorySerializer(many=True))(SubCategorySerializer.get_children)


class CategoryTreeSerializer(serializers.ModelSerializer):
    """
    Root category tree serializer.

    Returns active root categories with their
    active child categories recursively.
    """

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category

        fields = [
            "id",
            "name_en",
            "name_bn",
            "slug",
            "icon",
            "banner",
            "is_active",
            "is_featured",
            "display_order",
            "children",
        ]

        read_only_fields = [
            "id",
        ]

    @extend_schema_field(SubCategorySerializer(many=True))
    def get_children(self, obj):
        children = obj.get_children().filter(
            is_active=True
        )

        return SubCategorySerializer(
            children,
            many=True,
            context=self.context,
        ).data