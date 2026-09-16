from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CartViewSet,
    GuestCartSyncView,
    GuestCartFetchView,
    GuestCartConvertView,
    AdminGuestCartViewSet,
)

router = DefaultRouter()
router.register(r"admin/guest-carts", AdminGuestCartViewSet, basename="admin-guest-carts")
router.register(r"", CartViewSet, basename="cart")

urlpatterns = [
    path("guest-sync/", GuestCartSyncView.as_view(), name="guest-cart-sync"),
    path("guest-fetch/", GuestCartFetchView.as_view(), name="guest-cart-fetch"),
    path("guest-convert/", GuestCartConvertView.as_view(), name="guest-cart-convert"),
    path("", include(router.urls)),
]