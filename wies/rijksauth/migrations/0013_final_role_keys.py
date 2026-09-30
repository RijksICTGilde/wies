"""Renames two role keys to the words the screens use.

0011 landed ``bdm`` and ``office_assistant``; the roles are now called Business
Manager and Gebruikersbeheer, and a key that says something else makes the code
read against the product. Both keys were introduced by this same unreleased
change, so nothing outside it has ever matched on them.

The names are spelled out rather than imported: a migration is frozen in time and
app code is not. If both groups already exist (``setup_roles()`` ran with the new
key first), the members and permissions of the old group are merged into the new
one and the old is removed.
"""

from django.db import migrations

# (key before this migration, key after)
RENAMES = [
    ("bdm", "business_manager"),
    ("office_assistant", "user_admin"),
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
    for old, new in RENAMES:
        _rename(apps, old, new)


def backwards(apps, schema_editor):
    for old, new in RENAMES:
        _rename(apps, new, old)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("rijksauth", "0012_drop_assignment_admin_group"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
