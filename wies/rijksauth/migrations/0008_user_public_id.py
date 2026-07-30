from django.db import migrations, models

from wies.core.public_id import generate_public_id


def fill_public_ids(apps, schema_editor):
    """Give every existing user its own public_id. Done row by row because a
    single callable default on AddField would apply one shared value and break
    the unique constraint."""
    User = apps.get_model("rijksauth", "User")
    for user in User.objects.filter(public_id__isnull=True):
        user.public_id = generate_public_id()
        user.save(update_fields=["public_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("rijksauth", "0007_authevent_ip_authevent_user_agent"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="public_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(fill_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="public_id",
            field=models.UUIDField(default=generate_public_id, editable=False, unique=True),
        ),
    ]
