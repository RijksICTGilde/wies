"""Context processors injected into every template render."""

from django.utils import timezone

from wies.core.editables.assignment import _owner_display_context
from wies.core.models import Placement
from wies.core.querysets import annotate_placement_dates


def _onboarding_assignments(request, colleague):
    """Assignments the consultant is placed on, for the onboarding self-check step.

    Returns wies-sourced assignments where ``colleague`` has an active placement
    (not yet ended). Each entry carries the ``Assignment`` object plus the
    ``services`` the consultant is placed on (their rol + rolomschrijving) — so
    the template can render ``inline_edit`` for name/omschrijving and the
    service description, which the field-level permission rules open up for a
    placed consultant — plus the owner (Business Manager) name and a prefilled
    mailto for the "contact your BM" advice when a field is read-only.

    The step is for consultants only: Beheerders and BDM's don't get the
    "check your opdracht + mail your BM" flow (a BDM often *is* the BM). Empty
    when the user is not a Consultant or not placed on anything; the wizard
    skips the step in that case.
    """
    if colleague is None or not request.user.groups.filter(name="Consultant").exists():
        return []

    today = timezone.now().date()

    placements = annotate_placement_dates(
        Placement.objects.filter(colleague=colleague).select_related("service__assignment", "service__skill")
    )

    by_assignment: dict[int, dict] = {}
    for placement in placements:
        assignment = placement.service.assignment
        if assignment.source not in ("wies", ""):
            continue
        end_date = placement.actual_end_date
        if end_date is not None and today > end_date:
            continue
        entry = by_assignment.get(assignment.id)
        if entry is None:
            entry = {"assignment": assignment, "services": [], **_owner_display_context(assignment, request)}
            by_assignment[assignment.id] = entry
        if placement.service not in entry["services"]:
            entry["services"].append(placement.service)

    return list(by_assignment.values())


def onboarding(request):
    """Expose first-login onboarding state to the base template.

    ``show_onboarding`` is True for an authenticated user who has not yet
    completed or skipped the wizard. ``onboarding_assignments`` feeds the
    consultant opdracht-check step.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or user.onboarding_completed_at is not None:
        return {"show_onboarding": False}

    colleague = getattr(user, "colleague", None)
    return {
        "show_onboarding": True,
        "onboarding_assignments": _onboarding_assignments(request, colleague),
    }
