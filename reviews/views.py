from rest_framework import (
    permissions,
    status,
    viewsets,
)
from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.response import Response

from .models import ProductReview
from .serializers import (
    CreateProductReviewSerializer,
    ProductReviewSerializer,
)


class ProductReviewViewSet(viewsets.ModelViewSet):
    """
    Product Review API.

    PUBLIC
    ------

    GET /api/reviews/
    GET /api/reviews/<id>/


    CUSTOMER
    --------

    POST   /api/reviews/
    PATCH  /api/reviews/<id>/
    PUT    /api/reviews/<id>/
    DELETE /api/reviews/<id>/


    ADMIN
    -----

    Can view approved and unapproved reviews.
    Can approve/reject reviews.
    Can delete inappropriate reviews.
    """

    parser_classes = (
        JSONParser,
        MultiPartParser,
        FormParser,
    )

    # =========================================================
    # PERMISSIONS
    # =========================================================

    def get_permissions(self):

        # Anyone can read approved reviews
        if self.action in [
            "list",
            "retrieve",
        ]:
            return [
                permissions.AllowAny()
            ]

        return [
            permissions.IsAuthenticated()
        ]

    # =========================================================
    # SERIALIZER
    # =========================================================

    def get_serializer_class(self):

        if self.action == "create":
            return CreateProductReviewSerializer

        return ProductReviewSerializer

    # =========================================================
    # QUERYSET
    # =========================================================

    def get_queryset(self):

        user = self.request.user

        queryset = (
            ProductReview.objects
            .select_related(
                "product",
                "user",
                "order",
                "dark_store",
            )
            .prefetch_related(
                "images",
            )
        )

        # -----------------------------------------------------
        # ADMIN
        # -----------------------------------------------------

        if (
            user.is_authenticated
            and getattr(user, "role", None)
            in [
                "ADMIN",
                "SUPER_ADMIN",
            ]
        ):
            queryset = queryset

        # -----------------------------------------------------
        # PUBLIC / CUSTOMER
        # -----------------------------------------------------

        else:
            queryset = queryset.filter(
                is_approved=True
            )

        # -----------------------------------------------------
        # PRODUCT FILTER
        # -----------------------------------------------------

        product_id = (
            self.request.query_params.get(
                "product_id"
            )
        )

        if product_id:
            if not product_id.isdigit():
                return queryset.none()
            queryset = queryset.filter(
                product_id=product_id
            )

        # -----------------------------------------------------
        # DARK STORE FILTER
        # -----------------------------------------------------

        dark_store_id = (
            self.request.query_params.get(
                "dark_store_id"
            )
        )

        if dark_store_id:
            if not dark_store_id.isdigit():
                return queryset.none()
            queryset = queryset.filter(
                dark_store_id=dark_store_id
            )

        # -----------------------------------------------------
        # RATING FILTER
        # -----------------------------------------------------

        rating = (
            self.request.query_params.get(
                "rating"
            )
        )

        if rating:
            if not rating.isdigit():
                return queryset.none()
            queryset = queryset.filter(
                rating=rating
            )

        return queryset

    # =========================================================
    # CREATE
    # =========================================================

    def perform_create(self, serializer):

        serializer.save()

    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        request,
        *args,
        **kwargs,
    ):

        review = self.get_object()

        # -----------------------------------------------------
        # ADMIN
        # -----------------------------------------------------

        if self._is_admin(request.user):

            serializer = ProductReviewSerializer(
                review,
                data=request.data,
                partial=False,
                context={
                    "request": request,
                },
            )

            serializer.is_valid(
                raise_exception=True
            )

            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # -----------------------------------------------------
        # CUSTOMER OWNERSHIP
        # -----------------------------------------------------

        if review.user_id != request.user.id:

            return Response(
                {
                    "detail": (
                        "You can only edit "
                        "your own review."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProductReviewSerializer(
            review,
            data=request.data,
            partial=False,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # PARTIAL UPDATE
    # =========================================================

    def partial_update(
        self,
        request,
        *args,
        **kwargs,
    ):

        review = self.get_object()

        # -----------------------------------------------------
        # ADMIN
        # -----------------------------------------------------

        if self._is_admin(request.user):

            serializer = ProductReviewSerializer(
                review,
                data=request.data,
                partial=True,
                context={
                    "request": request,
                },
            )

            serializer.is_valid(
                raise_exception=True
            )

            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # -----------------------------------------------------
        # CUSTOMER OWNERSHIP
        # -----------------------------------------------------

        if review.user_id != request.user.id:

            return Response(
                {
                    "detail": (
                        "You can only edit "
                        "your own review."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProductReviewSerializer(
            review,
            data=request.data,
            partial=True,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # DELETE
    # =========================================================

    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):

        review = self.get_object()

        # -----------------------------------------------------
        # ADMIN
        # -----------------------------------------------------

        if self._is_admin(request.user):

            review.delete()

            return Response(
                status=status.HTTP_204_NO_CONTENT
            )

        # -----------------------------------------------------
        # CUSTOMER OWNERSHIP
        # -----------------------------------------------------

        if review.user_id != request.user.id:

            return Response(
                {
                    "detail": (
                        "You can only delete "
                        "your own review."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        review.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

    # =========================================================
    # ADMIN CHECK
    # =========================================================

    @staticmethod
    def _is_admin(user):

        return (
            user.is_authenticated
            and getattr(user, "role", None)
            in [
                "ADMIN",
                "SUPER_ADMIN",
            ]
        )