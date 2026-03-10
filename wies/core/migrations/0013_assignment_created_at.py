from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_assignmentorganizationunit_role_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="assignment",
            name="status",
            field=models.CharField(
                choices=[("OPEN", "OPEN"), ("INGEVULD", "INGEVULD")],
                default="OPEN",
                max_length=20,
            ),
        ),
    ]
