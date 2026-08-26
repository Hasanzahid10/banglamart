from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ProductInventoryViewSet

# Initialize DefaultRouter
router = DefaultRouter()

# Register ViewSets with the router
router.register(r'items', ProductViewSet, basename='product')
router.register(r'inventory', ProductInventoryViewSet, basename='product-inventory')

urlpatterns = [
    path('', include(router.urls)),
]