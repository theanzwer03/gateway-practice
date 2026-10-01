from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
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


class CurrentUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="current-user",
            email="current@example.com",
            password="strong-pass-123",
            first_name="Current",
            last_name="User",
            role=User.Role.CLIENT,
        )

    def test_authenticated_user_can_get_their_details(self):
        token = Token.objects.create(user=self.user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.user.id))
        self.assertEqual(response.data["username"], "current-user")
        self.assertEqual(response.data["email"], "current@example.com")
        self.assertEqual(response.data["first_name"], "Current")
        self.assertEqual(response.data["last_name"], "User")
        self.assertEqual(response.data["role"], User.Role.CLIENT)
        self.assertNotIn("password", response.data)

    def test_unauthenticated_request_is_rejected(self):
        response = APIClient().get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)


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
        return User.objects.get(username="new-client")

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
        self.assertEqual(user.role, User.Role.CLIENT)
        self.assertTrue(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertFalse(hasattr(user, "client_profile"))
        self.assertTrue(user.check_password(self.registration["password"]))
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])
        self.assertIn("verify-email", mail.outbox[0].body)

    def test_verification_enables_login_and_rejects_reuse(self):
        self.register()
        credentials = {"username": "new-client", "password": self.registration["password"]}
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

    def test_resend_verification_has_generic_response(self):
        self.register()
        response = self.post("resend-verification", {"email": "NEW@example.com"})
        self.assertEqual(len(mail.outbox), 2)
        missing = self.post("resend-verification", {"email": "missing@example.com"})
        self.assertEqual(response.data, missing.data)
        self.assertEqual(len(mail.outbox), 2)

    def test_password_reset_changes_password_revokes_token_and_rejects_reuse(self):
        user = self.verified_user()
        token = Token.objects.create(user=user)
        data = {**self.reset_parameters(), "new_password": "Different-Strong-99!"}
        self.assertEqual(self.post("reset-password", data).status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(data["new_password"]))
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())
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
        from .serializers import UserSerializer

        user = UserSerializer().create({**self.registration, "role": User.Role.CLIENT})
        self.assertFalse(user.email_verified)
        self.assertEqual(mail.outbox[0].to, [user.email])

    def test_client_email_change_requires_verification_and_revokes_token(self):
        from .serializers import UserSerializer

        user = self.verified_user()
        old_verification = self.email_parameters()
        Token.objects.create(user=user)
        UserSerializer().update(user, {"email": "changed@example.com"})
        self.assertFalse(user.email_verified)
        self.assertFalse(Token.objects.filter(user=user).exists())
        self.assertEqual(mail.outbox[-1].to, ["changed@example.com"])
        self.assertEqual(self.post("verify-email", old_verification).status_code, 400)
        self.assertEqual(self.post("verify-email", self.email_parameters()).status_code, 200)

    def test_registered_user_has_no_customer_access_until_admin_links_profile(self):
        user = self.verified_user()
        customer = Customer.objects.create(name="Private", email="private@example.com")
        self.api.force_authenticate(user=user)
        response = self.api.get("/api/customers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])
        self.assertEqual(self.api.get(f"/api/customers/{customer.pk}/").status_code, 404)
        self.assertEqual(self.api.post("/api/customers/", {"name": "Unauthorized"}).status_code, 403)
        Client.objects.create(user=user, customer=customer)
        self.assertEqual(self.api.get(f"/api/customers/{customer.pk}/").status_code, 200)
