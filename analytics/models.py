import uuid

from django.db import models


class DailySalesSummary(models.Model):
    """
    Daily aggregated sales and order statistics
    for each dark store.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    date = models.DateField(
        db_index=True,
    )

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.CASCADE,
        related_name="daily_sales_summaries",
    )

    total_orders = models.PositiveIntegerField(
        default=0,
    )

    completed_orders = models.PositiveIntegerField(
        default=0,
    )

    cancelled_orders = models.PositiveIntegerField(
        default=0,
    )

    total_revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    delivery_fees_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    discounts_given = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    net_revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-date"]

        constraints = [
            models.UniqueConstraint(
                fields=["date", "dark_store"],
                name="unique_daily_sales_per_store",
            ),
        ]

        indexes = [
            models.Index(
                fields=["dark_store", "-date"],
            ),
            models.Index(
                fields=["date", "dark_store"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.date} - "
            f"{self.dark_store.code}: "
            f"{self.net_revenue} BDT"
        )


class ProductSalesMetric(models.Model):
    """
    Lifetime aggregated performance of a product.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="sales_metric",
    )

    total_units_sold = models.PositiveIntegerField(
        default=0,
    )

    total_revenue_generated = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    total_orders = models.PositiveIntegerField(
        default=0,
    )

    last_sold_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-total_units_sold"]

    def __str__(self):
        return (
            f"{self.product.name_en} - "
            f"{self.total_units_sold} units sold"
        )


class DailyProductSales(models.Model):
    """
    Daily product sales per dark store.

    Useful for:
        - Top products
        - Store performance
        - Demand analysis
        - Recommendations
        - Inventory forecasting
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    date = models.DateField(
        db_index=True,
    )

    dark_store = models.ForeignKey(
        "logistics.DarkStore",
        on_delete=models.CASCADE,
        related_name="daily_product_sales",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="daily_sales",
    )

    units_sold = models.PositiveIntegerField(
        default=0,
    )

    revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    orders_count = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["-date"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "date",
                    "dark_store",
                    "product",
                ],
                name="unique_daily_product_store_sales",
            ),
        ]

        indexes = [
            models.Index(
                fields=["date", "dark_store"],
            ),
            models.Index(
                fields=["date", "product"],
            ),
            models.Index(
                fields=["dark_store", "product"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.date} - "
            f"{self.dark_store.code} - "
            f"{self.product.name_en}"
        )
