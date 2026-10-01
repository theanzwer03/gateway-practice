from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from customers.models import Client, ClientToken, Customer
from .models import User


class UserModelTests(TestCase):
    def test_password_is_hashed_by_manager(self):
        user = User.objects.create_user(username="admin", email="admin@example.com", password="strong-pass-123")
        self.assertTrue(user.check_password("strong-pass-123"))


class AdminAuthenticationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", email="admin@example.com", password="Strong-admin-99!")

    def test_admin_login_and_current_user(self):
        api = APIClient()
        response = api.post("/api/auth/token/", {"username": "admin", "password": "Strong-admin-99!"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("client", response.data)
        api.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        self.assertEqual(api.get("/api/auth/admin/me/").status_code, 200)
        self.assertEqual(api.get("/api/auth/me/").status_code, 403)
        self.assertEqual(api.get("/api/users/").status_code, 200)

    def test_user_serializer_rejects_client_role(self):
        from .serializers import UserSerializer
        serializer = UserSerializer(data={"username": "wrong", "email": "wrong@example.com", "role": "client"})
        self.assertFalse(serializer.is_valid())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailAuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.registration = {
            "username": "new-client", "email": "new@example.com",
            "password": "Correct-Horse-87!", "first_name": "New",
        }

    def post(self, endpoint, data):
        return self.api.post(f"/api/auth/{endpoint}/", data, format="json")

    def register(self):
        response = self.post("register", self.registration)
        self.assertEqual(response.status_code, 201)
        return Client.objects.get(username="new-client")

    def email_parameters(self):
        link = next(line for line in mail.outbox[-1].body.splitlines() if line.startswith("http"))
        return {key: values[0] for key, values in parse_qs(urlsplit(link).query).items()}

    def verified_user(self):
        user = self.register()
        self.assertEqual(self.post("verify-email", self.email_parameters()).status_code, 200)
        return user

    def reset_parameters(self):
        self.post("forgot-password", {"email": self.registration["email"]})
        return self.email_parameters()

    def test_registration_sends_email_and_cannot_grant_admin_access(self):
        self.registration.update(role="admin", is_active=False, email_verified=True, customer="123")
        user = self.register()
        self.assertFalse(User.objects.exists())
        self.assertEqual(user.customers.count(), 1)
        self.assertEqual(user.customers.get().email, user.email)
        self.assertTrue(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertFalse(hasattr(user, "user_id"))
        self.assertTrue(user.check_password(self.registration["password"]))
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])
        self.assertIn("verify-email", mail.outbox[0].body)

    def test_verification_enables_login_and_rejects_reuse(self):
        self.register()
        credentials = {"email": "new@example.com", "password": self.registration["password"]}
        self.assertEqual(self.post("login", credentials).status_code, 400)
        parameters = self.email_parameters()
        self.assertEqual(self.post("verify-email", parameters).status_code, 200)
        self.assertEqual(self.post("login", credentials).status_code, 200)
        self.assertEqual(self.post("verify-email", parameters).status_code, 400)

    def test_tampered_verification_token_is_rejected(self):
        user = self.register()
        parameters = self.email_parameters()
        parameters["token"] += "tampered"
        self.assertEqual(self.post("verify-email", parameters).status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    def test_expired_verification_token_is_rejected(self):
        self.register()
        with override_settings(EMAIL_VERIFICATION_TIMEOUT=-1):
            self.assertEqual(self.post("verify-email", self.email_parameters()).status_code, 400)

    def test_registration_rejects_weak_password_and_duplicate_email(self):
        data = {**self.registration, "password": "password"}
        self.assertEqual(self.post("register", data).status_code, 400)
        self.assertFalse(User.objects.exists())
        self.register()
        data = {**self.registration, "username": "other", "email": "NEW@example.com"}
        self.assertEqual(self.post("register", data).status_code, 400)

    def test_registration_rolls_back_when_email_delivery_fails(self):
        with patch("accounts.emails.send_mail", side_effect=SMTPException("offline")):
            with self.assertLogs("accounts.email_auth", level="ERROR"):
                self.assertEqual(self.post("register", self.registration).status_code, 503)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Customer.objects.exists())

    def test_resend_verification_has_generic_response(self):
        self.register()
        response = self.post("resend-verification", {"email": "NEW@example.com"})
        self.assertEqual(len(mail.outbox), 2)
        missing = self.post("resend-verification", {"email": "missing@example.com"})
        self.assertEqual(response.data, missing.data)
        self.assertEqual(len(mail.outbox), 2)

    def test_password_reset_changes_password_revokes_token_and_rejects_reuse(self):
        user = self.verified_user()
        token = ClientToken.objects.create(client=user)
        data = {**self.reset_parameters(), "new_password": "Different-Strong-99!"}
        self.assertEqual(self.post("reset-password", data).status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(data["new_password"]))
        self.assertFalse(ClientToken.objects.filter(pk=token.pk).exists())
        self.assertEqual(self.post("reset-password", data).status_code, 400)

    def test_forgot_password_does_not_reveal_account_existence(self):
        self.verified_user()
        response = self.post("forgot-password", {"email": "NEW@example.com"})
        self.assertEqual(len(mail.outbox), 2)
        missing = self.post("forgot-password", {"email": "missing@example.com"})
        self.assertEqual(response.data, missing.data)
        self.assertEqual(len(mail.outbox), 2)

    def test_unverified_or_inactive_users_cannot_reset_password(self):
        user = self.register()
        self.post("forgot-password", {"email": user.email})
        self.assertEqual(len(mail.outbox), 1)
        user.email_verified = True
        user.is_active = False
        user.save()
        self.post("forgot-password", {"email": user.email})
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_rejects_invalid_uid_tampered_token_and_weak_password(self):
        self.verified_user()
        parameters = self.reset_parameters()
        data = {**parameters, "new_password": "Different-Strong-99!"}
        self.assertEqual(self.post("reset-password", {**data, "uid": "invalid"}).status_code, 400)
        self.assertEqual(self.post("reset-password", {**data, "token": "invalid"}).status_code, 400)
        self.assertEqual(self.post("reset-password", {**data, "new_password": "password"}).status_code, 400)
        self.assertEqual(self.post("reset-password", data).status_code, 200)

    def test_expired_password_reset_is_rejected(self):
        self.verified_user()
        data = {**self.reset_parameters(), "new_password": "Different-Strong-99!"}
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            self.assertEqual(self.post("reset-password", data).status_code, 400)

    def test_email_delivery_failure_keeps_forgot_password_response_generic(self):
        self.verified_user()
        with patch("accounts.emails.send_mail", side_effect=SMTPException("offline")):
            with self.assertLogs("accounts.email_auth", level="ERROR"):
                response = self.post("forgot-password", {"email": "new@example.com"})
        missing = self.post("forgot-password", {"email": "missing@example.com"})
        self.assertEqual(response.data, missing.data)

    def test_email_endpoints_are_throttled(self):
        for _ in range(10):
            self.assertEqual(self.post("forgot-password", {"email": "missing@example.com"}).status_code, 200)
        self.assertEqual(self.post("forgot-password", {"email": "missing@example.com"}).status_code, 429)

    def test_admin_created_client_receives_verification_email(self):
        from customers.serializers import ClientSerializer

        user = ClientSerializer().create(dict(self.registration))
        self.assertFalse(user.email_verified)
        self.assertEqual(mail.outbox[0].to, [user.email])

    def test_client_email_change_requires_verification_and_revokes_token(self):
        from customers.serializers import ClientSerializer

        user = self.verified_user()
        old_verification = self.email_parameters()
        ClientToken.objects.create(client=user)
        ClientSerializer().update(user, {"email": "changed@example.com"})
        self.assertFalse(user.email_verified)
        self.assertFalse(ClientToken.objects.filter(client=user).exists())
        self.assertEqual(mail.outbox[-1].to, ["changed@example.com"])
        self.assertEqual(self.post("verify-email", old_verification).status_code, 400)
        self.assertEqual(self.post("verify-email", self.email_parameters()).status_code, 200)

    def test_registered_client_has_only_its_customers_and_can_create_more(self):
        client = self.verified_user()
        private = Customer.objects.create(name="Private", email="private@example.com")
        login = self.post("login", {"email": client.email, "password": self.registration["password"]})
        self.assertEqual(login.status_code, 200)
        self.assertNotIn("user", login.data)
        self.api.credentials(HTTP_AUTHORIZATION=f"ClientToken {login.data['token']}")
        self.assertEqual(self.api.get("/api/auth/me/").data["id"], str(client.pk))
        self.assertEqual(self.api.get("/api/users/").status_code, 403)
        self.assertEqual(self.api.get("/api/auth/admin/me/").status_code, 403)
        self.assertEqual(self.api.get(f"/api/customers/{private.pk}/").status_code, 404)
        response = self.api.post("/api/customers/", {"name": "Second", "email": "second@example.com", "clients": [str(client.pk)]}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(client.customers.count(), 2)
        self.assertEqual(self.api.get("/api/customers/").data["count"], 2)
        self.assertEqual(self.api.delete(f"/api/customers/{private.pk}/").status_code, 403)

    def test_client_token_rejects_inactive_and_unverified_accounts(self):
        client = self.verified_user()
        token = ClientToken.objects.create(client=client)
        self.api.credentials(HTTP_AUTHORIZATION=f"ClientToken {token.key}")
        client.email_verified = False
        client.save()
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)
        client.email_verified = True
        client.is_active = False
        client.save()
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)

    def test_admin_credentials_cannot_login_as_client(self):
        User.objects.create_user(username="admin", email="admin@example.com", password="Strong-admin-99!")
        self.assertEqual(self.post("login", {"email": "admin@example.com", "password": "Strong-admin-99!"}).status_code, 400)

    def test_client_credentials_cannot_login_as_admin(self):
        self.verified_user()
        self.assertEqual(self.post("token", {"username": "new-client", "password": self.registration["password"]}).status_code, 400)

    def test_client_password_is_never_returned(self):
        client = self.verified_user()
        from customers.serializers import ClientSerializer
        self.assertNotIn("password", ClientSerializer(client).data)
