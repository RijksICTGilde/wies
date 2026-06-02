from django.db import migrations


def remove_super_users(apps, schema_editor):
    # Delete all super users
    User = apps.get_model("rijksauth", "User")
    User.objects.filter(is_superuser=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("rijksauth", "0003_alter_user_email_constraint"),
    ]

    operations = [
        migrations.RunPython(remove_super_users, migrations.RunPython.noop),
    ]
