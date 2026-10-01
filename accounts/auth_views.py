from django.contrib.auth.hashers import make_password
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from customers.models import Client, ClientToken
from customers.serializers import ClientSerializer
from .email_auth import PublicEmailView
from .permissions import IsAdminRole
from .serializers import UserSerializer


class ClientLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ClientLoginView(PublicEmailView):
    serializer_class = ClientLoginSerializer

    @extend_schema(responses={200: inline_serializer(
        name="ClientLoginResponse",
        fields={"token": serializers.CharField(), "client": ClientSerializer()},
    )})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        client = Client.objects.filter(email__iexact=data["email"]).first()
        if client is None:
            make_password(data["password"])
            return Response({"detail": "Invalid credentials."}, status=400)
        if not client.check_password(data["password"]) or not client.is_active:
            return Response({"detail": "Invalid credentials."}, status=400)
        if not client.email_verified:
            return Response({"detail": "Verify your email before logging in."}, status=400)
        token, _ = ClientToken.objects.get_or_create(client=client)
        return Response({"token": token.key, "client": ClientSerializer(client).data})


class AdminObtainAuthToken(ObtainAuthToken):
    @extend_schema(request=AuthTokenSerializer, responses=inline_serializer(
        name="AdminLoginResponse",
        fields={"token": serializers.CharField(), "user": UserSerializer()},
    ))
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class CurrentUserView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]

    def get_object(self):
        return self.request.user


class CurrentClientView(RetrieveAPIView):
    serializer_class = ClientSerializer

    def get_object(self):
        from rest_framework.exceptions import PermissionDenied

        if not isinstance(self.request.user, Client):
            raise PermissionDenied("Client authentication required.")
        return self.request.user


obtain_client_auth_token = ClientLoginView.as_view()
obtain_admin_auth_token = AdminObtainAuthToken.as_view()
current_user = CurrentUserView.as_view()
current_client = CurrentClientView.as_view()
