import logging
from collections import defaultdict

from django.db import transaction
from django.db.models.functions import Lower

logger = logging.getLogger(__name__)


def _pick_canonical(colleagues):
    """
    Pick the canonical colleague from a duplicate group (all sharing one source).

    Tiebreakers, in order:
    1. has a linked user (only one can — User.colleague is OneToOne)
    2. lowest id
    """

    def sort_key(colleague):
        return (
            0 if colleague.user_id is not None else 1,
            colleague.id,
        )

    return min(colleagues, key=sort_key)


def _merge_into_canonical(canonical, duplicate, *, placement_model, assignment_model):
    """
    Repoint all FK and M2M references from `duplicate` to `canonical`, then
    delete `duplicate`. Caller must wrap in a transaction.
    """
    placement_model.objects.filter(colleague=duplicate).update(colleague=canonical)
    assignment_model.objects.filter(owner=duplicate).update(owner=canonical)

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

    Designed to be called from a data migration: pass historical model classes
    via `apps.get_model("core", ...)` so the function works on any migration
    state. Returns the number of duplicates merged.
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
            canonical = _pick_canonical(members)
            duplicates = [c for c in members if c.id != canonical.id]
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
