import secrets
import uuid

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models.functions import Lower


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


class Client(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    customers = models.ManyToManyField(Customer, related_name="clients", blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_primary_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["email"]
        constraints = [models.UniqueConstraint(Lower("email"), name="client_email_case_insensitive_unique")]

    USERNAME_FIELD = "email"
    is_staff = False
    is_superuser = False

    def __str__(self):
        return self.email


def generate_client_token():
    return secrets.token_hex(20)


class ClientToken(models.Model):
    key = models.CharField(max_length=40, primary_key=True, default=generate_client_token, editable=False)
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="auth_token")
    created_at = models.DateTimeField(auto_now_add=True)
