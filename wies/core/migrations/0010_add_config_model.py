# Generated manually for filter settings feature

from django.db import migrations, models


def add_config_permission_to_beheerder(apps, schema_editor):
    """Add change_config permission to Beheerder group."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    try:
        beheerder = Group.objects.get(name="Beheerder")
        config_ct = ContentType.objects.get(app_label="core", model="config")
        change_config = Permission.objects.get(codename="change_config", content_type=config_ct)
        beheerder.permissions.add(change_config)
    except (Group.DoesNotExist, ContentType.DoesNotExist, Permission.DoesNotExist):
        # Group or permission doesn't exist yet, skip (will be added by setup_roles)
        pass


def reverse_permission(apps, schema_editor):
    """Remove change_config permission from Beheerder group."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    try:
        beheerder = Group.objects.get(name="Beheerder")
        config_ct = ContentType.objects.get(app_label="core", model="config")
        change_config = Permission.objects.get(codename="change_config", content_type=config_ct)
        beheerder.permissions.remove(change_config)
    except (Group.DoesNotExist, ContentType.DoesNotExist, Permission.DoesNotExist):
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_alter_assignment_source_url_and_more"),
    ]

    operations = [
        # Add Config model
        migrations.CreateModel(
            name="Config",
            fields=[
                (
                    "key",
                    models.CharField(
                        max_length=100,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("value", models.JSONField(default=dict)),
            ],
            options={
                "verbose_name": "Configuratie",
                "verbose_name_plural": "Configuraties",
            },
        ),
        # Add change_config permission to Beheerder group
        migrations.RunPython(add_config_permission_to_beheerder, reverse_permission),
    ]
