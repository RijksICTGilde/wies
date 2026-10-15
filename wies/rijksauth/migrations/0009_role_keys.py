"""Renames the role groups from their screen label to a key, and gives everyone in
STAFF_EMAILS both beheer roles once.

``Group.name`` becomes a key the code matches on; what a role is called on screen
lives in ``ROLE_LABELS`` (``wies/core/roles.py``). The names are spelled out here
rather than imported: a migration is frozen in time and app code is not.

If the key group already exists (``setup_roles()`` ran first), the members and
permissions of the old group are merged into it and the old group is removed.

The STAFF_EMAILS addresses lose the functional rights the address list used to
carry, so they get ``business_manager`` and ``user_admin`` instead and take off
what they do not need. Not in ``setup_roles()``: that runs on every start and would
re-grant a role to someone who removed it from themselves. Backwards it grants
nothing back and takes nothing away.
"""

import os

from django.db import migrations

# (label before this migration, key)
RENAMES = [
    ("Consultant", "consultant"),
    ("Business Development Manager", "business_manager"),
    ("Beheerder", "user_admin"),
]
STAFF_ROLES = ("business_manager", "user_admin")


def _rename(apps, old, new):
    Group = apps.get_model("auth", "Group")
    source = Group.objects.filter(name=old).first()
    if source is None:
        return
    target = Group.objects.filter(name=new).first()
    if target is None:
        source.name = new
        source.save(update_fields=["name"])
        return
    target.permissions.add(*source.permissions.all())
    target.user_set.add(*source.user_set.all())
    source.delete()


def _grant_staff(apps):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("rijksauth", "User")
    emails = {e.strip().lower() for e in os.environ.get("STAFF_EMAILS", "").split(",") if e.strip()}
    if not emails:
        return
    groups = [Group.objects.get_or_create(name=name)[0] for name in STAFF_ROLES]
    for user in User.objects.all():
        if user.email and user.email.lower() in emails:
            user.groups.add(*groups)


def forwards(apps, schema_editor):
    for label, key in RENAMES:
        _rename(apps, label, key)
    _grant_staff(apps)


def backwards(apps, schema_editor):
    for label, key in RENAMES:
        _rename(apps, key, label)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("rijksauth", "0008_user_public_id"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
