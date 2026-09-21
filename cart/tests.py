from django.urls import reverse
from logistics.gis_compat import Point
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import User
from catalog.models import Category
from products.models import Product, ProductInventory
from logistics.models import DarkStore
from cart.models import Cart, CartItem


class CartAPITests(APITestCase):

    def setUp(self):
        # 1. Create a customer user
        self.user = User.objects.create_user(
            phone_number="01712345678",
            email="testcustomer@example.com",
            password="securepassword123",
            role=User.Role.CUSTOMER,
        )

        # 2. Authenticate the user
        self.client.force_authenticate(user=self.user)

        # 3. Create a Dark Store
        self.dark_store = DarkStore.objects.create(
            name="Uttara Dark Store",
            code="UTTARA-01",
            contact_number="01799999999",
            address="Uttara Sector 3, Dhaka",
            is_active=True,
        )

        # 4. Associate the customer's cart with the Dark Store
        self.cart = Cart.objects.create(
            user=self.user,
            dark_store=self.dark_store,
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
            stock_qty=10,
            store_price=18.00,  # Store-specific price
            is_available=True,
        )

    def test_get_cart_success(self):
        """Test retrieving the current user's cart."""
        url = reverse("cart-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["dark_store"], self.dark_store.id)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(float(response.data["total_price"]), 0.00)

    def test_add_item_to_cart_success(self):
        """Test adding a valid product to the cart."""
        url = reverse("cart-add-item")
        data = {
            "product_id": self.product.id,
            "quantity": 2
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 2)
        # Using store-specific discount price: 18.00 * 2 = 36.00
        self.assertEqual(float(response.data["total_price"]), 36.00)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["quantity"], 2)
        self.assertEqual(float(response.data["items"][0]["unit_price"]), 18.00)

    def test_add_item_insufficient_stock(self):
        """Test that adding quantity greater than stock fails."""
        url = reverse("cart-add-item")
        data = {
            "product_id": self.product.id,
            "quantity": 11  # Stock is only 10
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Only 10 units are available.")

    def test_update_cart_item_quantity_success(self):
        """Test updating the quantity of an item already in the cart."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            inventory=self.inventory,
            quantity=2,
            unit_price=18.00,
        )

        url = reverse("cart-update-item-quantity", kwargs={"item_id": str(cart_item.id)})
        data = {
            "quantity": 5
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 5)
        self.assertEqual(float(response.data["total_price"]), 90.00)

    def test_remove_cart_item_success(self):
        """Test removing a specific item from the cart."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            inventory=self.inventory,
            quantity=2,
            unit_price=18.00,
        )

        url = reverse("cart-remove-item", kwargs={"item_id": str(cart_item.id)})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 0)
        self.assertEqual(len(response.data["items"]), 0)

    def test_clear_cart_success(self):
        """Test clearing all items from the cart."""
        CartItem.objects.create(
            cart=self.cart,
            inventory=self.inventory,
            quantity=2,
            unit_price=18.00,
        )

        url = reverse("cart-clear-cart")
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Cart cleared successfully.")
        self.assertEqual(response.data["cart"]["total_items"], 0)
        self.assertEqual(len(response.data["cart"]["items"]), 0)
