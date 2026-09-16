"""Gives everyone in STAFF_EMAILS the new Opdrachtbeheer role, once, so nobody
loses the assignment rights STAFF_EMAILS used to carry.

Not in setup_roles(): that runs on every start and would re-grant the role to
someone who removed it from themselves.
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
