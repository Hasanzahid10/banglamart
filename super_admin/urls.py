from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SuperAdminViewSet, FeatureFlagViewSet

router = DefaultRouter()
router.register(r"feature-flags", FeatureFlagViewSet, basename="superadmin-flags")
router.register(r"", SuperAdminViewSet, basename="superadmin")

urlpatterns = [
    path("", include(router.urls)),
]