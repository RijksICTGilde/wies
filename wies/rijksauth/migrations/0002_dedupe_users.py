import logging
from collections import defaultdict

from django.db import migrations, transaction
from django.db.models.functions import Lower

logger = logging.getLogger(__name__)


def _merge_user_into_canonical(canonical, duplicate, *, colleague_model, event_model, task_model):
    """
    Repoint every FK and M2M reference from `duplicate` to `canonical`, then
    delete `duplicate`. Caller must wrap in a transaction.
    """
    # Event.user, Task.created_by — both nullable FKs, plain update.
    event_model.objects.filter(user=duplicate).update(user=canonical)
    task_model.objects.filter(created_by=duplicate).update(created_by=canonical)

    # Colleague.user is a OneToOneField. If both the canonical and duplicate
    # users have a linked colleague, the canonical's stays and the duplicate's
    # is left detached (user cleared) — the Colleague dedupe migration
    # (0003 in core) handles colleague-level dedupe.
    canonical_colleague = colleague_model.objects.filter(user=canonical).first()
    duplicate_colleague = colleague_model.objects.filter(user=duplicate).first()
    if duplicate_colleague is not None:
        if canonical_colleague is None:
            duplicate_colleague.user = canonical
            duplicate_colleague.save(update_fields=["user"])
        else:
            duplicate_colleague.user = None
            duplicate_colleague.save(update_fields=["user"])

    # M2Ms inherited from AbstractUser: groups, user_permissions.
    group_ids = list(duplicate.groups.values_list("id", flat=True))
    if group_ids:
        canonical.groups.add(*group_ids)
        duplicate.groups.clear()

    perm_ids = list(duplicate.user_permissions.values_list("id", flat=True))
    if perm_ids:
        canonical.user_permissions.add(*perm_ids)
        duplicate.user_permissions.clear()

    duplicate.delete()


def dedupe_users(user_model, colleague_model, event_model, task_model):
    """
    Merge users that share the same email (case-insensitive). The oldest by
    id is treated as canonical; all references on duplicates are repointed
    to it before the duplicates are deleted.

    Returns the number of duplicates merged.
    """
    groups = defaultdict(list)
    for user in user_model.objects.annotate(email_lower=Lower("email")).order_by("id"):
        groups[user.email_lower].append(user)

    merged = 0
    min_group_size_to_dedupe = 2
    for email_lower, members in groups.items():
        if len(members) < min_group_size_to_dedupe or not email_lower:
            continue

        with transaction.atomic():
            canonical, *duplicates = members
            for duplicate in duplicates:
                logger.info(
                    "Merging User id=%s into id=%s for email=%s",
                    duplicate.id,
                    canonical.id,
                    email_lower,
                )
                _merge_user_into_canonical(
                    canonical,
                    duplicate,
                    colleague_model=colleague_model,
                    event_model=event_model,
                    task_model=task_model,
                )
                merged += 1

    return merged


def run_dedupe(apps, schema_editor):
    user_model = apps.get_model("rijksauth", "User")
    colleague_model = apps.get_model("core", "Colleague")
    event_model = apps.get_model("core", "Event")
    task_model = apps.get_model("core", "Task")
    dedupe_users(user_model, colleague_model, event_model, task_model)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("rijksauth", "0001_initial"),
        # Colleague dedupe must run before User dedupe so the OneToOne
        # Colleague.user repointing logic here doesn't trip over
        # case-different colleague duplicates that still exist.
        ("core", "0003_dedupe_colleagues"),
    ]

    operations = [
        migrations.RunPython(run_dedupe, migrations.RunPython.noop),
    ]
