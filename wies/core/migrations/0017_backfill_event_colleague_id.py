from collections import defaultdict

from django.db import migrations


def backfill_colleague_id(apps, schema_editor):
    """Give the team rows in existing audit events the id of the colleague they name.

    The timeline decides on that id who may see a row, and no longer on the name.
    A frozen name that belongs to exactly one colleague gets that colleague's id.
    A name nobody carries any more (a rename, a deleted colleague) or that
    several colleagues share stays without one: guessing would show the row to
    the wrong person, so it remains hidden from everyone but the Business
    Managers.
    """
    Colleague = apps.get_model("core", "Colleague")
    Event = apps.get_model("core", "Event")

    ids_by_name: dict[str, list[int]] = defaultdict(list)
    for colleague_id, name in Colleague.objects.values_list("id", "name"):
        ids_by_name[name].append(colleague_id)

    events = Event.objects.filter(object_type="Assignment", action="update", context__field_name="services")
    for event in events.iterator():
        changed = False
        for change in event.context.get("changes") or []:
            for side in ("old", "new"):
                row = change.get(side)
                if not isinstance(row, dict) or row.get("colleague_id") is not None:
                    continue
                matches = ids_by_name.get(row.get("colleague_name"), [])
                if len(matches) == 1:
                    row["colleague_id"] = matches[0]
                    changed = True
        if changed:
            Event.objects.filter(pk=event.pk).update(context=event.context)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_service_description_optional"),
    ]

    operations = [
        migrations.RunPython(backfill_colleague_id, migrations.RunPython.noop),
    ]
