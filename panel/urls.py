from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegionAdminProfileViewSet,
    RegionViewSet,
    AdminDarkStoreViewSet,
)


router = DefaultRouter()

router.register(
    r"profile",
    RegionAdminProfileViewSet,
    basename="admin-profile",
)

router.register(
    r"regions",
    RegionViewSet,
    basename="admin-regions",
)

router.register(
    r"dark-stores",
    AdminDarkStoreViewSet,
    basename="admin-dark-stores",
)

urlpatterns = [
    path("", include(router.urls)),
]