import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Customer(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    billing_address = models.JSONField(default=dict, blank=True)
    tax_id = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_profile")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="clients")
    job_title = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_primary_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["customer__name", "user__email"]

    def clean(self):
        if self.user_id and self.user.role != "client":
            raise ValidationError({"user": "A client profile must reference a user with the client role."})

    def __str__(self):
        return f"{self.user.email} ({self.customer.name})"
