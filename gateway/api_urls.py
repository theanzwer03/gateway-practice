from rest_framework.routers import DefaultRouter

from accounts.views import UserViewSet
from billing.views import InvoiceViewSet, PaymentViewSet, TransactionViewSet
from customers.views import ClientViewSet, CustomerViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("customers", CustomerViewSet, basename="customer")
router.register("clients", ClientViewSet, basename="client")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("payments", PaymentViewSet, basename="payment")
router.register("transactions", TransactionViewSet, basename="transaction")

urlpatterns = router.urls
