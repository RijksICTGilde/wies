"""Renames the Beheerder role to Gebruikersbeheer, keeping members and permissions.

If both groups already exist (setup_roles() ran with the new name first), the
members and permissions of Beheerder are merged into Gebruikersbeheer and
Beheerder is removed.
"""

from django.db import migrations


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
    _rename(apps, "Beheerder", "Gebruikersbeheer")


def backwards(apps, schema_editor):
    _rename(apps, "Gebruikersbeheer", "Beheerder")


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("rijksauth", "0009_backfill_assignment_admin"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
