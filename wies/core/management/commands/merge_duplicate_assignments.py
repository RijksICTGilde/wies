"""Merge duplicate assignments that share the same name and owner.

Usage:
    python manage.py merge_duplicate_assignments           # dry-run, shows plan
    python manage.py merge_duplicate_assignments --apply   # executes the merge
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from wies.core.models import Assignment, AssignmentOrganizationUnit

logger = logging.getLogger(__name__)


def find_duplicate_groups():
    """Find assignments that share the same name, owner, and primary organization."""
    # Annotate each assignment with its primary org so we can group on it.
    qs = Assignment.objects.filter(
        organization_relations__role="PRIMARY",
    ).values(
        "name", "owner", "organization_relations__organization",
    ).annotate(
        count=Count("id"),
    ).filter(
        count__gt=1,
    ).order_by("name")

    groups = []
    for dupe in qs:
        assignments = (
            Assignment.objects.filter(
                name=dupe["name"],
                owner=dupe["owner"],
                organization_relations__role="PRIMARY",
                organization_relations__organization=dupe["organization_relations__organization"],
            )
            .select_related("owner")
            .prefetch_related(
                "services__placements__colleague",
                "services__skill",
                "organization_relations__organization",
            )
            .order_by("id")
        )
        group = list(assignments)
        # Avoid adding the same group twice (can happen with multiple orgs).
        if group and not any(g[0].id == group[0].id for g in groups):
            groups.append(group)
    return groups


def describe_assignment(assignment):
    """Human-readable summary of an assignment and its services/placements."""
    lines = [
        f"  #{assignment.id} - {assignment.name}",
        f"    owner: {assignment.owner}",
        f"    period: {assignment.start_date} - {assignment.end_date}",
        f"    source: {assignment.source} (id={assignment.source_id!r})",
    ]

    lines.extend(
        f"    org: {org_rel.organization.name} ({org_rel.role})" for org_rel in assignment.organization_relations.all()
    )

    services = assignment.services.all()
    if not services:
        lines.append("    (no services)")
    for svc in services:
        placements = svc.placements.all()
        if placements:
            lines.extend(
                f"    service #{svc.id}: {svc.skill or '?'} - {pl.colleague.name} (placement #{pl.id})"
                for pl in placements
            )
        else:
            lines.append(f"    service #{svc.id}: {svc.skill or '?'} - (vacant)")
    return "\n".join(lines)


def _merge_period(target, assignments, actions, *, dry_run):
    """Widen the date range to cover all assignments."""
    all_starts = [a.start_date for a in assignments if a.start_date]
    all_ends = [a.end_date for a in assignments if a.end_date]
    new_start = min(all_starts) if all_starts else None
    new_end = max(all_ends) if all_ends else None

    if new_start != target.start_date or new_end != target.end_date:
        actions.append(f"  Update period: {target.start_date}-{target.end_date} -> {new_start}-{new_end}")
        if not dry_run:
            target.start_date = new_start
            target.end_date = new_end
            target.save(update_fields=["start_date", "end_date"])


def _merge_extra_info(target, assignments, actions, *, dry_run):
    """Merge extra_info, deduplicating while preserving order."""
    extra_infos = [a.extra_info.strip() for a in assignments if a.extra_info.strip()]
    combined = "\n\n".join(dict.fromkeys(extra_infos))
    if combined != target.extra_info.strip():
        actions.append(f"  Merge extra_info from {len(extra_infos)} assignments")
        if not dry_run:
            target.extra_info = combined
            target.save(update_fields=["extra_info"])


def _merge_orgs(target, dupe, actions, target_orgs, has_primary, *, dry_run):
    """Consolidate organization relations from a duplicate onto the target."""
    for org_rel in dupe.organization_relations.all():
        key = (org_rel.organization_id, org_rel.role)
        if key in target_orgs:
            actions.append(f"  Skip org {org_rel.organization.name} ({org_rel.role}) - already on target")
        elif org_rel.role == "PRIMARY" and has_primary:
            new_key = (org_rel.organization_id, "INVOLVED")
            if new_key not in target_orgs:
                actions.append(
                    f"  Move org {org_rel.organization.name} as INVOLVED"
                    f" (was PRIMARY on #{dupe.id}, target already has PRIMARY)"
                )
                if not dry_run:
                    org_rel.assignment = target
                    org_rel.role = "INVOLVED"
                    org_rel.save(update_fields=["assignment", "role"])
                target_orgs.add(new_key)
            else:
                actions.append(f"  Skip org {org_rel.organization.name} - already INVOLVED on target")
        else:
            actions.append(f"  Move org {org_rel.organization.name} ({org_rel.role}) from #{dupe.id} -> #{target.id}")
            if not dry_run:
                org_rel.assignment = target
                org_rel.save(update_fields=["assignment"])
            target_orgs.add(key)
            if org_rel.role == "PRIMARY":
                has_primary = True
    return has_primary


def merge_group(assignments, *, dry_run=True):
    """Merge a group of duplicate assignments into the first (oldest) one.

    Strategy:
    - Keep the assignment with the lowest ID as the target.
    - Move all services (and their placements) from duplicates to the target.
    - Consolidate organization relations (skip duplicates, respect PRIMARY uniqueness).
    - Pick the widest date range across all assignments.
    - Preserve extra_info by appending if the duplicate has additional text.
    - Delete the now-empty duplicate assignments.
    """
    target = assignments[0]
    duplicates = assignments[1:]
    actions = []

    _merge_period(target, assignments, actions, dry_run=dry_run)
    _merge_extra_info(target, assignments, actions, dry_run=dry_run)

    target_orgs = set(
        AssignmentOrganizationUnit.objects.filter(assignment=target).values_list("organization_id", "role")
    )
    has_primary = any(role == "PRIMARY" for _, role in target_orgs)

    for dupe in duplicates:
        # Move services. For services that inherit their period from the
        # assignment, pin the original assignment's dates so the effective
        # period doesn't change when they move to the (possibly wider) target.
        services = list(dupe.services.all())
        for svc in services:
            actions.append(
                f"  Move service #{svc.id} ({svc.skill or '?'}) from assignment #{dupe.id} -> #{target.id}"
            )
            if svc.period_source == "ASSIGNMENT" and (dupe.start_date or dupe.end_date):
                actions.append(
                    f"    Pin service period to {dupe.start_date}-{dupe.end_date}"
                    " (was inheriting from assignment)"
                )
                if not dry_run:
                    svc.period_source = "SERVICE"
                    svc.specific_start_date = dupe.start_date
                    svc.specific_end_date = dupe.end_date
                    svc.assignment = target
                    svc.save(update_fields=[
                        "assignment", "period_source",
                        "specific_start_date", "specific_end_date",
                    ])
            elif not dry_run:
                svc.assignment = target
                svc.save(update_fields=["assignment"])

        has_primary = _merge_orgs(target, dupe, actions, target_orgs, has_primary, dry_run=dry_run)

        # Delete the empty duplicate.
        actions.append(f"  Delete empty assignment #{dupe.id}")
        if not dry_run:
            remaining = dupe.services.count()
            if remaining > 0:
                msg = (
                    f"Assignment #{dupe.id} still has {remaining} services after merge! Aborting to prevent data loss."
                )
                raise RuntimeError(msg)
            dupe.organization_relations.all().delete()
            dupe.delete()

    return actions


class Command(BaseCommand):
    help = "Merge duplicate assignments that share the same name and owner."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually perform the merge. Without this flag, only shows the plan.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        groups = find_duplicate_groups()

        if not groups:
            self.stdout.write(self.style.SUCCESS("No duplicate assignments found."))
            return

        self.stdout.write(f"Found {len(groups)} group(s) of duplicate assignments:\n")

        for group in groups:
            self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
            self.stdout.write(
                self.style.WARNING(f'Group: "{group[0].name}" (owner: {group[0].owner}) - {len(group)} assignments')
            )
            self.stdout.write(f"Target (keep): #{group[0].id}")
            self.stdout.write("")

            for assignment in group:
                self.stdout.write(describe_assignment(assignment))
                self.stdout.write("")

        if not apply:
            self.stdout.write(self.style.NOTICE("\nDry run - showing merge plan:\n"))

            for group in groups:
                self.stdout.write(self.style.WARNING(f'Group: "{group[0].name}"'))
                actions = merge_group(group, dry_run=True)
                for action in actions:
                    self.stdout.write(action)
                self.stdout.write("")

            self.stdout.write(self.style.NOTICE("Run with --apply to execute the merge."))
            return

        # Apply mode.
        self.stdout.write(self.style.WARNING("\nApplying merge...\n"))

        with transaction.atomic():
            for group in groups:
                self.stdout.write(self.style.WARNING(f'Merging: "{group[0].name}"'))
                actions = merge_group(group, dry_run=False)
                for action in actions:
                    self.stdout.write(action)
                self.stdout.write("")

        self.stdout.write(self.style.SUCCESS(f"Done. Merged {len(groups)} group(s) of duplicate assignments."))
