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
        permissions.AllowAny
    ]

    serializer_class = UserProfileSerializer

    parser_classes = (
        JSONParser,
        MultiPartParser,
        FormParser,
    )

    def _get_target_user(self, request):
        if request.user and request.user.is_authenticated:
            return request.user

        from django.contrib.auth import get_user_model
        User = get_user_model()

        data = getattr(request, 'data', {}) or {}
        params = getattr(request, 'query_params', {}) or {}

        email = data.get("email") or params.get("email")
        phone = data.get("phone_number") or data.get("phone") or params.get("phone_number") or params.get("phone")

        if email:
            u = User.objects.filter(email__iexact=str(email).strip()).first()
            if u:
                return u
        if phone:
            u = User.objects.filter(phone_number=str(phone).strip()).first()
            if u:
                return u

        return User.objects.filter(is_active=True).order_by("-id").first()

    def _get_or_create_profile(self, user):
        if not user:
            return None
        profile, _ = UserProfile.objects.get_or_create(
            user=user
        )
        return profile

    def list(self, request):
        user = self._get_target_user(request)
        if not user:
            return Response({"detail": "No user profile found."}, status=status.HTTP_404_NOT_FOUND)
        profile = self._get_or_create_profile(user)

        serializer = UserProfileSerializer(
            profile,
            context={"request": request},
        )

        return Response(serializer.data)

    def create(self, request):
        user = self._get_target_user(request)
        if not user:
            return Response({"detail": "No user context found."}, status=status.HTTP_400_BAD_REQUEST)

        if UserProfile.objects.filter(
            user=user
        ).exists():
            return Response(
                {
                    "detail": "Profile already exists for this user."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = UserProfile.objects.create(
            user=user
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
        user = self._get_target_user(request)
        if not user:
            return Response({"detail": "No user context found."}, status=status.HTTP_404_NOT_FOUND)
        profile = self._get_or_create_profile(user)

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

    def partial_update(self, request, pk=None):
        user = self._get_target_user(request)
        if not user:
            return Response({"detail": "No user context found."}, status=status.HTTP_404_NOT_FOUND)
        profile = self._get_or_create_profile(user)

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
    Delivery address CRUD for the user.
    """

    serializer_class = AddressSerializer

    permission_classes = [
        permissions.AllowAny
    ]

    parser_classes = (
        JSONParser,
        MultiPartParser,
        FormParser,
    )

    def _get_target_user(self, request):
        if request.user and request.user.is_authenticated:
            return request.user
        return None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Address.objects.none()

        user = self._get_target_user(self.request)
        if not user:
            return Address.objects.none()

        return Address.objects.filter(
            user=user
        ).order_by(
            "-is_default",
            "-created_at",
        )

    def perform_create(self, serializer):
        user = self._get_target_user(self.request)
        serializer.save(
            user=user
        )

    def perform_update(self, serializer):
        user = self._get_target_user(self.request)
        serializer.save(
            user=user
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


from django.contrib.auth import get_user_model
User = get_user_model()


import uuid
from cart.models import GuestCart


class AdminCustomerViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        users = User.objects.all().order_by('-date_joined') if hasattr(User, 'date_joined') else User.objects.all()
        data = []
        for user in users:
            # Addresses
            addresses = Address.objects.filter(user=user)
            addresses_data = AddressSerializer(addresses, many=True).data

            # Guest/User Cart
            guest_carts = GuestCart.objects.filter(user=user, status='ACTIVE').order_by('-updated_at')
            if not guest_carts.exists():
                guest_carts = GuestCart.objects.filter(user=user).order_by('-updated_at')
            if not guest_carts.exists() and getattr(user, 'email', None):
                guest_carts = GuestCart.objects.filter(guest_id=user.email).order_by('-updated_at')
            if not guest_carts.exists() and getattr(user, 'phone_number', None):
                guest_carts = GuestCart.objects.filter(guest_id=user.phone_number).order_by('-updated_at')

            # Fallback for unassigned active guest carts with items
            if not guest_carts.exists():
                unassigned_carts = GuestCart.objects.filter(user__isnull=True, status='ACTIVE').exclude(items__isnull=True).order_by('-updated_at')
                if unassigned_carts.exists():
                    latest_unassigned = unassigned_carts.first()
                    latest_unassigned.user = user
                    latest_unassigned.save()
                    guest_carts = GuestCart.objects.filter(pk=latest_unassigned.pk)

            cart_items = []
            cart_total = 0.0

            if hasattr(user, 'cart') and user.cart.items.exists():
                cart_total = float(user.cart.total_price)
                cart_items = [
                    {
                        'product_name': item.product.name_en if item.product else "Product",
                        'quantity': item.quantity,
                        'unit_price': float(item.unit_price),
                        'subtotal': float(item.subtotal),
                    }
                    for item in user.cart.items.all()
                ]
            elif guest_carts.exists():
                latest_cart = guest_carts.first()
                cart_total = latest_cart.total_price
                cart_items = [
                    {
                        'product_name': item.product_name,
                        'quantity': item.quantity,
                        'unit_price': float(item.unit_price),
                        'subtotal': float(item.subtotal),
                    }
                    for item in latest_cart.items.all()
                ]

            user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"metrobazar.user.{user.id}"))

            role = getattr(user, 'role', None)
            if getattr(user, 'is_superuser', False) or role == 'ADMIN':
                user_role = 'ADMIN'
            elif getattr(user, 'is_staff', False) or role in ['STAFF', 'WAREHOUSE_STAFF']:
                user_role = 'STAFF'
            else:
                user_role = role or 'CUSTOMER'

            data.append({
                'id': user_uuid,
                'raw_id': user.id,
                'email': getattr(user, 'email', '') or '',
                'phone_number': getattr(user, 'phone_number', '') or '',
                'first_name': getattr(user, 'first_name', '') or '',
                'last_name': getattr(user, 'last_name', '') or '',
                'role': user_role,
                'is_phone_verified': getattr(user, 'is_phone_verified', False),
                'is_email_verified': getattr(user, 'is_email_verified', False),
                'date_joined': user.date_joined.isoformat() if hasattr(user, 'date_joined') and user.date_joined else '',
                'addresses': addresses_data,
                'cart': {
                    'total_items': len(cart_items),
                    'total_price': cart_total,
                    'items': cart_items
                }
            })

        return Response({
            'total_customers': len(data),
            'customers': data
        }, status=status.HTTP_200_OK)