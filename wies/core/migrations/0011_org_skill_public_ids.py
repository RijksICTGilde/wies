from django.db import migrations, models

from wies.core.public_id import PUBLIC_ID_LENGTH, generate_public_id

# OrganizationUnit and Skill back the ?org=/?rol= filter facets; give them the
# same unguessable public_id so those URLs stop exposing sequential ids.
MODELS = ["organizationunit", "skill"]


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
        ("core", "0010_public_ids"),
    ]

    operations = [
        # Add nullable, backfill distinct values, then enforce unique + non-null.
        *[
            migrations.AddField(
                model_name=model_name,
                name="public_id",
                field=models.CharField(editable=False, max_length=PUBLIC_ID_LENGTH, null=True),
            )
            for model_name in MODELS
        ],
        migrations.RunPython(fill_public_ids, migrations.RunPython.noop),
        *[
            migrations.AlterField(
                model_name=model_name,
                name="public_id",
                field=models.CharField(
                    default=generate_public_id, editable=False, max_length=PUBLIC_ID_LENGTH, unique=True
                ),
            )
            for model_name in MODELS
        ],
    ]
