from collections import defaultdict

from django.db import migrations


def _colleague_id_for(row, colleagues_by_name, event_timestamp) -> int | None:
    """
    Returns the id to freeze on one snapshot row, or None to leave it as it is.
    Is user joined after event, it is set to None
    """
    if not isinstance(row, dict) or row.get("colleague_id") is not None:
        return None
    matches = colleagues_by_name.get(row.get("colleague_name"), [])
    if len(matches) != 1:
        return None
    colleague_id, date_joined = matches[0]
    if date_joined is not None and date_joined > event_timestamp:
        return None
    return colleague_id


def backfill_colleague_id(apps, schema_editor):
    """Give the team rows in existing audit events the id of the colleague they name."""
    Colleague = apps.get_model("core", "Colleague")
    Event = apps.get_model("core", "Event")

    colleagues_by_name: dict[str, list[tuple]] = defaultdict(list)
    for colleague_id, name, date_joined in Colleague.objects.values_list("id", "name", "user__date_joined"):
        colleagues_by_name[name].append((colleague_id, date_joined))

    events = Event.objects.filter(object_type="Assignment", action="update", context__field_name="services")
    for event in events.iterator():
        changes = event.context.get("changes")
        if not isinstance(changes, list):
            continue
        changed = False
        for change in changes:
            if not isinstance(change, dict):
                continue
            for side in ("old", "new"):
                row = change.get(side)
                colleague_id = _colleague_id_for(row, colleagues_by_name, event.timestamp)
                if colleague_id is not None:
                    row["colleague_id"] = colleague_id
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
