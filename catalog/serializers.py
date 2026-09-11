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


class CategoryCreateUpdateSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    icon = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name_en",
            "name_bn",
            "slug",
            "parent",
            "display_order",
            "is_active",
            "is_featured",
            "icon",
        ]
        read_only_fields = ["id", "slug"]

    def create(self, validated_data):
        from django.utils.text import slugify
        name_en = validated_data.get("name_en", "")
        base_slug = slugify(name_en) if name_en else "category"
        slug = base_slug
        count = 1
        while Category.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{count}"
            count += 1
        validated_data["slug"] = slug
        return Category.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance