from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from .models import Client, Customer


class ClientModelTests(TestCase):
    def test_client_profile_requires_client_role(self):
        customer = Customer.objects.create(name="Acme", email="billing@acme.test")
        user = User.objects.create_user(username="admin", email="admin@acme.test", role=User.Role.ADMIN)
        client = Client(customer=customer, user=user)
        with self.assertRaises(ValidationError):
            client.full_clean()
