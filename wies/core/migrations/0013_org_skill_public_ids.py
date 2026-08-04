from django.db import migrations, models

from wies.core.public_id import backfill_public_ids, generate_public_id

# OrganizationUnit and Skill back the ?org=/?rol= filter facets; give them the
# same unguessable public_id so those URLs stop exposing sequential ids.
MODELS = ["organizationunit", "skill"]


def fill_public_ids(apps, schema_editor):
    backfill_public_ids(apps, "core", MODELS)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_public_ids"),
    ]

    operations = [
        # Add nullable, backfill distinct values, then enforce unique + non-null.
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
