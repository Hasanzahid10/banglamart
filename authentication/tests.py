```python
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User, OTPVerification
from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer


class RegisterSerializerTest(APITestCase):

    def test_register_success_phone(self):
        data = {
            "phone_number": "+8801700000000",
            "password": "SecurePassword123!",
            "first_name": "Zahid",
            "last_name": "Hasan",
        }

        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.phone_number, "+8801700000000")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_phone_verified)

    def test_register_success_email(self):
        data = {
            "email": "[EMAIL_ADDRESS]",
            "password": "SecurePassword123!",
            "first_name": "Zahid",
        }

        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.email, "[EMAIL_ADDRESS]")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_email_verified)

    def test_register_email_case_insensitive(self):
        data = {
            "email": "[EMAIL_ADDRESS]",
            "password": "SecurePassword123!",
        }

        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()

        self.assertEqual(user.email.lower(), "[EMAIL_ADDRESS]")

    def test_register_no_password(self):
        data = {
            "phone_number": "+8801700000000",
        }

        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()

        self.assertIsNone(user.password)
        self.assertFalse(user.is_phone_verified)

    def test_register_phone_too_short(self):
        data = {
            "phone_number": "123",
            "password": "SecurePassword123!",
        }

        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Enter a valid phone number.",
            serializer.errors["phone_number"]
        )

    def test_register_invalid_email(self):
        data = {
            "email": "invalid-email",
            "password": "SecurePassword123!",
        }

        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Enter a valid email address.",
            serializer.errors["email"]
        )

    def test_register_duplicate_phone(self):
        User.objects.create_user(
            phone_number="+8801700000000",
            password="SecurePassword123!",
        )

        data = {
            "phone_number": "+8801700000000",
            "password": "SecurePassword123!",
        }

        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "This phone number is already registered.",
            serializer.errors["phone_number"]
        )

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email="[EMAIL_ADDRESS]",
            password="SecurePassword123!",
        )

        data = {
            "email": "[EMAIL_ADDRESS]",
            "password": "SecurePassword123!",
        }

        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "This email address is already registered.",
            serializer.errors["email"]
        )

    def test_register_both_phone_email_required(self):
        data = {
            "password": "SecurePassword123!",
        }

        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("identifier", serializer.errors)


class SendOTPViewTest(APITestCase):

    def test_send_otp_phone(self):
        response = self.client.post(
            "/api/v1/auth/send-otp/",
            {"recipient": "+8801700000000"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "OTP sent via SMS."
        )

        otp = OTPVerification.objects.filter(
            recipient="+8801700000000",
            channel=OTPVerification.Channel.SMS,
            is_verified=False,
        ).first()

        self.assertIsNotNone(otp)

    def test_send_otp_email(self):
        response = self.client.post(
            "/api/v1/auth/send-otp/",
            {"recipient": "[EMAIL_ADDRESS]"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "OTP sent via EMAIL."
        )

        otp = OTPVerification.objects.filter(
            recipient="[EMAIL_ADDRESS]",
            channel=OTPVerification.Channel.EMAIL,
            is_verified=False,
        ).first()

        self.assertIsNotNone(otp)

    def test_send_otp_invalid_phone(self):
        response = self.client.post(
            "/api/v1/auth/send-otp/",
            {"recipient": "123"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Enter a valid phone number or email address.",
            response.data["recipient"]
        )

    def test_send_otp_invalid_email(self):
        response = self.client.post(
            "/api/v1/auth/send-otp/",
            {"recipient": "invalid"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Enter a valid phone number or email address.",
            response.data["recipient"]
        )

    def test_send_otp_invalid_phone_with_plus(self):
        response = self.client.post(
            "/api/v1/auth/send-otp/",
            {"recipient": "+88017"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Enter a valid phone number or email address.",
            response.data["recipient"]
        )

    def test_send_otp_resend_invalidates_previous(self):
        # First OTP
        response1 = self.client.post(
            "/api/v1/auth
