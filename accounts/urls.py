from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProfileViewSet, AddressViewSet


router = DefaultRouter()

router.register(
    r"addresses",
    AddressViewSet,
    basename="address",
)


profile_view = ProfileViewSet.as_view({
    "get": "list",
    "post": "create",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})


urlpatterns = [
    path(
        "profile/",
        profile_view,
        name="profile",
    ),

    path(
        "",
        include(router.urls),
    ),
]