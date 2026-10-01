from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from accounts.emails import send_verification_email
from .models import Client, ClientToken, Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone", "billing_address", "tax_id", "status", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClientSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False, required=True)
    customer_name = serializers.CharField(write_only=True, required=False, max_length=255, allow_blank=False)
    customers = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Client
        fields = ["id", "username", "email", "first_name", "last_name", "password", "email_verified", "is_active", "customers", "customer_name", "job_title", "phone", "is_primary_contact", "created_at", "updated_at"]
        read_only_fields = ["id", "email_verified", "created_at", "updated_at"]

    def validate_email(self, value):
        value = value.lower()
        queryset = Client.objects.filter(email__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, attrs):
        if self.instance and "customer_name" in attrs:
            raise serializers.ValidationError({"customer_name": "Only used when creating a client."})
        if "password" in attrs:
            try:
                validate_password(attrs["password"], Client(**{key: value for key, value in attrs.items() if key != "customer_name"}))
            except ValidationError as error:
                raise serializers.ValidationError({"password": error.messages})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        customer_name = validated_data.pop("customer_name", validated_data["username"])
        password = validated_data.pop("password")
        client = Client(**validated_data)
        client.set_password(password)
        client.save()
        customer = Customer.objects.create(name=customer_name, email=client.email)
        client.customers.add(customer)
        send_verification_email(client)
        return client

    @transaction.atomic
    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        email_changed = "email" in validated_data and validated_data["email"] != instance.email
        if email_changed:
            validated_data["email_verified"] = False
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        if password or email_changed or not instance.is_active:
            ClientToken.objects.filter(client=instance).delete()
        if email_changed:
            send_verification_email(instance)
        return instance
