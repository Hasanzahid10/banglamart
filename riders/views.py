from django.db import transaction
from django.utils import timezone

from rest_framework import (
    viewsets,
    permissions,
    status,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from orders.models import Order
from logistics.models import DeliveryOrder

from .models import (
    RiderProfile,
    DeliveryTask,
)

from .serializers import (
    RiderProfileSerializer,
    UpdateRiderLocationSerializer,
    DeliveryTaskSerializer,
    UpdateTaskStatusSerializer,
)


# =========================================================
# RIDER PERMISSION
# =========================================================

class IsRiderUser(permissions.BasePermission):
    """
    Only authenticated RIDER and ADMIN users can access
    rider-related APIs.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in [
                "RIDER",
                "ADMIN",
            ]
        )


# =========================================================
# RIDER PROFILE VIEWSET
# =========================================================

class RiderViewSet(viewsets.ViewSet):
    """
    Rider profile, duty status and GPS location.

    Rider:
        - View own profile
        - Toggle own duty status
        - Update own location

    Admin:
        - Can access the endpoint as well
    """

    permission_classes = [
        IsRiderUser
    ]

    # -----------------------------------------------------
    # GET /api/riders/profile/
    # -----------------------------------------------------

    def _get_or_create_profile(self, user):
        """
        Get rider profile.

        For a RIDER, create profile if it does not exist.

        For ADMIN, this should normally not be used as an
        operational rider profile, but keeping the helper
        makes the endpoint safe.
        """

        profile, _ = (
            RiderProfile.objects
            .select_related(
                "user",
                "dark_store",
            )
            .get_or_create(
                user=user
            )
        )

        return profile

    @action(
        detail=False,
        methods=["get"],
        url_path="profile",
    )
    def get_profile(self, request):

        profile = self._get_or_create_profile(
            request.user
        )

        serializer = RiderProfileSerializer(
            profile
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # -----------------------------------------------------
    # POST /api/riders/toggle-duty/
    # -----------------------------------------------------

    @action(
        detail=False,
        methods=["post"],
        url_path="toggle-duty",
    )
    def toggle_duty(self, request):

        # Admin should manage riders rather than
        # switching their own rider duty status.
        if request.user.role == "ADMIN":
            return Response(
                {
                    "error": (
                        "Admin cannot use rider duty "
                        "controls."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        profile = self._get_or_create_profile(
            request.user
        )

        # -------------------------------------------------
        # Must have DarkStore assignment
        # -------------------------------------------------

        if (
            not profile.is_on_duty
            and not profile.dark_store
        ):
            return Response(
                {
                    "error": (
                        "You are not assigned to a "
                        "Dark Store. Please contact admin."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Do not allow going OFF duty while delivering
        # -------------------------------------------------

        if profile.is_on_duty:

            active_task_exists = (
                DeliveryTask.objects
                .filter(
                    rider=request.user,
                    status__in=[
                        DeliveryTask.TaskStatus.ASSIGNED,
                        DeliveryTask.TaskStatus.ACCEPTED,
                        DeliveryTask.TaskStatus.PICKED_UP,
                        DeliveryTask.TaskStatus.ARRIVED,
                    ],
                )
                .exists()
            )

            if active_task_exists:
                return Response(
                    {
                        "error": (
                            "You cannot go off duty "
                            "while you have an active "
                            "delivery task."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # -------------------------------------------------
        # Toggle
        # -------------------------------------------------

        profile.is_on_duty = (
            not profile.is_on_duty
        )

        profile.is_available = (
            profile.is_on_duty
        )

        profile.save(
            update_fields=[
                "is_on_duty",
                "is_available",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": (
                    "Rider is now ON DUTY."
                    if profile.is_on_duty
                    else "Rider is now OFF DUTY."
                ),
                "is_on_duty": profile.is_on_duty,
                "is_available": profile.is_available,
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------------------------------
    # POST /api/riders/update-location/
    # -----------------------------------------------------

    @action(
        detail=False,
        methods=["post"],
        url_path="update-location",
    )
    def update_location(
        self,
        request,
    ):

        if request.user.role == "ADMIN":
            return Response(
                {
                    "error": (
                        "Admin cannot update rider "
                        "GPS location."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = (
            UpdateRiderLocationSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        profile = self._get_or_create_profile(
            request.user
        )

        serializer.update_location(
            profile
        )

        return Response(
            {
                "message": (
                    "Location updated successfully."
                ),
                "latitude": float(
                    profile.latitude
                ),
                "longitude": float(
                    profile.longitude
                ),
                "last_location_update": (
                    profile.last_location_update
                ),
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# DELIVERY TASK VIEWSET
# =========================================================

class DeliveryTaskViewSet(
    viewsets.ReadOnlyModelViewSet
):
    """
    Delivery task management.

    RIDER:
        - Can see own tasks.
        - Can update own task status.

    ADMIN:
        - Can see all tasks.
        - Can update/manage tasks.
    """

    permission_classes = [
        IsRiderUser
    ]

    serializer_class = DeliveryTaskSerializer

    # -----------------------------------------------------
    # QUERYSET
    # -----------------------------------------------------

    def get_queryset(self):

        queryset = (
            DeliveryTask.objects
            .select_related(
                "delivery_order",
                "delivery_order__order",
                "delivery_order__dark_store",
                "rider",
                "rider__rider_profile",
                "dark_store",
            )
            .order_by("-created_at")
        )

        user = self.request.user

        # -------------------------------------------------
        # ADMIN
        # -------------------------------------------------

        if user.role == "ADMIN":
            return queryset

        # -------------------------------------------------
        # RIDER
        # -------------------------------------------------

        return queryset.filter(
            rider=user
        )

    # =====================================================
    # UPDATE STATUS
    # =====================================================

    @action(
        detail=True,
        methods=["patch"],
        url_path="update-status",
    )
    @transaction.atomic
    def update_status(
        self,
        request,
        pk=None,
    ):
        """
        Update delivery task status.

        Example:

        {
            "status": "accepted"
        }

        Failed:

        {
            "status": "failed",
            "failure_reason": "Customer unavailable."
        }
        """

        # -------------------------------------------------
        # Lock task
        # -------------------------------------------------

        try:
            task = (
                DeliveryTask.objects
                .select_for_update()
                .select_related(
                    "delivery_order",
                    "delivery_order__order",
                    "delivery_order__dark_store",
                    "rider",
                    "rider__rider_profile",
                    "dark_store",
                )
                .get(id=pk)
            )

        except DeliveryTask.DoesNotExist:

            return Response(
                {
                    "error":
                        "Delivery task not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # -------------------------------------------------
        # Rider can only update own task
        # -------------------------------------------------

        if (
            request.user.role == "RIDER"
            and task.rider_id != request.user.id
        ):
            return Response(
                {
                    "error":
                        "You can only update your "
                        "own delivery tasks."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # -------------------------------------------------
        # Validate input
        # -------------------------------------------------

        serializer = (
            UpdateTaskStatusSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        new_status = (
            serializer.validated_data["status"]
        )

        failure_reason = (
            serializer.validated_data.get(
                "failure_reason",
                "",
            )
        )

        current_status = task.status

        # =================================================
        # STATUS TRANSITIONS
        # =================================================

        allowed_transitions = {

            DeliveryTask.TaskStatus.ASSIGNED: [
                DeliveryTask.TaskStatus.ACCEPTED,
                DeliveryTask.TaskStatus.FAILED,
            ],

            DeliveryTask.TaskStatus.ACCEPTED: [
                DeliveryTask.TaskStatus.PICKED_UP,
                DeliveryTask.TaskStatus.FAILED,
            ],

            DeliveryTask.TaskStatus.PICKED_UP: [
                DeliveryTask.TaskStatus.ARRIVED,
                DeliveryTask.TaskStatus.FAILED,
            ],

            DeliveryTask.TaskStatus.ARRIVED: [
                DeliveryTask.TaskStatus.DELIVERED,
                DeliveryTask.TaskStatus.FAILED,
            ],

            DeliveryTask.TaskStatus.DELIVERED: [],

            DeliveryTask.TaskStatus.FAILED: [],

            DeliveryTask.TaskStatus.CANCELLED: [],
        }

        # -------------------------------------------------
        # Validate transition
        # -------------------------------------------------

        if new_status not in (
            allowed_transitions.get(
                current_status,
                [],
            )
        ):

            return Response(
                {
                    "error": (
                        f"Cannot change task status "
                        f"from '{current_status}' "
                        f"to '{new_status}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =================================================
        # RIDER / DARK STORE VALIDATION
        # =================================================

        rider_profile = getattr(
            task.rider,
            "rider_profile",
            None,
        )

        if rider_profile:

            if (
                rider_profile.dark_store_id
                and task.dark_store_id
                != rider_profile.dark_store_id
            ):
                return Response(
                    {
                        "error": (
                            "Rider is not assigned to "
                            "this DarkStore."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # =================================================
        # TIME
        # =================================================

        now = timezone.now()

        task.status = new_status

        # =================================================
        # ACCEPTED
        # =================================================

        if (
            new_status
            == DeliveryTask.TaskStatus.ACCEPTED
        ):

            task.accepted_at = now

            if rider_profile:

                rider_profile.is_available = False

                rider_profile.save(
                    update_fields=[
                        "is_available",
                        "updated_at",
                    ]
                )

        # =================================================
        # PICKED UP
        # =================================================

        elif (
            new_status
            == DeliveryTask.TaskStatus.PICKED_UP
        ):

            task.picked_up_at = now

            # ---------------------------------------------
            # Order
            # ---------------------------------------------

            order = getattr(
                task.delivery_order,
                "order",
                None,
            )

            if order:

                order.status = (
                    Order.OrderStatus.OUT_FOR_DELIVERY
                )

                order.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            # ---------------------------------------------
            # DeliveryOrder
            # ---------------------------------------------

            delivery_order = (
                task.delivery_order
            )

            if delivery_order:

                delivery_order.status = (
                    DeliveryOrder.Status.OUT_FOR_DELIVERY
                )

                delivery_order.picked_up_at = now

                delivery_order.save(
                    update_fields=[
                        "status",
                        "picked_up_at",
                        "updated_at",
                    ]
                )

        # =================================================
        # ARRIVED
        # =================================================

        elif (
            new_status
            == DeliveryTask.TaskStatus.ARRIVED
        ):

            task.arrived_at = now

        # =================================================
        # DELIVERED
        # =================================================

        elif (
            new_status
            == DeliveryTask.TaskStatus.DELIVERED
        ):

            task.delivered_at = now

            # ---------------------------------------------
            # Order
            # ---------------------------------------------

            order = getattr(
                task.delivery_order,
                "order",
                None,
            )

            if order:

                order.status = (
                    Order.OrderStatus.DELIVERED
                )

                # IMPORTANT:
                # Do NOT automatically mark the order
                # as PAID here.
                #
                # Online payment may already be PAID,
                # while COD requires a separate payment
                # collection/confirmation operation.

                order.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            # ---------------------------------------------
            # DeliveryOrder
            # ---------------------------------------------

            delivery_order = (
                task.delivery_order
            )

            if delivery_order:

                delivery_order.status = (
                    DeliveryOrder.Status.DELIVERED
                )

                delivery_order.delivered_at = now

                delivery_order.save(
                    update_fields=[
                        "status",
                        "delivered_at",
                        "updated_at",
                    ]
                )

            # ---------------------------------------------
            # Rider available again
            # ---------------------------------------------

            if rider_profile:

                rider_profile.is_available = True

                rider_profile.save(
                    update_fields=[
                        "is_available",
                        "updated_at",
                    ]
                )

        # =================================================
        # FAILED
        # =================================================

        elif (
            new_status
            == DeliveryTask.TaskStatus.FAILED
        ):

            task.failure_reason = (
                failure_reason
            )

            task.failed_at = now

            # ---------------------------------------------
            # Order
            # ---------------------------------------------

            order = getattr(
                task.delivery_order,
                "order",
                None,
            )

            if order:

                order.status = (
                    Order.OrderStatus.CANCELLED
                )

                order.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            # ---------------------------------------------
            # DeliveryOrder
            # ---------------------------------------------

            delivery_order = (
                task.delivery_order
            )

            if delivery_order:

                delivery_order.status = (
                    DeliveryOrder.Status.FAILED
                )

                delivery_order.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            # ---------------------------------------------
            # Rider available again
            # ---------------------------------------------

            if rider_profile:

                rider_profile.is_available = True

                rider_profile.save(
                    update_fields=[
                        "is_available",
                        "updated_at",
                    ]
                )

        # =================================================
        # SAVE TASK
        # =================================================

        task.save(
            update_fields=[
                "status",
                "failure_reason",
                "accepted_at",
                "picked_up_at",
                "arrived_at",
                "delivered_at",
                "failed_at",
                "updated_at",
            ]
        )

        # =================================================
        # RESPONSE
        # =================================================

        return Response(
            {
                "message": (
                    "Delivery task status updated "
                    f"to '{new_status}'."
                ),
                "task": (
                    DeliveryTaskSerializer(
                        task
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )