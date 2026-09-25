"""Removes the Opdrachtbeheer role and hands its members the roles that replace it.

A BDM now carries every wies-sourced opdracht, which is exactly what Opdrachtbeheer
granted, so the role is gone. 0009 handed it to the addresses in STAFF_EMAILS; this
gives those same addresses BDM and Office assistent instead, once, and drops the
group. A group nothing names would otherwise stay on the user sheet under its key.

Both roles for those addresses, not only BDM: an application administrator starts
out able to do everything and takes off what they do not need.

Whoever holds the group itself gets BDM and nothing more, whether or not their
address is on the list. 0009 is not the only way in: the roles screen hands out
Opdrachtbeheer too, so an environment that ran the earlier chain can have members
the address list never named, and deleting the group would take their rights with
it without a word. BDM alone, because user administration is what Opdrachtbeheer
never carried.

Not in setup_roles(): that runs on every start and would re-grant a role to
someone who removed it from themselves.
"""

import os

from django.db import migrations

GONE = ("Opdrachtbeheer", "assignment_admin")
# The keys 0011 leaves behind.
REPLACEMENTS = ("bdm", "office_assistant")
SUCCESSOR = "bdm"


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("rijksauth", "User")
    groups = {name: Group.objects.get_or_create(name=name)[0] for name in REPLACEMENTS}
    emails = {e.strip().lower() for e in os.environ.get("STAFF_EMAILS", "").split(",") if e.strip()}
    for user in User.objects.all():
        if user.email and user.email.lower() in emails:
            user.groups.add(*groups.values())
    for gone in Group.objects.filter(name__in=GONE):
        groups[SUCCESSOR].user_set.add(*gone.user_set.all())
        gone.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("rijksauth", "0011_role_keys"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
