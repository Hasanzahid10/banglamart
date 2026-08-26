from django.db import transaction
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    DarkStoreManager,
    DeliveryOrder,
)

from .serializers import (
    CreateDeliveryOrderSerializer,
    DeliveryOrderSerializer,
)


class LogisticsViewSet(viewsets.ModelViewSet):

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    queryset = (
        DeliveryOrder.objects
        .select_related(
            "user",
            "dark_store",
            "dark_store__service_area",
            "rider",
            "saved_address",
            "delivery_zone",
            "delivery_slot",
        )
        .order_by("-created_at")
    )

    # =========================================================
    # SERIALIZER
    # =========================================================

    def get_serializer_class(self):

        if self.action == "create":
            return CreateDeliveryOrderSerializer

        return DeliveryOrderSerializer

    # =========================================================
    # HELPER:
    # CHECK DARK STORE MANAGER
    # =========================================================

    def is_store_manager(
        self,
        user,
        dark_store,
    ):
        return DarkStoreManager.objects.filter(
            user=user,
            dark_store=dark_store,
            is_active=True,
            dark_store__is_active=True,
            dark_store__service_area__is_active=True,
        ).exists()

    # =========================================================
    # QUERYSET
    # =========================================================

    def get_queryset(self):

        user = self.request.user

        # -----------------------------------------------------
        # GLOBAL ADMIN
        # -----------------------------------------------------

        if user.role == "ADMIN":
            return self.queryset

        # -----------------------------------------------------
        # RIDER
        # -----------------------------------------------------

        if user.role == "RIDER":
            return self.queryset.filter(
                rider=user,
            )

        # -----------------------------------------------------
        # DARK STORE MANAGER
        # -----------------------------------------------------

        managed_store_ids = (
            DarkStoreManager.objects
            .filter(
                user=user,
                is_active=True,
                dark_store__is_active=True,
                dark_store__service_area__is_active=True,
            )
            .values_list(
                "dark_store_id",
                flat=True,
            )
        )

        # If user manages stores, show only those stores.
        if managed_store_ids:

            return self.queryset.filter(
                dark_store_id__in=managed_store_ids,
            )

        # -----------------------------------------------------
        # CUSTOMER
        # -----------------------------------------------------

        return self.queryset.filter(
            user=user,
        )

    # =========================================================
    # CREATE
    # =========================================================

    def create(
        self,
        request,
        *args,
        **kwargs,
    ):

        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True,
        )

        delivery_order = serializer.save()

        response_serializer = DeliveryOrderSerializer(
            delivery_order,
            context={
                "request": request,
            },
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # =========================================================
    # UPDATE STATUS
    # =========================================================

    @action(
        detail=True,
        methods=["patch"],
        url_path="update-status",
    )
    def update_status(
        self,
        request,
        pk=None,
    ):

        delivery = self.get_object()

        user = request.user

        new_status = request.data.get(
            "status"
        )

        # -----------------------------------------------------
        # REQUIRED STATUS
        # -----------------------------------------------------

        if not new_status:

            return Response(
                {
                    "status": (
                        "This field is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # VALID STATUS
        # -----------------------------------------------------

        valid_statuses = {
            choice[0]
            for choice in DeliveryOrder.Status.choices
        }

        if new_status not in valid_statuses:

            return Response(
                {
                    "status": (
                        "Invalid delivery status."
                    ),
                    "allowed_statuses": list(
                        valid_statuses
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # STATUS TRANSITIONS
        # -----------------------------------------------------

        allowed_transitions = {

            DeliveryOrder.Status.PENDING: [
                DeliveryOrder.Status.ASSIGNED,
                DeliveryOrder.Status.CANCELLED,
            ],

            DeliveryOrder.Status.ASSIGNED: [
                DeliveryOrder.Status.PACKING,
                DeliveryOrder.Status.CANCELLED,
            ],

            DeliveryOrder.Status.PACKING: [
                DeliveryOrder.Status.OUT_FOR_DELIVERY,
                DeliveryOrder.Status.CANCELLED,
            ],

            DeliveryOrder.Status.OUT_FOR_DELIVERY: [
                DeliveryOrder.Status.DELIVERED,
                DeliveryOrder.Status.FAILED,
            ],

            DeliveryOrder.Status.DELIVERED: [],

            DeliveryOrder.Status.FAILED: [
                DeliveryOrder.Status.OUT_FOR_DELIVERY,
                DeliveryOrder.Status.CANCELLED,
            ],

            DeliveryOrder.Status.CANCELLED: [],
        }

        current_status = delivery.status

        if new_status not in allowed_transitions.get(
            current_status,
            [],
        ):

            return Response(
                {
                    "error": (
                        f"Cannot change status from "
                        f"{current_status} to "
                        f"{new_status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =====================================================
        # GLOBAL ADMIN
        # =====================================================

        if user.role == "ADMIN":

            pass

        # =====================================================
        # DARK STORE MANAGER
        # =====================================================

        elif self.is_store_manager(
            user,
            delivery.dark_store,
        ):

            allowed_manager_statuses = [
                DeliveryOrder.Status.ASSIGNED,
                DeliveryOrder.Status.PACKING,
                DeliveryOrder.Status.CANCELLED,
            ]

            if new_status not in allowed_manager_statuses:

                return Response(
                    {
                        "error": (
                            "Dark store managers can only "
                            "control store fulfillment "
                            "statuses."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # =====================================================
        # RIDER
        # =====================================================

        elif user.role == "RIDER":

            # Extra safety check.
            if delivery.rider_id != user.id:

                return Response(
                    {
                        "error": (
                            "This delivery is not "
                            "assigned to you."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            allowed_rider_statuses = [
                DeliveryOrder.Status.OUT_FOR_DELIVERY,
                DeliveryOrder.Status.DELIVERED,
                DeliveryOrder.Status.FAILED,
            ]

            if new_status not in allowed_rider_statuses:

                return Response(
                    {
                        "error": (
                            "Riders cannot change the "
                            "delivery to this status."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # =====================================================
        # CUSTOMER / OTHER USER
        # =====================================================

        else:

            return Response(
                {
                    "error": (
                        "You do not have permission "
                        "to update delivery status."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # =====================================================
        # UPDATE TIMESTAMPS
        # =====================================================

        now = timezone.now()

        delivery.status = new_status

        if new_status == DeliveryOrder.Status.ASSIGNED:

            delivery.assigned_at = now

        elif new_status == DeliveryOrder.Status.OUT_FOR_DELIVERY:

            delivery.picked_up_at = now

        elif new_status == DeliveryOrder.Status.DELIVERED:

            delivery.delivered_at = now

        delivery.save(
            update_fields=[
                "status",
                "assigned_at",
                "picked_up_at",
                "delivered_at",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": (
                    f"Delivery status updated to "
                    f"{new_status}."
                ),
                "tracking_number": (
                    delivery.tracking_number
                ),
                "status": delivery.status,
            },
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # CANCEL DELIVERY
    # =========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(
        self,
        request,
        pk=None,
    ):

        delivery = self.get_object()

        user = request.user

        # =====================================================
        # PERMISSION
        # =====================================================

        is_admin = (
            user.role == "ADMIN"
        )

        is_customer = (
            delivery.user_id == user.id
        )

        is_store_manager = (
            self.is_store_manager(
                user,
                delivery.dark_store,
            )
        )

        if not (
            is_admin
            or is_customer
            or is_store_manager
        ):

            return Response(
                {
                    "detail": (
                        "You cannot cancel "
                        "this delivery."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # =====================================================
        # CANCELLABLE STATUS
        # =====================================================

        cancellable_statuses = [
            DeliveryOrder.Status.PENDING,
            DeliveryOrder.Status.ASSIGNED,
            DeliveryOrder.Status.PACKING,
        ]

        if delivery.status not in cancellable_statuses:

            return Response(
                {
                    "detail": (
                        "This delivery can no longer "
                        "be cancelled."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =====================================================
        # CANCEL
        # =====================================================

        delivery.status = (
            DeliveryOrder.Status.CANCELLED
        )

        delivery.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": (
                    "Delivery cancelled successfully."
                ),
                "tracking_number": (
                    delivery.tracking_number
                ),
                "status": delivery.status,
            },
            status=status.HTTP_200_OK,
        )

    # =========================================================
    # ASSIGN RIDER
    # =========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="assign-rider",
    )
    def assign_rider(
        self,
        request,
        pk=None,
    ):

        delivery = self.get_object()

        user = request.user

        # -----------------------------------------------------
        # ONLY ADMIN / STORE MANAGER
        # -----------------------------------------------------

        if user.role != "ADMIN":

            if not self.is_store_manager(
                user,
                delivery.dark_store,
            ):

                return Response(
                    {
                        "detail": (
                            "You do not have permission "
                            "to assign riders for this "
                            "dark store."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        rider_id = request.data.get(
            "rider_id"
        )

        if not rider_id:

            return Response(
                {
                    "rider_id": (
                        "This field is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:

            rider = User.objects.get(
                id=rider_id,
                role="RIDER",
            )

        except User.DoesNotExist:

            return Response(
                {
                    "rider_id": (
                        "Invalid rider."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------------------
        # ASSIGN
        # -----------------------------------------------------

        if delivery.status not in [
            DeliveryOrder.Status.PENDING,
            DeliveryOrder.Status.ASSIGNED,
            DeliveryOrder.Status.PACKING,
        ]:

            return Response(
                {
                    "detail": (
                        "Rider cannot be assigned "
                        "at this stage."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        delivery.rider = rider

        if delivery.status == DeliveryOrder.Status.PENDING:
            delivery.status = (
                DeliveryOrder.Status.ASSIGNED
            )
            delivery.assigned_at = timezone.now()

        delivery.save(
            update_fields=[
                "rider",
                "status",
                "assigned_at",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": (
                    "Rider assigned successfully."
                ),
                "tracking_number": (
                    delivery.tracking_number
                ),
                "rider_id": rider.id,
                "rider_name": rider.get_full_name(),
                "status": delivery.status,
            },
            status=status.HTTP_200_OK,
        )