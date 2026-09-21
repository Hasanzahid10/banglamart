from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet


router = DefaultRouter()

router.register(
    r"",
    AuthViewSet,
    basename="auth",
)

urlpatterns = [
    path("me/", AuthViewSet.as_view({"get": "me", "patch": "me", "put": "me"}), name="auth-me"),
    path("change-password/", AuthViewSet.as_view({"post": "change_password"}), name="auth-change-password"),
    path("", include(router.urls)),
]