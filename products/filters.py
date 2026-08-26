import django_filters

from .models import Product


class ProductFilter(django_filters.FilterSet):

    # =========================================================
    # PRICE
    # =========================================================

    min_price = django_filters.NumberFilter(
        method="filter_min_price",
    )

    max_price = django_filters.NumberFilter(
        method="filter_max_price",
    )

    # =========================================================
    # CATEGORY
    # =========================================================

    category_slug = django_filters.CharFilter(
        field_name="category__slug",
        lookup_expr="iexact",
    )

    # =========================================================
    # BRAND
    # =========================================================

    brand = django_filters.CharFilter(
        field_name="brand",
        lookup_expr="iexact",
    )

    # =========================================================
    # DARK STORE
    # =========================================================

    dark_store_id = django_filters.NumberFilter(
        field_name="inventories__dark_store_id",
        lookup_expr="exact",
    )

    # =========================================================
    # SERVICE AREA
    # =========================================================

    service_area_id = django_filters.NumberFilter(
        field_name=(
            "inventories__dark_store__service_area_id"
        ),
        lookup_expr="exact",
    )

    # =========================================================
    # STOCK
    # =========================================================

    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock",
    )

    # =========================================================
    # AVAILABILITY
    # =========================================================

    is_available = django_filters.BooleanFilter(
        method="filter_is_available",
    )

    # =========================================================
    # PRODUCT ACTIVE
    # =========================================================

    is_active = django_filters.BooleanFilter(
        field_name="is_active",
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:

        model = Product

        fields = [
            "category",
            "category_slug",
            "brand",
            "is_active",
            "dark_store_id",
            "service_area_id",
            "min_price",
            "max_price",
            "in_stock",
            "is_available",
        ]

    # =========================================================
    # HELPER
    # =========================================================

    def _inventory_queryset(self, queryset):

        """
        Restrict product queries to the requested
        dark store when dark_store_id is provided.
        """

        dark_store_id = self.data.get(
            "dark_store_id"
        )

        filters = {
            "inventories__is_available": True,
        }

        if dark_store_id:
            filters[
                "inventories__dark_store_id"
            ] = dark_store_id

        return queryset.filter(
            **filters
        )

    # =========================================================
    # MIN PRICE
    # =========================================================

    def filter_min_price(
        self,
        queryset,
        name,
        value,
    ):

        queryset = self._inventory_queryset(
            queryset
        )

        return queryset.filter(
            inventories__store_price__gte=value
        ).distinct()

    # =========================================================
    # MAX PRICE
    # =========================================================

    def filter_max_price(
        self,
        queryset,
        name,
        value,
    ):

        queryset = self._inventory_queryset(
            queryset
        )

        return queryset.filter(
            inventories__store_price__lte=value
        ).distinct()

    # =========================================================
    # IN STOCK
    # =========================================================

    def filter_in_stock(
        self,
        queryset,
        name,
        value,
    ):

        if not value:
            return queryset

        queryset = self._inventory_queryset(
            queryset
        )

        return queryset.filter(
            inventories__stock_qty__gt=0,
        ).distinct()

    # =========================================================
    # IS AVAILABLE
    # =========================================================

    def filter_is_available(
        self,
        queryset,
        name,
        value,
    ):

        if value:

            queryset = self._inventory_queryset(
                queryset
            )

            return queryset.distinct()

        return queryset