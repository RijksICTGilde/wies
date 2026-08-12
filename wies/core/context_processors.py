"""Context processors injected into every template render."""

import urllib.parse

from django.utils import timezone

from wies.core.models import LabelCategory, Placement
from wies.core.querysets import annotate_placement_dates


def _onboarding_owner_mailto(assignment) -> str:
    """Returns a mailto (address and subject, no body) for the BM of ``assignment``."""
    if not assignment.owner or not assignment.owner.email:
        return ""
    subject = urllib.parse.quote(f"Opdracht {assignment.name}")
    return f"mailto:{assignment.owner.email}?subject={subject}"


def _onboarding_can_edit(entry, user) -> bool:
    """Returns whether the user may change anything on this assignment or their own role.

    Decides whether the check step shows a "Wijzigen" button, which opens the edit
    screen running on these same specs (see onboarding_assignment_edit).
    """
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle
    from wies.core.editables.service import ServiceEditables  # noqa: PLC0415
    from wies.core.permission_engine import Verb, has_permission  # noqa: PLC0415

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
        for spec in (ServiceEditables.skill, ServiceEditables.description)
    )


def _onboarding_assignments(colleague, user=None):
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
                "owner_mailto": _onboarding_owner_mailto(assignment),
            }
            by_assignment[assignment.id] = entry
        if placement.service not in entry["services"]:
            entry["services"].append(placement.service)

    entries = list(by_assignment.values())
    for entry in entries:
        entry["user_can_edit"] = _onboarding_can_edit(entry, user) if user is not None else False
    return entries


def onboarding(request):
    """Exposes first-login onboarding state to the base template.

    ``show_onboarding`` is True until the user finishes or skips the wizard.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or user.onboarding_completed_at is not None:
        return {"show_onboarding": False}

    colleague = getattr(user, "colleague", None)
    return {
        "show_onboarding": True,
        "onboarding_label_categories": list(LabelCategory.objects.all()),
        "onboarding_colleague": colleague,
        "onboarding_assignments": _onboarding_assignments(colleague, user),
    }
