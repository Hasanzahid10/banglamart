import uuid
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from cart.models import Cart
from logistics.models import DeliveryOrder
from products.models import ProductInventory

from .models import Order, OrderItem


# ============================================================
# ORDER ITEM SERIALIZER
# ============================================================

class OrderItemSerializer(serializers.ModelSerializer):

    product_id = serializers.ReadOnlyField(
        source="inventory.product.id"
    )

    class Meta:
        model = OrderItem

        fields = (
            "id",
            "product_id",
            "product_name_en",
            "product_name_bn",
            "sku",
            "unit",
            "unit_price",
            "quantity",
            "subtotal",
        )

        read_only_fields = fields


# ============================================================
# CHECKOUT SERIALIZER
# ============================================================

class CheckoutSerializer(serializers.Serializer):

    # --------------------------------------------------------
    # DELIVERY ORDER
    # --------------------------------------------------------

    delivery_order_id = serializers.UUIDField(
        required=True,
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(self, attrs):

        user = self.context["request"].user

        # ====================================================
        # 1. GET CART
        # ====================================================

        try:

            cart = (
                Cart.objects
                .select_related(
                    "dark_store",
                )
                .prefetch_related(
                    "items__inventory__product",
                )
                .get(
                    user=user,
                )
            )

        except Cart.DoesNotExist:

            raise serializers.ValidationError({
                "cart": (
                    "No active cart found."
                )
            })

        # ----------------------------------------------------
        # Cart must contain products
        # ----------------------------------------------------

        cart_items = list(
            cart.items.all()
        )

        if not cart_items:

            raise serializers.ValidationError({
                "cart": (
                    "Your cart is empty."
                )
            })

        attrs["cart"] = cart

        # ====================================================
        # 2. GET DELIVERY ORDER
        # ====================================================

        delivery_order_id = attrs[
            "delivery_order_id"
        ]

        try:

            delivery_order = (
                DeliveryOrder.objects
                .select_related(
                    "dark_store",
                    "dark_store__service_area",
                    "delivery_slot",
                )
                .get(
                    id=delivery_order_id,
                    user=user,
                )
            )

        except DeliveryOrder.DoesNotExist:

            raise serializers.ValidationError({
                "delivery_order_id": (
                    "Invalid delivery order."
                )
            })

        # ====================================================
        # 3. DELIVERY ORDER MUST STILL BE AVAILABLE
        # ====================================================

        if delivery_order.status not in [
            DeliveryOrder.Status.PENDING,
        ]:

            raise serializers.ValidationError({
                "delivery_order": (
                    "This delivery order is no longer "
                    "available for checkout."
                )
            })

        # ====================================================
        # 4. MAKE SURE DELIVERY ORDER IS NOT ALREADY USED
        # ====================================================

        if hasattr(delivery_order, "order"):

            raise serializers.ValidationError({
                "delivery_order": (
                    "This delivery order is already "
                    "attached to another order."
                )
            })

        attrs["delivery_order"] = (
            delivery_order
        )

        # ====================================================
        # 5. DARK STORE IS DETERMINED BY DELIVERY ROUTING
        # ====================================================

        dark_store = delivery_order.dark_store

        if not dark_store:

            raise serializers.ValidationError({
                "dark_store": (
                    "Unable to determine the serving "
                    "dark store."
                )
            })

        if not dark_store.is_active:

            raise serializers.ValidationError({
                "dark_store": (
                    "The selected dark store is "
                    "currently unavailable."
                )
            })

        # ----------------------------------------------------
        # ServiceArea must also be active
        # ----------------------------------------------------

        if not dark_store.service_area.is_active:

            raise serializers.ValidationError({
                "service_area": (
                    "The service area is currently "
                    "inactive."
                )
            })

        attrs["dark_store"] = dark_store

        # ====================================================
        # 6. ADDRESS SNAPSHOT
        # ====================================================

        location = delivery_order.location

        if not location:

            raise serializers.ValidationError({
                "delivery_order": (
                    "Delivery location is missing."
                )
            })

        attrs["address_snapshot"] = {

            "recipient_name":
                delivery_order.recipient_name,

            "recipient_phone":
                delivery_order.recipient_phone,

            "street_address":
                delivery_order.street_address,

            "area":
                delivery_order.area,

            "city":
                delivery_order.city,

            "latitude":
                float(location.y),

            "longitude":
                float(location.x),

        }

        # ====================================================
        # 7. DELIVERY FEE
        # ====================================================

        attrs["delivery_fee"] = (
            delivery_order.delivery_fee
        )

        # ====================================================
        # 8. CART / DARK STORE VALIDATION
        # ====================================================

        # ----------------------------------------------------
        # If cart already has a DarkStore, it must match.
        #
        # However, the DeliveryOrder remains the source of
        # truth for the selected serving DarkStore.
        # ----------------------------------------------------

        if (
            cart.dark_store_id
            and
            cart.dark_store_id
            != dark_store.id
        ):

            raise serializers.ValidationError({
                "cart": (
                    "Your cart belongs to a different "
                    "dark store. Please refresh your "
                    "cart for the selected delivery area."
                )
            })

        # ====================================================
        # 9. STOCK VALIDATION
        # ====================================================

        for cart_item in cart_items:

            inventory = cart_item.inventory

            product = inventory.product

            # ------------------------------------------------
            # Product active
            # ------------------------------------------------

            if not product.is_active:

                raise serializers.ValidationError({
                    "stock": (
                        f"Product "
                        f"'{product.name_en}' "
                        "is no longer available."
                    )
                })

            # ------------------------------------------------
            # Inventory must belong to serving DarkStore
            # ------------------------------------------------

            if (
                inventory.dark_store_id
                != dark_store.id
            ):

                raise serializers.ValidationError({
                    "stock": (
                        f"Product "
                        f"'{product.name_en}' "
                        "is not available at the "
                        "serving dark store."
                    )
                })

            # ------------------------------------------------
            # Inventory active
            # ------------------------------------------------

            if not inventory.is_available:

                raise serializers.ValidationError({
                    "stock": (
                        f"Product "
                        f"'{product.name_en}' "
                        "is currently unavailable."
                    )
                })

            # ------------------------------------------------
            # Available stock
            #
            # stock_qty - reserved_qty
            # ------------------------------------------------

            available_qty = (
                inventory.stock_qty
                - inventory.reserved_qty
            )

            if available_qty < cart_item.quantity:

                raise serializers.ValidationError({
                    "stock": (
                        f"Insufficient stock for "
                        f"'{product.name_en}'. "
                        f"Available: "
                        f"{available_qty}"
                    )
                })

        return attrs

    # ========================================================
    # CREATE ORDER
    # ========================================================

    @transaction.atomic
    def create(self, validated_data):

        user = self.context["request"].user

        cart = validated_data[
            "cart"
        ]

        dark_store = validated_data[
            "dark_store"
        ]

        delivery_order = validated_data[
            "delivery_order"
        ]

        address_snapshot = validated_data[
            "address_snapshot"
        ]

        delivery_fee = Decimal(
            validated_data.get(
                "delivery_fee",
                Decimal("0.00"),
            )
        )

        # ====================================================
        # 1. GET CART ITEMS
        # ====================================================

        cart_items = list(
            cart.items.select_related(
                "inventory",
                "inventory__product",
            )
        )

        if not cart_items:

            raise serializers.ValidationError({
                "cart": (
                    "Your cart is empty."
                )
            })

        # ====================================================
        # 2. LOCK INVENTORY ROWS
        # ====================================================

        inventory_ids = [
            item.inventory_id
            for item in cart_items
        ]

        inventories = {
            inventory.id: inventory
            for inventory in (
                ProductInventory.objects
                .select_for_update()
                .select_related(
                    "product",
                    "dark_store",
                )
                .filter(
                    id__in=inventory_ids
                )
            )
        }

        # ====================================================
        # 3. RE-CHECK STOCK AFTER LOCK
        # ====================================================

        for cart_item in cart_items:

            inventory = inventories.get(
                cart_item.inventory_id
            )

            if not inventory:

                raise serializers.ValidationError({
                    "stock": (
                        "Product inventory no longer exists."
                    )
                })

            product = inventory.product

            # ------------------------------------------------
            # Product active
            # ------------------------------------------------

            if not product.is_active:

                raise serializers.ValidationError({
                    "stock": (
                        f"{product.name_en} "
                        "is no longer available."
                    )
                })

            # ------------------------------------------------
            # Correct DarkStore
            # ------------------------------------------------

            if (
                inventory.dark_store_id
                != dark_store.id
            ):

                raise serializers.ValidationError({
                    "stock": (
                        f"{product.name_en} "
                        "is not available at the "
                        "selected dark store."
                    )
                })

            # ------------------------------------------------
            # Inventory available
            # ------------------------------------------------

            if not inventory.is_available:

                raise serializers.ValidationError({
                    "stock": (
                        f"{product.name_en} "
                        "is currently unavailable."
                    )
                })

            # ------------------------------------------------
            # Available stock
            # ------------------------------------------------

            available_qty = (
                inventory.stock_qty
                - inventory.reserved_qty
            )

            if (
                available_qty
                < cart_item.quantity
            ):

                raise serializers.ValidationError({
                    "stock": (
                        f"Insufficient stock for "
                        f"{product.name_en}. "
                        f"Available: "
                        f"{available_qty}"
                    )
                })

        # ====================================================
        # 4. CALCULATE SUBTOTAL
        # ====================================================

        subtotal = Decimal("0.00")

        for cart_item in cart_items:

            inventory = inventories[
                cart_item.inventory_id
            ]

            # ------------------------------------------------
            # Use current store price
            # ------------------------------------------------

            unit_price = (
                inventory.effective_price
            )

            item_subtotal = (
                unit_price
                * cart_item.quantity
            )

            subtotal += item_subtotal

        # ====================================================
        # 5. DISCOUNT
        # ====================================================

        discount_amount = Decimal(
            "0.00"
        )

        # ====================================================
        # 6. TOTAL
        # ====================================================

        total_amount = (
            subtotal
            + delivery_fee
            - discount_amount
        )

        # ====================================================
        # 7. ORDER NUMBER
        # ====================================================

        order_number = (
            f"ORD-"
            f"{uuid.uuid4().hex[:12].upper()}"
        )

        # ====================================================
        # 8. CREATE ORDER
        # ====================================================

        order = Order.objects.create(

            order_number=order_number,

            user=user,

            dark_store=dark_store,

            delivery_order=delivery_order,

            subtotal=subtotal,

            delivery_fee=delivery_fee,

            discount_amount=discount_amount,

            total_amount=total_amount,

            delivery_address_snapshot=(
                address_snapshot
            ),

            note=validated_data.get(
                "note",
                "",
            ),

            status=(
                Order.OrderStatus
                .PENDING_PAYMENT
            ),

            payment_status=(
                Order.PaymentStatus
                .UNPAID
            ),
        )

        # ====================================================
        # 9. CREATE ORDER ITEMS
        # ====================================================

        for cart_item in cart_items:

            inventory = inventories[
                cart_item.inventory_id
            ]

            product = inventory.product

            # ------------------------------------------------
            # IMPORTANT:
            # Use current inventory effective price.
            # ------------------------------------------------

            unit_price = (
                inventory.effective_price
            )

            item_subtotal = (
                unit_price
                * cart_item.quantity
            )

            OrderItem.objects.create(

                order=order,

                inventory=inventory,

                # Product snapshot
                product_name_en=(
                    product.name_en
                ),

                product_name_bn=(
                    product.name_bn
                ),

                sku=product.sku,

                unit=product.unit,

                # Price snapshot
                unit_price=unit_price,

                quantity=(
                    cart_item.quantity
                ),

                subtotal=item_subtotal,
            )

            # ------------------------------------------------
            # RESERVE STOCK
            #
            # DO NOT decrease stock_qty here.
            # ------------------------------------------------

            inventory.reserved_qty += (
                cart_item.quantity
            )

            inventory.save(
                update_fields=[
                    "reserved_qty",
                    "updated_at",
                ]
            )

        # ====================================================
        # 10. ATTACH DELIVERY ORDER
        # ====================================================

        delivery_order.save(
            update_fields=[
                "updated_at",
            ]
        )

        # ====================================================
        # 11. CLEAR CART
        # ====================================================

        cart.items.all().delete()

        return order


# ============================================================
# ORDER SERIALIZER
# ============================================================

class OrderSerializer(
    serializers.ModelSerializer
):

    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    dark_store_name = serializers.CharField(
        source="dark_store.name",
        read_only=True,
        default="",
    )

    service_area_name = serializers.CharField(
        source="dark_store.service_area.name",
        read_only=True,
        default="",
    )

    service_area_city = serializers.CharField(
        source="dark_store.service_area.city",
        read_only=True,
        default="",
    )

    delivery_tracking_number = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    payment_gateway = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()

    def get_delivery_tracking_number(self, obj):
        if obj.delivery_order:
            return obj.delivery_order.tracking_number
        return f"TRK-{obj.order_number}"

    def get_user_name(self, obj):
        if isinstance(obj.delivery_address_snapshot, dict) and obj.delivery_address_snapshot.get('recipient_name'):
            return obj.delivery_address_snapshot.get('recipient_name')
        if obj.user:
            full_name = f"{getattr(obj.user, 'first_name', '')} {getattr(obj.user, 'last_name', '')}".strip()
            if full_name:
                return full_name
            return getattr(obj.user, 'email', '') or getattr(obj.user, 'phone_number', '') or "Customer"
        return "Customer"

    def get_user_phone(self, obj):
        if isinstance(obj.delivery_address_snapshot, dict) and obj.delivery_address_snapshot.get('recipient_phone'):
            return obj.delivery_address_snapshot.get('recipient_phone')
        if obj.user:
            return getattr(obj.user, 'phone_number', '') or ""
        return ""

    def get_user_email(self, obj):
        if obj.user:
            return getattr(obj.user, 'email', '') or ""
        return ""

    def get_payment_gateway(self, obj):
        return "Cash on Delivery"

    def get_delivery_address(self, obj):
        if isinstance(obj.delivery_address_snapshot, dict):
            return {
                "recipient_name": obj.delivery_address_snapshot.get("recipient_name", self.get_user_name(obj)),
                "recipient_phone": obj.delivery_address_snapshot.get("recipient_phone", self.get_user_phone(obj)),
                "street_address": obj.delivery_address_snapshot.get("street_address", "House 24, Road 5"),
                "area": obj.delivery_address_snapshot.get("area", "Dhaka"),
                "city": obj.delivery_address_snapshot.get("city", "Dhaka"),
            }
        return {
            "recipient_name": self.get_user_name(obj),
            "recipient_phone": self.get_user_phone(obj),
            "street_address": "House 24, Road 5",
            "area": "Dhaka",
            "city": "Dhaka",
        }

    class Meta:

        model = Order

        fields = (
            "id",
            "order_number",

            "user_name",
            "user_phone",
            "user_email",
            "payment_gateway",
            "delivery_address",

            "service_area_name",
            "service_area_city",

            "dark_store_name",

            "delivery_tracking_number",

            "status",
            "payment_status",

            "subtotal",
            "delivery_fee",
            "discount_amount",
            "total_amount",

            "delivery_address_snapshot",

            "note",

            "items",

            "created_at",
            "updated_at",
        )

        read_only_fields = fields