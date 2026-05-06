import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models

from wies.core.services.colleagues import dedupe_colleagues


def run_dedupe(apps, schema_editor):
    colleague_model = apps.get_model("core", "Colleague")
    placement_model = apps.get_model("core", "Placement")
    assignment_model = apps.get_model("core", "Assignment")
    dedupe_colleagues(colleague_model, placement_model, assignment_model)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_modify_event"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(run_dedupe, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="colleague",
            name="unique_colleague_email_source",
        ),
        migrations.AddConstraint(
            model_name="colleague",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("email"),
                models.F("source"),
                name="unique_colleague_email_source_ci",
            ),
        ),
    ]
