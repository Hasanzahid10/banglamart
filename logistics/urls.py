from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LogisticsViewSet


router = DefaultRouter()

router.register(
    r"orders",
    LogisticsViewSet,
    basename="logistics-order",
)

urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]