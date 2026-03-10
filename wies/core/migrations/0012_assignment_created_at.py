from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
