from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import RiderViewSet, DeliveryTaskViewSet


router = DefaultRouter()

router.register(
    r"riders",
    RiderViewSet,
    basename="rider",
)

router.register(
    r"tasks",
    DeliveryTaskViewSet,
    basename="delivery-task",
)


urlpatterns = [
    path("", include(router.urls)),
]