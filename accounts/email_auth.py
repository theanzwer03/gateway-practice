import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .emails import VERIFICATION_SALT, send_password_reset_email, send_verification_email
from customers.models import Client, ClientToken
from customers.serializers import ClientSerializer


logger = logging.getLogger(__name__)


class EmailAuthThrottle(AnonRateThrottle):
    rate = "10/hour"


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RegistrationSerializer(ClientSerializer):
    class Meta(ClientSerializer.Meta):
        fields = ["username", "email", "password", "first_name", "last_name", "customer_name", "phone"]
        read_only_fields = []


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerificationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=2048)


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=200)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class PublicEmailView(GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [EmailAuthThrottle]


class RegisterView(PublicEmailView):
    serializer_class = RegistrationSerializer

    @extend_schema(responses={201: DetailSerializer, 400: DetailSerializer, 503: DetailSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except (SMTPException, OSError):
            logger.exception("Registration verification email delivery failed")
            return Response({"detail": "Email delivery failed. Please try again later."}, status=503)
        return Response({"detail": "Registration successful. Check your email to verify your account."}, status=201)


class VerifyEmailView(PublicEmailView):
    serializer_class = VerificationSerializer

    @extend_schema(responses={200: DetailSerializer, 400: DetailSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = signing.loads(
                serializer.validated_data["token"], salt=VERIFICATION_SALT,
                max_age=settings.EMAIL_VERIFICATION_TIMEOUT,
            )
            with transaction.atomic():
                user = Client.objects.select_for_update().get(
                    pk=payload["client_id"], email=payload["email"],
                    email_verified=False, is_active=True,
                )
                user.email_verified = True
                user.save(update_fields=["email_verified", "updated_at"])
        except (signing.BadSignature, Client.DoesNotExist, KeyError, ValueError, DjangoValidationError):
            return Response({"detail": "Invalid or expired verification link."}, status=400)
        return Response({"detail": "Email verified. You can now log in."})


class ResendVerificationView(PublicEmailView):
    serializer_class = EmailSerializer

    @extend_schema(responses=DetailSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = Client.objects.filter(
            email__iexact=serializer.validated_data["email"],
            email_verified=False, is_active=True,
        ).first()
        if user:
            try:
                send_verification_email(user)
            except (SMTPException, OSError):
                logger.exception("Verification email delivery failed")
        return Response({"detail": "If the account needs verification, an email has been sent."})


class ForgotPasswordView(PublicEmailView):
    serializer_class = EmailSerializer

    @extend_schema(responses=DetailSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = Client.objects.filter(
            email__iexact=serializer.validated_data["email"],
            is_active=True, email_verified=True,
        ).first()
        if user and user.has_usable_password():
            try:
                send_password_reset_email(user)
            except (SMTPException, OSError):
                logger.exception("Password reset email delivery failed")
        return Response({"detail": "If an eligible account exists, a password reset email has been sent."})


class ResetPasswordView(PublicEmailView):
    serializer_class = ResetPasswordSerializer

    @extend_schema(responses={200: DetailSerializer, 400: DetailSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            try:
                user = Client.objects.select_for_update().get(
                    pk=force_str(urlsafe_base64_decode(data["uid"])),
                    is_active=True, email_verified=True,
                )
            except (ValueError, TypeError, OverflowError, UnicodeDecodeError, DjangoValidationError, Client.DoesNotExist):
                user = None
            if user is None or not default_token_generator.check_token(user, data["token"]):
                return Response({"detail": "Invalid or expired password reset link."}, status=400)
            try:
                validate_password(data["new_password"], user)
            except DjangoValidationError as error:
                raise serializers.ValidationError({"new_password": error.messages})
            user.set_password(data["new_password"])
            user.save(update_fields=["password", "updated_at"])
            ClientToken.objects.filter(client=user).delete()
        return Response({"detail": "Password reset successful. Log in with your new password."})
