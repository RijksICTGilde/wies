"""Gives everyone in STAFF_EMAILS the new Opdrachtbeheer role, once.

Platform administration (STAFF_EMAILS) used to carry the assignment rights that
now belong to Opdrachtbeheer; this keeps those rights for whoever holds them
today. Each environment reads its own list at deploy time. It is deliberately
not in setup_roles(), which runs on every start and would re-grant the role to
someone who removed it from themselves. See features/roles.md.
"""

import os

from django.db import migrations


def backfill(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("rijksauth", "User")
    group, _ = Group.objects.get_or_create(name="Opdrachtbeheer")
    emails = {e.strip().lower() for e in os.environ.get("STAFF_EMAILS", "").split(",") if e.strip()}
    for user in User.objects.all():
        if user.email and user.email.lower() in emails:
            user.groups.add(group)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("rijksauth", "0008_user_public_id"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
