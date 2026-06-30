"""Context processors injected into every template render."""

from wies.core.models import LabelCategory


def onboarding(request):
    """Expose first-login onboarding state to the base template.

    ``show_onboarding`` is True for an authenticated user who has not yet
    completed or skipped the wizard. ``onboarding_label_categories`` feeds
    the profile step (same label categories as the profile page).
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or user.onboarding_completed_at is not None:
        return {"show_onboarding": False}

    return {
        "show_onboarding": True,
        "onboarding_label_categories": list(LabelCategory.objects.all()),
        "onboarding_colleague": getattr(user, "colleague", None),
    }
