from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

from customers.serializers import ClientSerializer
from .serializers import UserSerializer


class ClientObtainAuthToken(ObtainAuthToken):
    """Issue a DRF token and return the authenticated user's client profile."""

    @extend_schema(
        request=AuthTokenSerializer,
        responses=inline_serializer(
            name="ClientLoginResponse",
            fields={
                "token": serializers.CharField(),
                "user": UserSerializer(),
                "client": ClientSerializer(allow_null=True),
            },
        ),
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        client = getattr(user, "client_profile", None)

        return Response({
            "token": token.key,
            "user": UserSerializer(user).data,
            "client": ClientSerializer(client).data if client else None,
        })


obtain_client_auth_token = ClientObtainAuthToken.as_view()
