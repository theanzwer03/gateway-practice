from decimal import Decimal

from rest_framework import serializers

from .models import Invoice, Payment, Transaction


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_currency(self, value):
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Use a three-letter ISO 4217 currency code.")
        return value.upper()

    def validate(self, attrs):
        subtotal = attrs.get("subtotal", getattr(self.instance, "subtotal", None))
        tax = attrs.get("tax", getattr(self.instance, "tax", Decimal("0")))
        total = attrs.get("total", getattr(self.instance, "total", None))
        if subtotal is not None and total is not None and total != subtotal + tax:
            raise serializers.ValidationError({"total": "Total must equal subtotal plus tax."})
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        invoice = attrs.get("invoice", getattr(self.instance, "invoice", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if invoice and customer and invoice.customer_id != customer.id:
            raise serializers.ValidationError({"invoice": "Invoice and payment must belong to the same customer."})
        return attrs

    def validate_currency(self, value):
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Use a three-letter ISO 4217 currency code.")
        return value.upper()


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        payment = attrs.get("payment", getattr(self.instance, "payment", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if payment and customer and payment.customer_id != customer.id:
            raise serializers.ValidationError({"payment": "Payment and transaction must belong to the same customer."})
        return attrs

    def validate_currency(self, value):
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Use a three-letter ISO 4217 currency code.")
        return value.upper()
