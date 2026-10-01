from django.db import migrations, models


def remove_migrated_client_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    users = User.objects.using(schema_editor.connection.alias)
    users.filter(role="client", is_staff=False, is_superuser=False).delete()
    users.filter(role="client").update(role="admin")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_email_verified"),
        ("customers", "0002_standalone_clients"),
        ("authtoken", "0004_alter_tokenproxy_options"),
        ("admin", "0003_logentry_add_action_flag_choices"),
    ]

    operations = [
        migrations.RunPython(remove_migrated_client_users),
        migrations.AlterField(model_name="user", name="role", field=models.CharField(choices=[("admin", "Admin")], db_index=True, default="admin", max_length=16)),
        migrations.RemoveField(model_name="user", name="email_verified"),
        migrations.AddConstraint(model_name="user", constraint=models.CheckConstraint(condition=models.Q(role="admin"), name="gateway_user_admin_only")),
    ]
