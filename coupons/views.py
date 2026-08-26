from rest_framework import (
    viewsets,
    permissions,
    status,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Coupon
from .serializers import (
    CouponSerializer,
    ApplyCouponSerializer,
)


class CouponViewSet(viewsets.ModelViewSet):

    queryset = Coupon.objects.select_related(
        "dark_store"
    )

    serializer_class = CouponSerializer

    def get_permissions(self):

        if self.action in [
            "list",
            "retrieve",
            "validate_coupon",
        ]:
            return [
                permissions.IsAuthenticated()
            ]

        return [
            permissions.IsAdminUser()
        ]

    def get_queryset(self):

        user = self.request.user

        if (
            user.is_staff
            or getattr(user, "role", "") in [
                "ADMIN",
                "MANAGER",
            ]
        ):
            return Coupon.objects.all()

        from django.utils import timezone

        now = timezone.now()

        return Coupon.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="validate",
    )
    def validate_coupon(self, request):

        serializer = ApplyCouponSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        coupon = serializer.validated_data["coupon"]
        order_amount = serializer.validated_data[
            "order_amount"
        ]

        discount_amount = coupon.calculate_discount(
            order_amount
        )

        final_amount = (
            order_amount - discount_amount
        )

        return Response(
            {
                "valid": True,
                "code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": coupon.discount_value,
                "discount_amount": discount_amount,
                "original_amount": order_amount,
                "final_amount": final_amount,
                "dark_store": (
                    coupon.dark_store_id
                    if coupon.dark_store
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )