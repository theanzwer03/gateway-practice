from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


VERIFICATION_SALT = "clients.email-verification"


def email_link(base_url, **parameters):
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query))
    query.update(parameters)
    return urlunsplit(parts._replace(query=urlencode(query)))


def send_verification_email(user):
    token = signing.dumps(
        {"client_id": str(user.pk), "email": user.email}, salt=VERIFICATION_SALT
    )
    link = email_link(settings.EMAIL_VERIFICATION_URL, token=token)
    send_mail(
        "Verify your Gateway email",
        f"Welcome to Gateway! Verify your email using this link:\n\n{link}\n\n"
        f"This link expires in {settings.EMAIL_VERIFICATION_TIMEOUT // 3600} hours.\n"
        "If you did not create this account, ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def send_password_reset_email(user):
    link = email_link(
        settings.PASSWORD_RESET_URL,
        uid=urlsafe_base64_encode(force_bytes(user.pk)),
        token=default_token_generator.make_token(user),
    )
    send_mail(
        "Reset your Gateway password",
        f"Reset your password using this link:\n\n{link}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_TIMEOUT // 60} minutes.\n"
        "If you did not request a password reset, ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
