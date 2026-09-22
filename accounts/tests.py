from django.test import TestCase
from rest_framework.test import APIClient

from customers.models import Client, Customer
from .models import User


class UserModelTests(TestCase):
    def test_password_is_hashed_by_manager(self):
        user = User.objects.create_user(username="admin", email="admin@example.com", password="strong-pass-123")
        self.assertTrue(user.check_password("strong-pass-123"))


class ClientLoginTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Acme", email="billing@acme.test")
        self.user = User.objects.create_user(
            username="client-user",
            email="client@acme.test",
            password="strong-pass-123",
            role=User.Role.CLIENT,
        )
        self.client_profile = Client.objects.create(
            user=self.user,
            customer=self.customer,
            job_title="Billing Manager",
            is_primary_contact=True,
        )

    def test_token_endpoint_returns_token_and_client_details(self):
        response = APIClient().post(
            "/api/auth/token/",
            {"username": "client-user", "password": "strong-pass-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["id"], str(self.user.id))
        self.assertEqual(response.data["client"]["id"], str(self.client_profile.id))
        self.assertEqual(response.data["client"]["customer"], self.customer.id)

    def test_login_alias_returns_token_and_client_details(self):
        response = APIClient().post(
            "/api/auth/login/",
            {"username": "client-user", "password": "strong-pass-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["id"], str(self.user.id))
        self.assertEqual(response.data["client"]["id"], str(self.client_profile.id))
