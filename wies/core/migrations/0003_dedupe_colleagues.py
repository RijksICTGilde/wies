import logging
from collections import defaultdict

from django.conf import settings
from django.db import migrations, transaction
from django.db.models.functions import Lower

logger = logging.getLogger(__name__)


def _merge_into_canonical(canonical, duplicate, *, placement_model, assignment_model):
    """
    Repoint all FK and M2M references from `duplicate` to `canonical`, then
    delete `duplicate`. Caller must wrap in a transaction.
    """
    placement_model.objects.filter(colleague=duplicate).update(colleague=canonical)
    assignment_model.objects.filter(owner=duplicate).update(owner=canonical)

    # If the canonical has no linked user but the duplicate does, hand the
    # user over so it isn't lost when the duplicate is deleted. user is a
    # OneToOneField, so clear the duplicate before setting it on the canonical.
    if canonical.user_id is None and duplicate.user_id is not None:
        user = duplicate.user
        duplicate.user = None
        duplicate.save(update_fields=["user"])
        canonical.user = user
        canonical.save(update_fields=["user"])

    # M2M labels: union onto canonical, then clear duplicate's set so deleting
    # the duplicate doesn't remove labels that should stay on the canonical.
    label_ids = list(duplicate.labels.values_list("id", flat=True))
    if label_ids:
        canonical.labels.add(*label_ids)
        duplicate.labels.clear()

    duplicate.delete()


def dedupe_colleagues(colleague_model, placement_model, assignment_model):
    """
    Merge colleagues that share the same email (case-insensitive) AND source.
    Cross-source duplicates (e.g. a wies and an otys_iir colleague for the same
    person) are left alone — they're treated as legitimately distinct records.

    Returns the number of duplicates merged.
    """
    groups = defaultdict(list)
    for colleague in colleague_model.objects.annotate(email_lower=Lower("email")).order_by("id"):
        groups[(colleague.email_lower, colleague.source)].append(colleague)

    merged = 0
    min_group_size_to_dedupe = 2
    for (email_lower, source), members in groups.items():
        if len(members) < min_group_size_to_dedupe or not email_lower:
            continue

        with transaction.atomic():
            canonical, *duplicates = members
            for duplicate in duplicates:
                logger.info(
                    "Merging Colleague id=%s into id=%s for source=%s email=%s",
                    duplicate.id,
                    canonical.id,
                    source,
                    email_lower,
                )
                _merge_into_canonical(
                    canonical,
                    duplicate,
                    placement_model=placement_model,
                    assignment_model=assignment_model,
                )
                merged += 1

    return merged


def run_dedupe(apps, schema_editor):
    colleague_model = apps.get_model("core", "Colleague")
    placement_model = apps.get_model("core", "Placement")
    assignment_model = apps.get_model("core", "Assignment")
    dedupe_colleagues(colleague_model, placement_model, assignment_model)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_modify_event"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(run_dedupe, migrations.RunPython.noop),
    ]
