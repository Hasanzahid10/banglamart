from django.contrib import admin

from .models import Coupon, CouponUsage


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "min_order_amount",
        "dark_store",
        "times_used",
        "total_usage_limit",
        "per_user_limit",
        "is_active",
        "start_date",
        "end_date",
    )

    list_filter = (
        "discount_type",
        "is_active",
        "dark_store",
        "start_date",
        "end_date",
    )

    search_fields = (
        "code",
        "description",
        "dark_store__name",
        "dark_store__code",
    )

    readonly_fields = (
        "times_used",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "dark_store",
    )

    fieldsets = (
        (
            "Coupon Information",
            {
                "fields": (
                    "code",
                    "description",
                    "is_active",
                )
            },
        ),
        (
            "Discount",
            {
                "fields": (
                    "discount_type",
                    "discount_value",
                    "min_order_amount",
                    "max_discount_amount",
                )
            },
        ),
        (
            "Regional / Dark Store",
            {
                "fields": (
                    "dark_store",
                )
            },
        ),
        (
            "Usage Limits",
            {
                "fields": (
                    "total_usage_limit",
                    "per_user_limit",
                    "times_used",
                )
            },
        ),
        (
            "Validity",
            {
                "fields": (
                    "start_date",
                    "end_date",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):

    list_display = (
        "coupon",
        "user",
        "order",
        "discount_amount",
        "used_at",
    )

    list_filter = (
        "coupon",
        "used_at",
    )

    search_fields = (
        "coupon__code",
        "user__phone_number",
        "user__email",
        "order__order_number",
    )

    readonly_fields = (
        "id",
        "coupon",
        "user",
        "order",
        "discount_amount",
        "used_at",
    )

    autocomplete_fields = (
        "coupon",
        "user",
        "order",
    )