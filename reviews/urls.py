from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProductReviewViewSet


router = DefaultRouter()

router.register(
    r"products",
    ProductReviewViewSet,
    basename="product-reviews",
)


urlpatterns = [
    path("", include(router.urls)),
]