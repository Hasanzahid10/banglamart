from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BannerViewSet, FlashSaleViewSet


router = DefaultRouter()

router.register(
    r"banners",
    BannerViewSet,
    basename="promotions-banners",
)

router.register(
    r"flash-sales",
    FlashSaleViewSet,
    basename="promotions-flash-sales",
)


urlpatterns = [
    path("", include(router.urls)),
]