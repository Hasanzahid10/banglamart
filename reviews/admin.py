from django.contrib import admin

from .models import ProductReview, ReviewImage


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    fields = ("image", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "product",
        "user",
        "rating",
        "is_verified_purchase",
        "is_approved",
        "created_at",
    )

    list_filter = (
        "rating",
        "is_verified_purchase",
        "is_approved",
        "created_at",
    )

    search_fields = (
        "product__name_en",
        "user__email",
        "user__phone_number",
        "comment",
        "title",
    )

    readonly_fields = (
        "id",
        "user",
        "product",
        "order",
        "is_verified_purchase",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    list_per_page = 25

    inlines = [
        ReviewImageInline,
    ]