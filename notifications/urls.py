from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    DeviceTokenViewSet,
)


router = DefaultRouter()

router.register(
    r"device-tokens",
    DeviceTokenViewSet,
    basename="device-tokens",
)

router.register(
    r"notifications",
    NotificationViewSet,
    basename="notifications",
)


urlpatterns = [
    path("", include(router.urls)),
]