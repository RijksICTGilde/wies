from django.db import migrations, models

from wies.core.public_id import backfill_public_ids, generate_public_id


def fill_public_ids(apps, schema_editor):
    backfill_public_ids(apps, "rijksauth", ["user"])


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
