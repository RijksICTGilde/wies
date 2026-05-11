import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_dedupe_colleagues"),
    ]

    operations = [
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
