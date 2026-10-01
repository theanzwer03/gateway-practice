from django.db import transaction
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsAdminRole, is_gateway_admin
from .models import Client, Customer
from .serializers import ClientSerializer, CustomerSerializer


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def get_queryset(self):
        user = self.request.user
        if is_gateway_admin(user):
            return self.queryset
        return self.queryset.filter(clients=user).distinct() if isinstance(user, Client) else self.queryset.none()

    def get_permissions(self):
        return [IsAdminRole()] if self.action not in ("list", "retrieve", "create") else super().get_permissions()

    @transaction.atomic
    def perform_create(self, serializer):
        customer = serializer.save()
        if isinstance(self.request.user, Client):
            self.request.user.customers.add(customer)


class ClientViewSet(ModelViewSet):
    queryset = Client.objects.prefetch_related("customers")
    serializer_class = ClientSerializer

    def get_queryset(self):
        user = self.request.user
        if is_gateway_admin(user):
            return self.queryset
        return self.queryset.filter(pk=user.pk) if isinstance(user, Client) else self.queryset.none()

    def get_permissions(self):
        return [IsAdminRole()] if self.action not in ("list", "retrieve") else super().get_permissions()
