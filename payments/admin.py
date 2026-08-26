from django.contrib import admin

from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "transaction_id",
        "order",
        "user",
        "gateway",
        "amount",
        "currency",
        "status",
        "gateway_transaction_id",
        "created_at",
        "paid_at",
    )

    list_filter = (
        "gateway",
        "status",
        "currency",
        "created_at",
    )

    search_fields = (
        "transaction_id",
        "gateway_transaction_id",
        "order__order_number",
        "user__phone_number",
        "user__email",
    )

    readonly_fields = (
        "id",
        "transaction_id",
        "created_at",
        "updated_at",
        "paid_at",
        "failed_at",
        "refunded_at",
    )

    fieldsets = (
        (
            "Transaction",
            {
                "fields": (
                    "id",
                    "transaction_id",
                    "gateway_transaction_id",
                    "order",
                    "user",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "gateway",
                    "status",
                    "amount",
                    "currency",
                )
            },
        ),
        (
            "Gateway Response",
            {
                "fields": (
                    "gateway_response",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "paid_at",
                    "failed_at",
                    "refunded_at",
                )
            },
        ),
    )

    ordering = ("-created_at",)

    list_per_page = 50
