from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import ClientToken


class ClientTokenAuthentication(TokenAuthentication):
    keyword = "ClientToken"
    model = ClientToken

    def authenticate_credentials(self, key):
        try:
            token = ClientToken.objects.select_related("client").get(key=key)
        except ClientToken.DoesNotExist:
            raise AuthenticationFailed("Invalid client token.")
        client = token.client
        if not client.is_active or not client.email_verified:
            raise AuthenticationFailed("Client account is inactive or unverified.")
        return client, token


class ClientTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "customers.authentication.ClientTokenAuthentication"
    name = "clientTokenAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "header", "name": "Authorization", "description": "ClientToken <token>"}
