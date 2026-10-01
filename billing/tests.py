from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Client, ClientToken, Customer
from .models import Invoice, Payment, Transaction
from .serializers import InvoiceSerializer, PaymentSerializer


class BillingValidationTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Acme", email="billing@acme.test")

    def test_invoice_total_must_match(self):
        serializer = InvoiceSerializer(data={
            "customer": self.customer.id,
            "number": "INV-001",
            "subtotal": "100.00",
            "tax": "10.00",
            "total": "109.00",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("total", serializer.errors)

    def test_payment_currency_is_normalized(self):
        serializer = PaymentSerializer(data={"customer": self.customer.id, "amount": Decimal("25.00"), "currency": "php"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["currency"], "PHP")


class ClientBillingAccessTests(TestCase):
    def setUp(self):
        self.client_account = Client.objects.create(username="client", email="client@example.com", email_verified=True)
        self.owned = [Customer.objects.create(name=name, email=self.client_account.email) for name in ("First", "Second")]
        self.client_account.customers.add(*self.owned)
        self.other = Customer.objects.create(name="Other", email="other@example.com")
        self.records = {}
        for index, customer in enumerate([*self.owned, self.other]):
            invoice = Invoice.objects.create(customer=customer, number=f"INV-{index}", subtotal=10, total=10)
            payment = Payment.objects.create(customer=customer, invoice=invoice, amount=10)
            entry = Transaction.objects.create(customer=customer, payment=payment, amount=10, type="charge", reference=f"TX-{index}")
            if customer == self.other:
                self.records = {"invoices": invoice, "payments": payment, "transactions": entry}
        self.api = APIClient()
        token = ClientToken.objects.create(client=self.client_account)
        self.api.credentials(HTTP_AUTHORIZATION=f"ClientToken {token.key}")

    def test_client_reads_billing_for_all_linked_customers_only(self):
        for endpoint, private in self.records.items():
            response = self.api.get(f"/api/{endpoint}/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 2)
            self.assertEqual(self.api.get(f"/api/{endpoint}/{private.pk}/").status_code, 404)
            self.assertEqual(self.api.post(f"/api/{endpoint}/", {}, format="json").status_code, 403)

    def test_admin_retains_access_to_all_customers(self):
        admin = User.objects.create_user(username="admin", email="admin@example.com")
        self.api.force_authenticate(user=admin)
        self.assertEqual(self.api.get("/api/invoices/").data["count"], 3)

    def test_client_with_same_id_as_admin_cannot_access_admin_records(self):
        User.objects.create_user(id=self.client_account.pk, username="admin", email="admin@example.com")
        self.assertEqual(self.api.get("/api/users/").status_code, 403)
        self.assertEqual(self.api.get("/api/clients/").data["count"], 1)
