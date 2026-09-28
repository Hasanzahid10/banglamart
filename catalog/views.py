# pyrefly: ignore [missing-import]
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
from .serializers import CategoryTreeSerializer, CategoryCreateUpdateSerializer
from drf_spectacular.utils import extend_schema


from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class CategoryListView(APIView):
    """
    GET /api/catalog/categories/
    POST /api/catalog/categories/

    Returns/Creates categories and sub-categories in active category tree.
    """

    permission_classes = [
        permissions.AllowAny,
    ]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = CategoryTreeSerializer

    @extend_schema(
        operation_id="catalog_categories_list",
        responses={200: CategoryTreeSerializer}
    )
    def get(self, request, *args, **kwargs):

        # --------------------------------
        # 1. Check Redis cache (Bypass if nocache=true)
        # --------------------------------

        nocache = request.query_params.get("nocache") == "true"
        if not nocache:
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

    @extend_schema(
        operation_id="catalog_categories_create",
        request=CategoryCreateUpdateSerializer,
        responses={201: CategoryCreateUpdateSerializer}
    )
    def post(self, request, *args, **kwargs):
        data = {}
        for key in request.data:
            data[key] = request.data.get(key)

        # Support 'image' or 'icon' file uploads
        if 'image' in request.FILES:
            data['icon'] = request.FILES['image']
            data['image'] = request.FILES['image']
        elif 'icon' in request.FILES:
            data['icon'] = request.FILES['icon']
            data['image'] = request.FILES['icon']

        if 'is_active' not in data or data.get('is_active') in (None, '', 'undefined'):
            data['is_active'] = True

        parent_val = data.get("parent")
        if not parent_val or parent_val in ("null", "undefined", None, ""):
            data["parent"] = None
        else:
            try:
                parent_id = int(parent_val)
                if Category.objects.filter(pk=parent_id).exists():
                    data["parent"] = parent_id
                else:
                    data["parent"] = None
            except (ValueError, TypeError):
                data["parent"] = None

        serializer = CategoryCreateUpdateSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            category = serializer.save()

            # Rebuild MPTT tree structure
            try:
                Category.objects.rebuild()
            except Exception:
                pass

            # Invalidate Redis category cache
            cache.delete(CATEGORY_LIST_CACHE_KEY)

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class CategoryAdminDetailView(APIView):
    """
    GET /api/catalog/categories/id/<int:pk>/
    PUT /api/catalog/categories/id/<int:pk>/
    PATCH /api/catalog/categories/id/<int:pk>/
    DELETE /api/catalog/categories/id/<int:pk>/
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        try:
            return Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return None

    def get(self, request, pk, *args, **kwargs):
        category = self.get_object(pk)
        if not category:
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CategoryCreateUpdateSerializer(category, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk, *args, **kwargs):
        category = self.get_object(pk)
        if not category:
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        
        data = {}
        for key in request.data:
            data[key] = request.data.get(key)

        if 'image' in request.FILES:
            data['icon'] = request.FILES['image']
            data['image'] = request.FILES['image']
        elif 'icon' in request.FILES:
            data['icon'] = request.FILES['icon']
            data['image'] = request.FILES['icon']

        serializer = CategoryCreateUpdateSerializer(category, data=data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            cache.delete(CATEGORY_LIST_CACHE_KEY)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, *args, **kwargs):
        return self.put(request, pk, *args, **kwargs)

    def delete(self, request, pk, *args, **kwargs):
        category = self.get_object(pk)
        if not category:
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            descendants = category.get_descendants(include_self=True)
            from products.models import Product, ProductImage, ProductInventory
            from cart.models import CartItem
            from wishlist.models import WishlistItem
            from promotions.models import FlashSaleItem
            from orders.models import OrderItem

            products = list(Product.objects.filter(category__in=descendants))
            for prod in products:
                # 1. Delete ProductImages
                try:
                    ProductImage.objects.filter(product=prod).delete()
                except Exception:
                    pass

                # 2. Delete Wishlist & FlashSale items
                try:
                    WishlistItem.objects.filter(product=prod).delete()
                except Exception:
                    pass
                try:
                    FlashSaleItem.objects.filter(product=prod).delete()
                except Exception:
                    pass

                # 3. Clean Inventories, CartItems & OrderItems FK
                inv_ids = list(ProductInventory.objects.filter(product=prod).values_list('id', flat=True))
                if inv_ids:
                    try:
                        CartItem.objects.filter(inventory_id__in=inv_ids).delete()
                    except Exception:
                        pass
                    try:
                        OrderItem.objects.filter(inventory_id__in=inv_ids).update(inventory=None)
                    except Exception:
                        pass
                    try:
                        ProductInventory.objects.filter(product=prod).delete()
                    except Exception:
                        pass

                # 4. Hard Delete Product
                try:
                    prod.delete()
                except Exception:
                    prod.is_active = False
                    prod.save()

            # 5. Delete Category and all descendants from DB
            try:
                descendants.delete()
            except Exception:
                category.delete()

            try:
                Category.objects.rebuild()
            except Exception:
                pass

            cache.delete(CATEGORY_LIST_CACHE_KEY)
            return Response({"detail": "Category and all its products deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"Failed to delete category: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


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
    serializer_class = CategoryTreeSerializer

    @extend_schema(
        operation_id="catalog_categories_retrieve",
        responses={200: CategoryTreeSerializer}
    )
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