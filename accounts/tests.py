from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import UserProfile, Address

User = get_user_model()


class UserProfileAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+8801711111111",
            email="customer@example.com",
            first_name="Rasid",
            last_name="Islam",
            password="password123",
            role="customer",
        )
        # Profile is auto-created on demand or manually
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                "alternate_phone": "+8801722222222",
                "date_of_birth": "1995-05-15"
            }
        )
        self.profile_url = reverse("user-profile")

    def test_retrieve_profile_unauthenticated(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_profile_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Zahid")
        self.assertEqual(response.data["alternate_phone"], "+8801722222222")

    def test_update_profile(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "first_name": "Rasid Updated",
            "last_name": "Islam Updated",
            "alternate_phone": "+8801733333333"
        }
        response = self.client.put(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user model fields updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Rasid Updated")
        
        # Verify profile model fields updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.alternate_phone, "+8801733333333")

    def test_partial_update_profile(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "alternate_phone": "+8801799999999"
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.alternate_phone, "+8801799999999")


class AddressAPITests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            phone_number="+8801711111111",
            email="user1@example.com",
            password="password123",
            role="customer",
        )
        self.user2 = User.objects.create_user(
            phone_number="+8801722222222",
            email="user2@example.com",
            password="password123",
            role="customer",
        )
        self.address1 = Address.objects.create(
            user=self.user1,
            title="Home",
            address_type="home",
            street_address="Road 1, House 2",
            area="Mirpur",
            city="Dhaka",
            latitude="23.810300",
            longitude="90.412500",
            is_default=True
        )
        self.address_list_url = reverse("address-list")

    def test_list_addresses_unauthenticated(self):
        response = self.client.get(self.address_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_addresses_only_returns_own_addresses(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.address_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Home")

        # User2 has no addresses yet
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(self.address_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_address(self):
        self.client.force_authenticate(user=self.user1)
        data = {
            "title": "Office",
            "address_type": "work",
            "street_address": "Road 10, Block C",
            "area": "Gulshan",
            "city": "Dhaka",
            "latitude": "23.792500",
            "longitude": "90.407800",
            "is_default": False
        }
        response = self.client.post(self.address_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Address.objects.filter(user=self.user1).count(), 2)

    def test_set_default_address(self):
        # Create a second address for user1
        address2 = Address.objects.create(
            user=self.user1,
            title="Office",
            address_type="work",
            street_address="Road 10, Block C",
            area="Gulshan",
            city="Dhaka",
            latitude="23.792500",
            longitude="90.407800",
            is_default=False
        )
        self.client.force_authenticate(user=self.user1)
        
        # Call set-default custom action on address2
        url = reverse("address-set-default", kwargs={"pk": address2.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        address2.refresh_from_db()
        self.address1.refresh_from_db()
        
        # Verify address2 is default, address1 is no longer default
        self.assertTrue(address2.is_default)
        self.assertFalse(self.address1.is_default)

    def test_cannot_access_other_users_address(self):
        self.client.force_authenticate(user=self.user2)
        url = reverse("address-detail", kwargs={"pk": self.address1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)