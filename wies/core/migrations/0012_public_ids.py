from django.db import migrations, models

from wies.core.public_id import generate_public_id

# Every URL-exposed core model gains an unguessable public_id (the User model in
# the rijksauth app gets its own migration; migrations cannot span apps).
MODELS = ["assignment", "colleague", "placement", "service", "label", "labelcategory", "suborganization"]


def fill_public_ids(apps, schema_editor):
    """Give every existing row its own public_id. Done row by row because a single
    callable default on AddField would apply one shared value and break unique."""
    for model_name in MODELS:
        model = apps.get_model("core", model_name)
        for obj in model.objects.filter(public_id__isnull=True):
            obj.public_id = generate_public_id()
            obj.save(update_fields=["public_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_suborganization_colleague_suborganization"),
    ]

    operations = [
        # Add all columns nullable first, then backfill distinct values, then
        # enforce unique + non-null — safe on the populated production DB.
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
