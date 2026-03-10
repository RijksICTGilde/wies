from django.db import migrations, models


def migrate_lead_to_open(apps, schema_editor):
    Assignment = apps.get_model("core", "Assignment")
    Assignment.objects.filter(status="LEAD").update(status="OPEN")


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
        migrations.RunPython(migrate_lead_to_open, migrations.RunPython.noop),
    ]
