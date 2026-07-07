import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def scrub_legacy_organizations_events(apps, schema_editor):
    """Rewrite legacy ``organizations`` audit events whose
    ``old_value``/``new_value`` is a Python repr-string into the empty-list
    shape ``[]``, so the timeline renderer (which now expects list-of-dicts)
    no longer crashes.

    Between the PR #341 release (2026-05-20) and the PR #369 release
    (2026-06-10), ``_emit_inline_edit_audit_event`` stored
    ``str(old_value or "")``, producing strings like
    ``"[{'organization': <OrganizationUnit: ...>, 'role': 'PRIMARY'}, ...]"``
    for organizations edits. That repr is not reliably parseable, so we
    drop the per-row delta and leave the timeline showing "geen"; the
    event itself (timestamp + user) is preserved.

    Defensive: only rewrites rows whose shape exactly matches the legacy
    signature (Assignment + field_name=organizations + str in old or new).
    Anything else is left alone.
    """
    Event = apps.get_model("core", "Event")

    qs = Event.objects.filter(
        object_type="Assignment",
        action="update",
        context__field_name="organizations",
    )
    scrubbed = 0
    for event in qs.iterator():
        old = event.context.get("old_value")
        new = event.context.get("new_value")
        if not isinstance(old, str) and not isinstance(new, str):
            continue
        event.context["old_value"] = []
        event.context["new_value"] = []
        event.save(update_fields=["context"])
        scrubbed += 1
        logger.info("Scrubbed legacy organizations Event id=%s", event.id)

    logger.info("scrub_legacy_organizations_events: rewrote %s rows", scrubbed)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_alter_placement_period_source_and_more"),
    ]

    operations = [
        migrations.RunPython(scrub_legacy_organizations_events, migrations.RunPython.noop),
    ]
