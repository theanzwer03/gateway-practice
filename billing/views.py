from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsAdminRole, is_gateway_admin
from customers.models import Client
from .models import Invoice, Payment, Transaction
from .serializers import InvoiceSerializer, PaymentSerializer, TransactionSerializer


class CustomerScopedViewSet(ModelViewSet):
    def get_queryset(self):
        queryset = self.queryset.select_related("customer")
        user = self.request.user
        if is_gateway_admin(user):
            return queryset
        return queryset.filter(customer__clients=user).distinct() if isinstance(user, Client) else queryset.none()

    def get_permissions(self):
        return [IsAdminRole()] if self.action not in ("list", "retrieve") else super().get_permissions()


class InvoiceViewSet(CustomerScopedViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer


class PaymentViewSet(CustomerScopedViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer


class TransactionViewSet(CustomerScopedViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
