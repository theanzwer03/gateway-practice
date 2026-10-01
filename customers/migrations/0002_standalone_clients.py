import django.db.models.deletion
from django.db import migrations, models
from django.db.models.functions import Lower

import customers.models


def copy_client_accounts(apps, schema_editor):
    Client = apps.get_model("customers", "Client")
    Customer = apps.get_model("customers", "Customer")
    User = apps.get_model("accounts", "User")
    database = schema_editor.connection.alias
    profiles = Client.objects.using(database)
    seen_emails = set()
    for user in User.objects.using(database).filter(role="client"):
        if user.email.lower() in seen_emails:
            raise ValueError("Client emails must be unique ignoring case. Resolve duplicates before migrating.")
        seen_emails.add(user.email.lower())
    for profile in profiles.select_related("user"):
        user = profile.user
        profile.username = user.username
        profile.email = user.email.lower()
        profile.password = user.password
        profile.last_login = user.last_login
        profile.first_name = user.first_name
        profile.last_name = user.last_name
        profile.is_active = user.is_active
        profile.email_verified = user.email_verified
        profile.save(using=database)
        profile.customers.add(profile.customer_id)
    for user in User.objects.using(database).filter(role="client", is_staff=False, is_superuser=False):
        if not profiles.filter(user_id=user.pk).exists():
            profile = profiles.create(
                username=user.username, email=user.email.lower(), password=user.password,
                first_name=user.first_name, last_name=user.last_name,
                last_login=user.last_login, is_active=user.is_active,
                email_verified=user.email_verified,
            )
            customer = Customer.objects.using(database).create(name=user.username, email=user.email)
            profile.customers.add(customer)


class Migration(migrations.Migration):
    dependencies = [("customers", "0001_initial"), ("accounts", "0002_user_email_verified")]

    operations = [
        migrations.AlterModelOptions(name="client", options={"ordering": ["email"]}),
        migrations.AlterField(model_name="client", name="user", field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="client_profile", to="accounts.user")),
        migrations.AlterField(model_name="client", name="customer", field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="clients", to="customers.customer")),
        migrations.AddField(model_name="client", name="username", field=models.CharField(max_length=150, default=""), preserve_default=False),
        migrations.AddField(model_name="client", name="email", field=models.EmailField(max_length=254, default=""), preserve_default=False),
        migrations.AddField(model_name="client", name="password", field=models.CharField(max_length=128, verbose_name="password", default="!"), preserve_default=False),
        migrations.AddField(model_name="client", name="last_login", field=models.DateTimeField(blank=True, null=True, verbose_name="last login")),
        migrations.AddField(model_name="client", name="first_name", field=models.CharField(max_length=150, blank=True)),
        migrations.AddField(model_name="client", name="last_name", field=models.CharField(max_length=150, blank=True)),
        migrations.AddField(model_name="client", name="is_active", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="client", name="email_verified", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="client", name="customers", field=models.ManyToManyField(blank=True, related_name="clients", to="customers.customer")),
        migrations.RunPython(copy_client_accounts),
        migrations.RemoveField(model_name="client", name="user"),
        migrations.RemoveField(model_name="client", name="customer"),
        migrations.AlterField(model_name="client", name="username", field=models.CharField(max_length=150, unique=True)),
        migrations.AlterField(model_name="client", name="email", field=models.EmailField(max_length=254, unique=True)),
        migrations.AddConstraint(model_name="client", constraint=models.UniqueConstraint(Lower("email"), name="client_email_case_insensitive_unique")),
        migrations.CreateModel(name="ClientToken", fields=[
            ("key", models.CharField(default=customers.models.generate_client_token, editable=False, max_length=40, primary_key=True, serialize=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("client", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="auth_token", to="customers.client")),
        ]),
    ]

