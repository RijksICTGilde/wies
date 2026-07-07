"""Context processors injected into every template render."""

import urllib.parse

from django.utils import timezone

from wies.core.models import LabelCategory, Placement
from wies.core.querysets import annotate_placement_dates


def _onboarding_owner_mailto(assignment) -> str:
    """Bare mailto for the "contact your BM" link in the onboarding step.

    Unlike the assignment page's owner mailto (which pre-fills an
    information-request body), this only sets the address and a subject — the
    user is correcting/completing their own opdracht and writes the body
    themselves, so a pre-filled "kun je me meer informatie geven?" would be off.
    """
    if not assignment.owner or not assignment.owner.email:
        return ""
    subject = urllib.parse.quote(f"Opdracht {assignment.name}")
    return f"mailto:{assignment.owner.email}?subject={subject}"


def _onboarding_assignments(colleague):
    """Assignments the user is placed on, for the onboarding self-check step.

    Returns every assignment where ``colleague`` has an active placement (not
    yet ended), matching what the profile page shows as active. Each entry
    carries the ``Assignment`` object plus the ``services`` the user is placed
    on (their rol + rolomschrijving), so the template can render ``inline_edit``
    for name/omschrijving and the service description. The field-level
    permission rules decide per field what is editable: for a placed consultant
    on a wies-sourced opdracht name/omschrijving open up; on external (OTYS)
    opdrachten everything stays read-only. Each entry also carries a bare
    ``owner_mailto`` (address + subject, no body) for the "contact your BM"
    advice on read-only fields.

    Shown to anyone with an active placement, not just consultants: someone can
    be placed on an ODI opdracht without holding the Consultant role (e.g.
    bedrijfsvoering/OR), and they should still see and check their opdracht.
    Empty when the user is not placed on anything; the wizard skips the step.
    """
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

    return list(by_assignment.values())


def onboarding(request):
    """Expose first-login onboarding state to the base template.

    ``show_onboarding`` is True for an authenticated user who has not yet
    completed or skipped the wizard. ``onboarding_label_categories`` feeds the
    profile step; ``onboarding_assignments`` feeds the consultant
    opdracht-check step.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or user.onboarding_completed_at is not None:
        return {"show_onboarding": False}

    colleague = getattr(user, "colleague", None)
    return {
        "show_onboarding": True,
        "onboarding_label_categories": list(LabelCategory.objects.all()),
        "onboarding_colleague": colleague,
        "onboarding_assignments": _onboarding_assignments(colleague),
    }
