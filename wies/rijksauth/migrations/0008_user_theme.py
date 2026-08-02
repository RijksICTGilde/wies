from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rijksauth", "0007_authevent_ip_authevent_user_agent"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="theme",
            field=models.CharField(
                choices=[("system", "Systeem"), ("light", "Licht"), ("dark", "Donker")],
                default="system",
                max_length=6,
            ),
        ),
    ]
