from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import User
from catalog.models import Category
from products.models import Product, ProductInventory
from logistics.models import DarkStore
from cart.models import Cart, CartItem
from accounts.models import Address
from orders.models import Order, OrderItem


class OrderAPITests(APITestCase):

    def setUp(self):
        # 1. Create a customer user
        self.customer = User.objects.create_user(
            phone_number="01712345678",
            email="testcustomer@example.com",
            password="securepassword123",
            role="CUSTOMER",
        )

        # 2. Create another customer user (to test queryset isolation)
        self.other_customer = User.objects.create_user(
            phone_number="01787654321",
            email="othercustomer@example.com",
            password="securepassword123",
            role="CUSTOMER",
        )

        # 3. Create an admin user
        self.admin_user = User.objects.create_user(
            phone_number="01711111111",
            email="admin@example.com",
            password="adminpassword123",
            role="ADMIN",
        )

        # 4. Create a Dark Store
        self.dark_store = DarkStore.objects.create(
            name="Uttara Dark Store",
            code="UTTARA-01",
            contact_number="01799999999",
            address="Uttara Sector 3, Dhaka",
            is_active=True,
        )

        # 5. Create a Category
        self.category = Category.objects.create(
            name_en="Beverages",
            slug="beverages",
            is_active=True,
        )

        # 6. Create a Product
        self.product = Product.objects.create(
            category=self.category,
            name_en="Mineral Water 1L",
            slug="mineral-water-1l",
            sku="WAT-1L",
            unit="1 bottle",
            base_price=20.00,
            is_active=True,
        )

        # 7. Create Product Inventory at the Dark Store
        self.inventory = ProductInventory.objects.create(
            dark_store=self.dark_store,
            product=self.product,
            stock_qty=100,
            store_price=18.00,
            is_available=True,
        )

        # 8. Setup customer cart
        self.cart = Cart.objects.create(
            user=self.customer,
            dark_store=self.dark_store,
        )
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            inventory=self.inventory,
            quantity=2,
            unit_price=18.00,
        )

        # 9. Setup saved Address for the customer
        self.address = Address.objects.create(
            user=self.customer,
            title="Home",
            street_address="House 12, Road 4, Sector 3",
            area="Uttara",
            city="Dhaka",
            latitude=23.8729,
            longitude=90.3995,
            is_default=True,
        )

    def test_checkout_success_with_address(self):
        """Test checking out successfully using a saved address ID."""
        self.client.force_authenticate(user=self.customer)
        url = reverse("orders-checkout")
        data = {
            "address_id": self.address.id,
            "note": "Deliver after 5 PM",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("order", response.data)
        self.assertIn("payment_gateway_payload", response.data)

        # Check that the order is created with correct financials
        order = Order.objects.get(id=response.data["order"]["id"])
        self.assertEqual(order.user, self.customer)
        self.assertEqual(order.dark_store, self.dark_store)
        self.assertEqual(order.subtotal, 36.00)  # 2 * 18.00
        self.assertEqual(order.delivery_fee, 30.00)
        self.assertEqual(order.total_amount, 66.00)
        self.assertEqual(order.status, Order.OrderStatus.PENDING_PAYMENT)
        self.assertEqual(order.payment_status, Order.PaymentStatus.UNPAID)

        # Verify stock reservation (100 - 2 = 98)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.stock_qty, 98)

        # Verify cart items are cleared
        self.assertFalse(self.cart.items.exists())

    def test_checkout_empty_cart(self):
        """Test that checkout fails when the cart is empty."""
        self.cart_item.delete()  # Make cart empty
        self.client.force_authenticate(user=self.customer)
        url = reverse("orders-checkout")
        data = {
            "address_id": self.address.id,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cart", response.data)

    def test_checkout_insufficient_stock(self):
        """Test that checkout fails when cart quantity exceeds inventory stock."""
        # Set stock qty lower than cart item quantity
        self.inventory.stock_qty = 1
        self.inventory.save()

        self.client.force_authenticate(user=self.customer)
        url = reverse("orders-checkout")
        data = {
            "address_id": self.address.id,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stock", response.data)

    def test_list_orders_customer_isolation(self):
        """Test that customers can retrieve only their own orders."""
        # Create an order for self.customer
        order = Order.objects.create(
            order_number="ORD-11111111",
            user=self.customer,
            dark_store=self.dark_store,
            subtotal=36.00,
            delivery_fee=30.00,
            total_amount=66.00,
            delivery_address_snapshot={},
        )
        # Create an order for self.other_customer
        other_order = Order.objects.create(
            order_number="ORD-22222222",
            user=self.other_customer,
            dark_store=self.dark_store,
            subtotal=20.00,
            delivery_fee=30.00,
            total_amount=50.00,
            delivery_address_snapshot={},
        )

        # Customer 1 retrieves orders
        self.client.force_authenticate(user=self.customer)
        url = reverse("orders-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only customer 1's order should be returned
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(order.id))

    def test_list_orders_admin_access(self):
        """Test that admin user can retrieve all orders."""
        Order.objects.create(
            order_number="ORD-11111111",
            user=self.customer,
            dark_store=self.dark_store,
            subtotal=36.00,
            delivery_fee=30.00,
            total_amount=66.00,
            delivery_address_snapshot={},
        )
        Order.objects.create(
            order_number="ORD-22222222",
            user=self.other_customer,
            dark_store=self.dark_store,
            subtotal=20.00,
            delivery_fee=30.00,
            total_amount=50.00,
            delivery_address_snapshot={},
        )

        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("orders-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Both orders should be returned for admin
        self.assertEqual(response.data["count"], 2)

    def test_payment_callback_success(self):
        """Test that a successful payment callback updates order and payment status."""
        order = Order.objects.create(
            order_number="ORD-12345678",
            user=self.customer,
            dark_store=self.dark_store,
            subtotal=36.00,
            delivery_fee=30.00,
            total_amount=66.00,
            delivery_address_snapshot={},
            status=Order.OrderStatus.PENDING_PAYMENT,
            payment_status=Order.PaymentStatus.UNPAID,
        )

        url = reverse("orders-payment-callback", kwargs={"pk": str(order.id)})
        data = {
            "payment_status": "paid"
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.status, Order.OrderStatus.CONFIRMED)

    def test_payment_callback_failed(self):
        """Test that a failed payment callback cancels the order."""
        order = Order.objects.create(
            order_number="ORD-12345678",
            user=self.customer,
            dark_store=self.dark_store,
            subtotal=36.00,
            delivery_fee=30.00,
            total_amount=66.00,
            delivery_address_snapshot={},
            status=Order.OrderStatus.PENDING_PAYMENT,
            payment_status=Order.PaymentStatus.UNPAID,
        )

        url = reverse("orders-payment-callback", kwargs={"pk": str(order.id)})
        data = {
            "payment_status": "failed"
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)
        self.assertEqual(order.status, Order.OrderStatus.CANCELLED)

    def test_cancel_order_success(self):
        """Test that customer can cancel their pending payment order."""
        order = Order.objects.create(
            order_number="ORD-12345678",
            user=self.customer,
            dark_store=self.dark_store,
            subtotal=36.00,
            delivery_fee=30.00,
            total_amount=66.00,
            delivery_address_snapshot={},
            status=Order.OrderStatus.PENDING_PAYMENT,
            payment_status=Order.PaymentStatus.UNPAID,
        )

        self.client.force_authenticate(user=self.customer)
        url = reverse("orders-cancel", kwargs={"pk": str(order.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.OrderStatus.CANCELLED)

    def test_cancel_order_already_paid_fails(self):
        """Test that customer cannot cancel an already paid order."""
        order = Order.objects.create(
            order_number="ORD-12345678",
            user=self.customer,
            dark_store=self.dark_store,
            subtotal=36.00,
            delivery_fee=30.00,
            total_amount=66.00,
            delivery_address_snapshot={},
            status=Order.OrderStatus.CONFIRMED,
            payment_status=Order.PaymentStatus.PAID,
        )

        self.client.force_authenticate(user=self.customer)
        url = reverse("orders-cancel", kwargs={"pk": str(order.id)})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertNotEqual(order.status, Order.OrderStatus.CANCELLED)
