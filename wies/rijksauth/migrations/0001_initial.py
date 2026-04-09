import django.utils.timezone
from django.db import migrations, models


def update_content_type_forward(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="core", model="user").update(app_label="rijksauth")


def update_content_type_reverse(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="rijksauth", model="user").update(app_label="core")


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0016_unique_colleague_email_source"),
    ]

    operations = [
        # Move User model from core to rijksauth
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="User",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("password", models.CharField(max_length=128, verbose_name="password")),
                        ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                        (
                            "is_superuser",
                            models.BooleanField(
                                default=False,
                                help_text="Designates that this user has all permissions without explicitly assigning them.",
                                verbose_name="superuser status",
                            ),
                        ),
                        ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                        ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                        (
                            "is_staff",
                            models.BooleanField(
                                default=False,
                                help_text="Designates whether the user can log into this admin site.",
                                verbose_name="staff status",
                            ),
                        ),
                        (
                            "is_active",
                            models.BooleanField(
                                default=True,
                                help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                                verbose_name="active",
                            ),
                        ),
                        (
                            "date_joined",
                            models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined"),
                        ),
                        ("email", models.EmailField(max_length=254, unique=True)),
                        (
                            "groups",
                            models.ManyToManyField(
                                blank=True,
                                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                                related_name="user_set",
                                related_query_name="user",
                                to="auth.group",
                                verbose_name="groups",
                            ),
                        ),
                        (
                            "user_permissions",
                            models.ManyToManyField(
                                blank=True,
                                help_text="Specific permissions for this user.",
                                related_name="user_set",
                                related_query_name="user",
                                to="auth.permission",
                                verbose_name="user permissions",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "auth_user",
                    },
                ),
            ],
            database_operations=[
                # Rename main user table
                migrations.RunSQL(
                    "ALTER TABLE core_user RENAME TO auth_user;",
                    "ALTER TABLE auth_user RENAME TO core_user;",
                ),
                # Rename M2M tables (Django derives names from db_table)
                migrations.RunSQL(
                    "ALTER TABLE core_user_groups RENAME TO auth_user_groups;",
                    "ALTER TABLE auth_user_groups RENAME TO core_user_groups;",
                ),
                migrations.RunSQL(
                    "ALTER TABLE core_user_user_permissions RENAME TO auth_user_user_permissions;",
                    "ALTER TABLE auth_user_user_permissions RENAME TO core_user_user_permissions;",
                ),
                # Drop username column (no longer used, email is USERNAME_FIELD)
                migrations.RunSQL(
                    "ALTER TABLE auth_user DROP COLUMN username;",
                    "ALTER TABLE auth_user ADD COLUMN username varchar(150) NOT NULL DEFAULT '';",
                ),
            ],
        ),
        # Update content type so permissions keep working
        migrations.RunPython(
            update_content_type_forward,
            update_content_type_reverse,
        ),
        # Create AuthEvent table (new model, straightforward)
        migrations.CreateModel(
            name="AuthEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user_email", models.EmailField(blank=True, db_index=True, max_length=255)),
                ("name", models.CharField(db_index=True, max_length=32)),
                ("context", models.JSONField(default=dict)),
            ],
        ),
    ]
