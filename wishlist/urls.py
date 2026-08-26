from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WishlistViewSet


router = DefaultRouter()

router.register(
    r"",
    WishlistViewSet,
    basename="wishlist",
)


urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]