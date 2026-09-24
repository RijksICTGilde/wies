"""Removes the Opdrachtbeheer role and hands its members the roles that replace it.

A BDM now carries every wies-sourced opdracht, which is exactly what Opdrachtbeheer
granted, so the role is gone. 0009 handed it to the addresses in STAFF_EMAILS; this
gives those same addresses BDM and Office assistent instead, once, and drops the
group. A group nothing names would otherwise stay on the user sheet under its key.

Both roles, not only BDM: an application administrator starts out able to do
everything and takes off what they do not need.

Not in setup_roles(): that runs on every start and would re-grant a role to
someone who removed it from themselves.
"""

import os

from django.db import migrations

GONE = ("Opdrachtbeheer", "assignment_admin")
# The keys 0011 leaves behind.
REPLACEMENTS = ("bdm", "office_assistant")


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("rijksauth", "User")
    groups = [Group.objects.get_or_create(name=name)[0] for name in REPLACEMENTS]
    emails = {e.strip().lower() for e in os.environ.get("STAFF_EMAILS", "").split(",") if e.strip()}
    for user in User.objects.all():
        if user.email and user.email.lower() in emails:
            user.groups.add(*groups)
    Group.objects.filter(name__in=GONE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("rijksauth", "0011_role_keys"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
