import unittest

from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase

from .models import Client, Customer


class ClientModelTests(TestCase):
    def test_client_is_standalone_and_can_have_multiple_customers(self):
        client = Client(username="standalone", email="client@example.com")
        client.set_password("Strong-password-99!")
        client.save()
        client.customers.add(
            Customer.objects.create(name="First", email=client.email),
            Customer.objects.create(name="Second", email=client.email),
        )
        self.assertEqual(client.customers.count(), 2)
        self.assertTrue(client.check_password("Strong-password-99!"))
        self.assertFalse(client.is_staff)
        self.assertFalse(client.is_superuser)


class StandaloneClientMigrationTests(unittest.TestCase):
    def test_migration_preserves_credentials_links_and_admins(self):
        # Exercise the full migration on an independent database, including legacy data.
        alias = "client_migration_test"
        config = connections["default"].settings_dict.copy()
        config["NAME"] = ":memory:"
        connections.databases[alias] = config
        connection = connections[alias]
        try:
            executor = MigrationExecutor(connection)
            old_targets = [
                ("accounts", "0002_user_email_verified"),
                ("customers", "0001_initial"),
                ("billing", "0001_initial"),
                ("authtoken", "0004_alter_tokenproxy_options"),
                ("admin", "0003_logentry_add_action_flag_choices"),
            ]
            executor.migrate(old_targets)
            old_apps = executor.loader.project_state(old_targets).apps
            User = old_apps.get_model("accounts", "User")
            Client = old_apps.get_model("customers", "Client")
            Customer = old_apps.get_model("customers", "Customer")
            Invoice = old_apps.get_model("billing", "Invoice")
            Token = old_apps.get_model("authtoken", "Token")
            admin = User.objects.using(alias).create(username="admin", email="admin@example.com", role="admin")
            user = User.objects.using(alias).create(username="legacy", email="Legacy@example.com", role="client", password="preserved-hash", email_verified=True)
            second = User.objects.using(alias).create(username="other", email="other@example.com", role="client", password="other-hash")
            orphan = User.objects.using(alias).create(username="orphan", email="orphan@example.com", role="client", password="orphan-hash", email_verified=False)
            customer = Customer.objects.using(alias).create(name="Existing", email=user.email)
            profile = Client.objects.using(alias).create(user=user, customer=customer)
            Client.objects.using(alias).create(user=second, customer=customer)
            invoice = Invoice.objects.using(alias).create(customer=customer, number="OLD-001", subtotal=10, tax=0, total=10)
            Token.objects.using(alias).create(user=user, key="a" * 40)
            Token.objects.using(alias).create(user=admin, key="b" * 40)
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            executor.migrate(targets)
            apps = executor.loader.project_state(targets).apps
            migrated = apps.get_model("customers", "Client").objects.using(alias).get(pk=profile.pk)
            self.assertEqual(migrated.password, "preserved-hash")
            self.assertEqual(migrated.email, "legacy@example.com")
            self.assertTrue(migrated.email_verified)
            self.assertEqual(list(migrated.customers.values_list("pk", flat=True)), [customer.pk])
            migrated_orphan = apps.get_model("customers", "Client").objects.using(alias).get(username="orphan")
            self.assertEqual(migrated_orphan.password, orphan.password)
            self.assertFalse(migrated_orphan.email_verified)
            self.assertEqual(migrated_orphan.customers.count(), 1)
            self.assertEqual(apps.get_model("customers", "Customer").objects.using(alias).get(pk=customer.pk).clients.count(), 2)
            self.assertEqual(apps.get_model("billing", "Invoice").objects.using(alias).get(pk=invoice.pk).customer_id, customer.pk)
            self.assertEqual(list(apps.get_model("accounts", "User").objects.using(alias).values_list("pk", flat=True)), [admin.pk])
            self.assertEqual(apps.get_model("authtoken", "Token").objects.using(alias).count(), 1)
        finally:
            connection.close()
            del connections[alias]
            del connections.databases[alias]
