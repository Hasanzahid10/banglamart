from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Wishlist, WishlistItem
from .serializers import (
    WishlistSerializer,
    ToggleWishlistSerializer,
)


class WishlistViewSet(viewsets.ViewSet):
    """
    Customer wishlist management.
    """

    permission_classes = [
        permissions.IsAuthenticated
    ]

    serializer_class = WishlistSerializer

    # =========================================================
    # GET /api/wishlist/
    # =========================================================

    def list(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(
            user=request.user
        )

        serializer = WishlistSerializer(
            wishlist,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # POST /api/wishlist/toggle/
    # =========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="toggle",
    )
    def toggle(self, request):
        serializer = ToggleWishlistSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        product_id = (
            serializer.validated_data["product_id"]
        )

        wishlist, _ = Wishlist.objects.get_or_create(
            user=request.user
        )

        item = WishlistItem.objects.filter(
            wishlist=wishlist,
            product_id=product_id,
        ).first()

        if item:
            item.delete()
            added = False
            message = "Product removed from wishlist."

        else:
            WishlistItem.objects.create(
                wishlist=wishlist,
                product_id=product_id,
            )
            added = True
            message = "Product added to wishlist."

        wishlist.refresh_from_db()

        wishlist_data = WishlistSerializer(
            wishlist,
            context={"request": request},
        ).data

        return Response(
            {
                "message": message,
                "added": added,
                "wishlist": wishlist_data,
            },
            status=status.HTTP_200_OK,
        )