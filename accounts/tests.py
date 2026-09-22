from django.test import TestCase

from .models import User


class UserModelTests(TestCase):
    def test_password_is_hashed_by_manager(self):
        user = User.objects.create_user(username="admin", email="admin@example.com", password="strong-pass-123")
        self.assertTrue(user.check_password("strong-pass-123"))
