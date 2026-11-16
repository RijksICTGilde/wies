"""Context processors injected into every template render."""

from wies.core.querysets import label_categories_for_everyone
from wies.core.services.assignments import onboarding_assignments


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
        "onboarding_label_categories": list(label_categories_for_everyone()),
        "onboarding_colleague": colleague,
        "onboarding_assignments": onboarding_assignments(colleague, user),
    }
