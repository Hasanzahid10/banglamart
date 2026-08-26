from django.core.cache import cache

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .cache import (
    CATEGORY_CACHE_TTL,
    CATEGORY_LIST_CACHE_KEY,
    category_detail_cache_key,
)
from .models import Category
from .serializers import CategoryTreeSerializer


class CategoryListView(APIView):
    """
    GET /api/catalog/categories/

    Returns the complete active category tree.

    Public endpoint.
    """

    permission_classes = [
        permissions.AllowAny,
    ]

    def get(self, request, *args, **kwargs):

        # --------------------------------
        # 1. Check Redis cache
        # --------------------------------

        cached_data = cache.get(
            CATEGORY_LIST_CACHE_KEY
        )

        if cached_data is not None:

            return Response(
                cached_data,
                status=status.HTTP_200_OK,
            )

        # --------------------------------
        # 2. Query database
        # --------------------------------

        root_categories = (
            Category.objects
            .filter(
                parent=None,
                is_active=True,
            )
            .order_by(
                "display_order",
                "name_en",
            )
        )

        # --------------------------------
        # 3. Serialize
        # --------------------------------

        serializer = CategoryTreeSerializer(
            root_categories,
            many=True,
            context={
                "request": request,
            },
        )

        data = serializer.data

        # --------------------------------
        # 4. Save in Redis
        # --------------------------------

        cache.set(
            CATEGORY_LIST_CACHE_KEY,
            data,
            CATEGORY_CACHE_TTL,
        )

        # --------------------------------
        # 5. Return response
        # --------------------------------

        return Response(
            data,
            status=status.HTTP_200_OK,
        )


class CategoryDetailView(APIView):
    """
    GET /api/catalog/categories/<slug>/

    Returns one active category and its
    active child categories.

    Public endpoint.
    """

    permission_classes = [
        permissions.AllowAny,
    ]

    def get(
        self,
        request,
        slug,
        *args,
        **kwargs,
    ):

        # --------------------------------
        # 1. Generate cache key
        # --------------------------------

        cache_key = category_detail_cache_key(
            slug
        )

        # --------------------------------
        # 2. Check Redis
        # --------------------------------

        cached_data = cache.get(
            cache_key
        )

        if cached_data is not None:

            return Response(
                cached_data,
                status=status.HTTP_200_OK,
            )

        # --------------------------------
        # 3. Query database
        # --------------------------------

        category = (
            Category.objects
            .filter(
                slug=slug,
                is_active=True,
            )
            .first()
        )

        if category is None:

            return Response(
                {
                    "detail": "Category not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # --------------------------------
        # 4. Serialize
        # --------------------------------

        serializer = CategoryTreeSerializer(
            category,
            context={
                "request": request,
            },
        )

        data = serializer.data

        # --------------------------------
        # 5. Save in Redis
        # --------------------------------

        cache.set(
            cache_key,
            data,
            CATEGORY_CACHE_TTL,
        )

        # --------------------------------
        # 6. Return response
        # --------------------------------

        return Response(
            data,
            status=status.HTTP_200_OK,
        )