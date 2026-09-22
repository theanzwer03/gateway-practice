from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsAdminRole
from .models import Client, Customer
from .serializers import ClientSerializer, CustomerSerializer


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == "admin":
            return self.queryset
        return self.queryset.filter(clients__user=user)

    def get_permissions(self):
        return [IsAdminRole()] if self.action not in ("list", "retrieve") else super().get_permissions()


class ClientViewSet(ModelViewSet):
    queryset = Client.objects.select_related("user", "customer")
    serializer_class = ClientSerializer

    def get_queryset(self):
        user = self.request.user
        return self.queryset if user.is_superuser or user.role == "admin" else self.queryset.filter(user=user)

    def get_permissions(self):
        return [IsAdminRole()] if self.action not in ("list", "retrieve") else super().get_permissions()
