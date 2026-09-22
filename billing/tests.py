from decimal import Decimal

from django.test import TestCase

from customers.models import Customer
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
