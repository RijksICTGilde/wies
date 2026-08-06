import uuid

from django.db import migrations, models

from wies.core.public_id import generate_public_id

MODELS = ["user"]

BATCH_SIZE = 1000


def fill_public_ids(apps, schema_editor):
    """One distinct value per existing row; a callable AddField default would give them all the same one."""
    for model_name in MODELS:
        model = apps.get_model("rijksauth", model_name)
        batch = []
        for obj in model.objects.filter(public_id__isnull=True).iterator():
            obj.public_id = uuid.uuid4()
            batch.append(obj)
            if len(batch) >= BATCH_SIZE:
                model.objects.bulk_update(batch, ["public_id"])
                batch = []
        if batch:
            model.objects.bulk_update(batch, ["public_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("rijksauth", "0007_authevent_ip_authevent_user_agent"),
    ]

    operations = [
        *[
            migrations.AddField(
                model_name=model_name,
                name="public_id",
                field=models.UUIDField(editable=False, null=True),
            )
            for model_name in MODELS
        ],
        migrations.RunPython(fill_public_ids, migrations.RunPython.noop),
        *[
            migrations.AlterField(
                model_name=model_name,
                name="public_id",
                field=models.UUIDField(default=generate_public_id, editable=False, unique=True),
            )
            for model_name in MODELS
        ],
    ]
