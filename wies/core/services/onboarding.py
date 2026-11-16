"""The onboarding self-check: the assignments a new user is placed on, and what they may change there."""

import urllib.parse

from django.utils import timezone

from wies.core.editables.assignment import AssignmentEditables
from wies.core.editables.service import ServiceEditables
from wies.core.models import Placement
from wies.core.permission_engine import Verb, has_permission
from wies.core.querysets import annotate_placement_dates


def onboarding_owner_mailto(assignment) -> str:
    """Returns a mailto (address and subject, no body) for the BM of ``assignment``."""
    if not assignment.owner or not assignment.owner.email:
        return ""
    subject = urllib.parse.quote(f"Opdracht {assignment.name}")
    return f"mailto:{assignment.owner.email}?subject={subject}"


def onboarding_can_edit(entry, user) -> bool:
    """Returns whether the user may change anything on this assignment or their own role.

    Decides whether the check step shows a "Wijzigen" button, which opens the edit
    screen running on these same specs (see onboarding_assignment_edit).
    """
    assignment = entry["assignment"]
    assignment_specs = (
        AssignmentEditables.name,
        AssignmentEditables.extra_info,
        AssignmentEditables.organizations,
        AssignmentEditables.period,
    )
    if any(has_permission(Verb.UPDATE, assignment, user, spec) for spec in assignment_specs):
        return True
    return any(
        has_permission(Verb.UPDATE, service, user, spec)
        for service in entry["services"]
        for spec in (ServiceEditables.skill, ServiceEditables.description, ServiceEditables.hours_per_week)
    )


def onboarding_assignments(colleague, user=None):
    """Returns the active assignments the user is placed on, for the self-check step."""
    if colleague is None:
        return []

    today = timezone.now().date()

    placements = annotate_placement_dates(
        Placement.objects.filter(colleague=colleague).select_related("service__assignment", "service__skill")
    )

    by_assignment: dict[int, dict] = {}
    for placement in placements:
        assignment = placement.service.assignment
        end_date = placement.actual_end_date
        if end_date is not None and today > end_date:
            continue
        entry = by_assignment.get(assignment.id)
        if entry is None:
            entry = {
                "assignment": assignment,
                "services": [],
                "owner_mailto": onboarding_owner_mailto(assignment),
            }
            by_assignment[assignment.id] = entry
        if placement.service not in entry["services"]:
            entry["services"].append(placement.service)

    entries = list(by_assignment.values())
    for entry in entries:
        entry["user_can_edit"] = onboarding_can_edit(entry, user) if user is not None else False
    return entries
