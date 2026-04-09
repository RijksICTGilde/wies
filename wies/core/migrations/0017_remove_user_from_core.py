"""State-only migration: remove User from core, repoint FKs to rijksauth.User."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_unique_colleague_email_source"),
        ("rijksauth", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                # Remove M2M fields before deleting the model
                migrations.RemoveField(model_name="user", name="groups"),
                migrations.RemoveField(model_name="user", name="user_permissions"),
                # Remove User from core's state (table already moved by rijksauth.0001)
                migrations.DeleteModel(name="User"),
                # Repoint FK fields to rijksauth.User in state
                migrations.AlterField(
                    model_name="colleague",
                    name="user",
                    field=models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="colleague",
                        to="rijksauth.User",
                    ),
                ),
                migrations.AlterField(
                    model_name="task",
                    name="created_by",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tasks",
                        to="rijksauth.User",
                    ),
                ),
            ],
            database_operations=[],  # All DB changes handled by rijksauth.0001
        ),
    ]
