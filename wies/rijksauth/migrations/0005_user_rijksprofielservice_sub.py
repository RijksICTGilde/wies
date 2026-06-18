from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rijksauth", "0004_remove_super_users"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="rijksprofielservice_sub",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
