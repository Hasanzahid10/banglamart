from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import (
    JSONParser,
    MultiPartParser,
    FormParser,
)
from rest_framework.response import Response

from .models import UserProfile, Address
from .serializers import (
    UserProfileSerializer,
    AddressSerializer,
)

class ProfileViewSet(viewsets.ViewSet):

    permission_classes = [
        permissions.IsAuthenticated
    ]

    parser_classes = (
        JSONParser,
        MultiPartParser,
        FormParser,
    )

    def _get_or_create_profile(self, user):
        profile, _ = UserProfile.objects.get_or_create(
            user=user
        )
        return profile

    def list(self, request):
        profile = self._get_or_create_profile(
            request.user
        )

        serializer = UserProfileSerializer(
            profile,
            context={"request": request},
        )

        return Response(serializer.data)

    def create(self, request):
        if UserProfile.objects.filter(
            user=request.user
        ).exists():
            return Response(
                {
                    "detail": "Profile already exists for this user."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = UserProfile.objects.create(
            user=request.user
        )

        serializer = UserProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, pk=None):
        profile = self._get_or_create_profile(
            request.user
        )

        serializer = UserProfileSerializer(
            profile,
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, pk=None):
        profile = self._get_or_create_profile(
            request.user
        )

        serializer = UserProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        try:
            profile = UserProfile.objects.get(
                user=request.user
            )
        except UserProfile.DoesNotExist:
            return Response(
                {
                    "detail": "Profile does not exist."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if profile.avatar:
            profile.avatar.delete(save=False)

        profile.delete()

        return Response(
            {
                "message": (
                    "User profile has been "
                    "deleted successfully."
                )
            },
            status=status.HTTP_200_OK,
        )




class AddressViewSet(viewsets.ModelViewSet):
    """
    Delivery address CRUD for the authenticated user.

    Users can ONLY access their own addresses.
    """

    serializer_class = AddressSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    parser_classes = (
        JSONParser,
        MultiPartParser,
        FormParser,
    )

    def get_queryset(self):
        return Address.objects.filter(
            user=self.request.user
        ).order_by(
            "-is_default",
            "-created_at",
        )

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(
            user=self.request.user
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="set-default",
    )
    def set_default(self, request, pk=None):

        address = self.get_object()

        Address.objects.filter(
            user=request.user,
            is_default=True,
        ).exclude(
            pk=address.pk
        ).update(
            is_default=False
        )

        address.is_default = True
        address.save()

        serializer = self.get_serializer(
            address
        )

        return Response(
            {
                "message": (
                    "Address set as default successfully."
                ),
                "address": serializer.data,
            },
            status=status.HTTP_200_OK,
        )