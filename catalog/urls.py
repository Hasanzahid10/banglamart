from django.urls import path

from .views import (
    CategoryListView,
    CategoryDetailView,
    CategoryAdminDetailView,
)

urlpatterns = [
    path(
        "categories/",
        CategoryListView.as_view(),
        name="category-list",
    ),

    path(
        "categories/id/<int:pk>/",
        CategoryAdminDetailView.as_view(),
        name="category-admin-detail",
    ),

    path(
        "categories/<slug:slug>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
]