from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsAdminRole
from .models import Invoice, Payment, Transaction
from .serializers import InvoiceSerializer, PaymentSerializer, TransactionSerializer


class CustomerScopedViewSet(ModelViewSet):
    def get_queryset(self):
        queryset = self.queryset.select_related("customer")
        user = self.request.user
        return queryset if user.is_superuser or user.role == "admin" else queryset.filter(customer__clients__user=user)

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
