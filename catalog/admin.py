from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import Category


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):

    # Field used to display the category tree indentation
    mptt_indent_field = "name_en"

    # ---------------------------------------------------------
    # LIST VIEW
    # ---------------------------------------------------------

    list_display = (
        "tree_actions",
        "indented_title",
        "name_bn",
        "slug",
        "display_order",
        "is_active",
        "is_featured",
    )

    list_display_links = (
        "indented_title",
    )

    list_editable = (
        "display_order",
        "is_active",
        "is_featured",
    )

    list_filter = (
        "is_active",
        "is_featured",
    )

    search_fields = (
        "name_en",
        "name_bn",
        "slug",
    )

    ordering = (
        "tree_id",
        "lft",
    )

    # Automatically generate slug from English name
    prepopulated_fields = {
        "slug": ("name_en",),
    }

    # ---------------------------------------------------------
    # FORM
    # ---------------------------------------------------------

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name_en",
                    "name_bn",
                    "slug",
                    "parent",
                )
            },
        ),
        (
            "Visual Assets",
            {
                "fields": (
                    "icon",
                    "banner",
                )
            },
        ),
        (
            "Display Controls",
            {
                "fields": (
                    "display_order",
                    "is_active",
                    "is_featured",
                )
            },
        ),
    )