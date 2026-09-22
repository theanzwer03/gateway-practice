from django.db import transaction
from rest_framework import serializers

from accounts.models import User
from accounts.serializers import UserSerializer
from .models import Client, Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone", "billing_address", "tax_id", "status", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Client
        fields = ["id", "user", "customer", "customer_name", "job_title", "phone", "is_primary_contact", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user_data["role"] = User.Role.CLIENT
        user = UserSerializer().create(user_data)
        return Client.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user_data["role"] = User.Role.CLIENT
            UserSerializer().update(instance.user, user_data)
        return super().update(instance, validated_data)
