from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from logistics.models import DarkStore
from orders.models import Order

from .models import (
    GlobalPlatformConfig,
    SystemFeatureFlag,
)
from .serializers import (
    GlobalPlatformConfigSerializer,
    SystemFeatureFlagSerializer,
    UserRoleUpdateSerializer,
)

User = get_user_model()


# ============================================================
# PERMISSION
# ============================================================

class IsSuperAdmin(permissions.BasePermission):
    """
    Only Django SuperAdmins can access this application.

    This permission intentionally does NOT allow normal ADMIN users.
    """

    message = "Only SuperAdmin users can access this resource."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_superuser
        )


# ============================================================
# SUPER ADMIN
# ============================================================

class SuperAdminViewSet(viewsets.ViewSet):
    """
    Global platform management.

    SuperAdmin responsibilities:

        - Global platform configuration
        - Feature flags
        - User role management
        - Global platform statistics

    Regional operational management belongs to admin_panel.
    """

    permission_classes = [IsSuperAdmin]

    serializer_class = GlobalPlatformConfigSerializer

    # ========================================================
    # PLATFORM CONFIG
    # ========================================================

    @action(
        detail=False,
        methods=["get", "put", "patch"],
        url_path="platform-config",
    )
    def platform_config(self, request):
        """
        GET/PATCH/PUT platform-wide configuration.
        """

        config, _ = GlobalPlatformConfig.objects.get_or_create(
            pk="00000000-0000-0000-0000-000000000001"
        )

        if request.method in ["PUT", "PATCH"]:

            serializer = GlobalPlatformConfigSerializer(
                config,
                data=request.data,
                partial=True,
            )

            serializer.is_valid(
                raise_exception=True
            )

            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        serializer = GlobalPlatformConfigSerializer(
            config
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # USER ROLE MANAGEMENT
    # ========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="update-user-role",
    )
    def update_user_role(self, request):
        """
        Change a user's application role.

        SuperAdmin only.

        IMPORTANT:
        A SuperAdmin cannot modify their own
        superuser status through this endpoint.
        """

        serializer = UserRoleUpdateSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        user_id = serializer.validated_data[
            "user_id"
        ]

        role = serializer.validated_data[
            "role"
        ]

        target_user = User.objects.get(
            id=user_id
        )

        # ----------------------------------------------------
        # Prevent self-demotion
        # ----------------------------------------------------

        if target_user.id == request.user.id:

            if (
                "is_superuser"
                in serializer.validated_data
                and not serializer.validated_data[
                    "is_superuser"
                ]
            ):
                return Response(
                    {
                        "detail": (
                            "You cannot remove your own "
                            "SuperAdmin privileges."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ----------------------------------------------------
        # Prevent changing another superuser accidentally
        # ----------------------------------------------------

        if (
            target_user.is_superuser
            and target_user.id != request.user.id
        ):

            requested_superuser = serializer.validated_data.get(
                "is_superuser"
            )

            if requested_superuser is False:

                return Response(
                    {
                        "detail": (
                            "Another SuperAdmin cannot be "
                            "demoted through this endpoint."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # ----------------------------------------------------
        # Update atomically
        # ----------------------------------------------------

        with transaction.atomic():

            target_user.role = role

            if "is_staff" in serializer.validated_data:
                target_user.is_staff = (
                    serializer.validated_data[
                        "is_staff"
                    ]
                )

            if "is_superuser" in serializer.validated_data:

                # Only allow setting superuser explicitly.
                target_user.is_superuser = (
                    serializer.validated_data[
                        "is_superuser"
                    ]
                )

            target_user.save(
                update_fields=[
                    "role",
                    "is_staff",
                    "is_superuser",
                ]
            )

        return Response(
            {
                "message": (
                    f"User '{target_user.phone_number or target_user.email}' "
                    f"updated successfully."
                ),
                "user_id": target_user.id,
                "role": target_user.role,
                "is_staff": target_user.is_staff,
                "is_superuser": target_user.is_superuser,
            },
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # EXECUTIVE SUMMARY
    # ========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path="executive-summary",
    )
    def executive_summary(self, request):
        """
        Global platform-level statistics.

        Unlike admin_panel, this endpoint is NOT region scoped.
        """

        return Response(
            {
                "users": {
                    "total": User.objects.count(),

                    "customers": User.objects.filter(
                        role="CUSTOMER"
                    ).count(),

                    "riders": User.objects.filter(
                        role="RIDER"
                    ).count(),

                    "admins": User.objects.filter(
                        role="ADMIN"
                    ).count(),

                    "super_admins": User.objects.filter(
                        is_superuser=True
                    ).count(),
                },

                "dark_stores": {
                    "total": DarkStore.objects.count(),

                    "active": DarkStore.objects.filter(
                        is_active=True
                    ).count(),

                    "inactive": DarkStore.objects.filter(
                        is_active=False
                    ).count(),
                },

                "orders": {
                    "total": Order.objects.count(),

                    "completed": Order.objects.filter(
                        status=Order.OrderStatus.DELIVERED
                    ).count(),
                },
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# FEATURE FLAGS
# ============================================================

class FeatureFlagViewSet(
    viewsets.ModelViewSet
):
    """
    Global feature flag management.

    Only SuperAdmin can create, update, delete,
    or view feature flags.
    """

    permission_classes = [IsSuperAdmin]

    queryset = SystemFeatureFlag.objects.all()

    serializer_class = SystemFeatureFlagSerializer

    ordering = [
        "name",
    ]

    search_fields = [
        "name",
        "description",
    ]

    filterset_fields = [
        "is_enabled",
    ]