"""Context processors injected into every template render."""

import urllib.parse

from django.utils import timezone

from wies.core.models import LabelCategory, Placement
from wies.core.querysets import annotate_placement_dates


def _onboarding_owner_mailto(assignment) -> str:
    """Return a mailto (address + subject, no body) for the BM of ``assignment``.

    Empty when the assignment has no owner or the owner has no email.
    """
    if not assignment.owner or not assignment.owner.email:
        return ""
    subject = urllib.parse.quote(f"Opdracht {assignment.name}")
    return f"mailto:{assignment.owner.email}?subject={subject}"


def _onboarding_assignments(colleague):
    """Return the active assignments the user is placed on, for the self-check step.

    One entry per assignment, each with its ``Assignment``, the ``services`` the
    user is placed on, and a bare ``owner_mailto``. Empty when the user has no
    active placement. Editability is left to the field-level permission rules.
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
        "onboarding_assignments": _onboarding_assignments(colleague),
    }
