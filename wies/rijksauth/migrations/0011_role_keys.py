"""Renames the three role groups to their key, so ``Group.name`` stops being a label.

What a role is called on screen lives in ``ROLE_LABELS`` (``wies/core/roles.py``).
The names are spelled out here rather than imported: a migration is frozen in time
and app code is not.

If both groups already exist (``setup_roles()`` ran with the key first), the members
and permissions of the old group are merged into the new one and the old is removed.
"""

from django.db import migrations

# (name before this migration, key)
RENAMES = [
    ("Consultant", "consultant"),
    ("Business Development Manager", "bdm"),
    ("Gebruikersbeheer", "office_assistant"),
]


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


def forwards(apps, schema_editor):
    for label, key in RENAMES:
        _rename(apps, label, key)


def backwards(apps, schema_editor):
    for label, key in RENAMES:
        _rename(apps, key, label)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("rijksauth", "0010_rename_beheerder_group"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
