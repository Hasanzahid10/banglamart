from django.db.models import Prefetch
from django.core.cache import cache

from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.filters import (
    SearchFilter,
    OrderingFilter,
)

from django_filters.rest_framework import (
    DjangoFilterBackend,
)

from .models import (
    Product,
    ProductInventory,
    ProductImage,
)

from .serializers import (
    ProductSerializer,
    ProductInventorySerializer,
    CustomerProductSerializer,
)

from .filters import ProductFilter


class ProductViewSet(viewsets.ModelViewSet):
    """
    Product catalog API.

    CUSTOMER:
        GET /api/products/
        GET /api/products/<id>/

        Customers see products available from
        their serving dark store.

    ADMIN:
        Full product catalog management.

    DARK STORE MANAGER:
        Can browse products but should NOT create
        or delete global products unless explicitly
        given catalog permission.
    """

    lookup_value_regex = r"\d+"

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name_en",
        "name_bn",
        "brand",
        "description",
        "sku",
    ]

    ordering_fields = [
        "base_price",
        "created_at",
        "name_en",
    ]

    ordering = [
        "-created_at",
    ]

    def perform_create(self, serializer):
        product = serializer.save()
        gallery_files = self.request.FILES.getlist("gallery_images")
        for index, file in enumerate(gallery_files):
            ProductImage.objects.create(
                product=product,
                image=file,
                display_order=index + 1,
            )

    def perform_update(self, serializer):
        product = serializer.save()
        gallery_files = self.request.FILES.getlist("gallery_images")
        if gallery_files:
            for index, file in enumerate(gallery_files):
                ProductImage.objects.create(
                    product=product,
                    image=file,
                    display_order=index + 1,
                )

    # =========================================================
    # QUERYSET
    # =========================================================

    def get_queryset(self):

        user = self.request.user

        # -----------------------------------------------------
        # ADMIN
        # -----------------------------------------------------

        if (
            user.is_authenticated
            and user.role == "ADMIN"
        ):

            return (
                Product.objects
                .select_related(
                    "category",
                )
                .prefetch_related(
                    Prefetch(
                        "inventories",
                        queryset=(
                            ProductInventory.objects
                            .select_related(
                                "dark_store",
                                "dark_store__service_area",
                            )
                        ),
                    )
                )
            )

        # -----------------------------------------------------
        # CUSTOMER / PUBLIC
        # -----------------------------------------------------

        return (
            Product.objects
            .filter(
                is_active=True,
            )
            .select_related(
                "category",
            )
            .prefetch_related(
                Prefetch(
                    "inventories",
                    queryset=(
                        ProductInventory.objects
                        .filter(
                            is_available=True,
                            stock_qty__gt=0,
                            dark_store__is_active=True,
                            dark_store__service_area__is_active=True,
                        )
                        .select_related(
                            "dark_store",
                            "dark_store__service_area",
                        )
                    ),
                )
            )
        )

    # =========================================================
    # SERIALIZER
    # =========================================================

    def get_serializer_class(self):

        if self.action in [
            "list",
            "retrieve",
        ]:

            # Customer-facing response
            if not (
                self.request.user.is_authenticated
                and self.request.user.role == "ADMIN"
            ):

                return CustomerProductSerializer

        return ProductSerializer

    # =========================================================
    # PERMISSIONS
    # =========================================================

    def get_permissions(self):
        return [
            permissions.AllowAny()
        ]
    #=========================================
    # list cache fuction 
    #==========================================
#    def list(self, request, *args, **kwargs):
#
#       cache_key = "banglamart:products:list"
#
#       cached_products = cache.get(cache_key)
#
#            return Response(cached_products)

#        queryset = self.filter_queryset(self.get_queryset())
#
#       serializer = self.get_serializer(queryset, many=True)
#
#       cache.set(
#           cache_key,
##            serializer.data,
#           timeout=300,
#       )
##
#       return Response(serializer.data)



class ProductInventoryViewSet(viewsets.ModelViewSet):
    """
    Manage product stock and pricing for dark stores.

    Admin/staff only.
    """

    lookup_value_regex = r"\d+"

    queryset = (
        ProductInventory.objects
        .select_related(
            "product",
            "dark_store",
        )
    )

    serializer_class = ProductInventorySerializer

    permission_classes = [
        permissions.IsAdminUser
    ]

    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
    ]

    filterset_fields = [
        "dark_store",
        "product",
        "is_available",
    ]

    ordering_fields = [
        "stock_qty",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-updated_at"
    ]