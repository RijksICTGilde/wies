"""Your own profile: name, theme, labels and onboarding."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from wies.core.editables.service import ServiceEditables
from wies.core.editables.user import UserEditables
from wies.core.forms import (
    ProfileLabelsForm,
    ProfileNameForm,
)
from wies.core.inline_edit.forms import (
    build_combined_form_class,
)
from wies.core.models import (
    Assignment,
    Colleague,
)
from wies.core.querysets import (
    label_categories_for_everyone,
)
from wies.core.services.assignments import (
    onboarding_assignments,
    onboarding_edit_specs,
)
from wies.core.services.inline_edit_save import save_edit_specs

from ._common import resolve_panel_object
from .panels import (
    build_aanvraag_panel_data,
    build_assignment_panel_data,
    build_colleague_panel_data,
    get_colleague_assignments,
    resolve_aanvraag_panel,
)


@login_required
@require_POST
def user_theme(request):
    """Stores the display preference of the logged-in user.

    The choice lives on the Colleague, not in the browser, so it travels to every
    device and base.html can render it server-side as data-scheme — correct on
    first paint, without a flash.
    """
    theme = request.POST.get("theme", "")
    if theme not in Colleague.Theme.values:
        return HttpResponseBadRequest("Onbekende weergave")
    colleague = getattr(request.user, "colleague", None)
    if colleague is None:
        # A user without a Colleague has nowhere to store it; the screen has
        # already switched client-side, only persisting is refused.
        return HttpResponse("Geen collega om de weergave op te slaan", status=409)
    colleague.theme = theme
    colleague.save(update_fields=["theme"])
    return HttpResponse(status=204)


@login_required
def profile_name_edit(request):
    """First and last name of the logged-in user, in one sheet.

    Saving goes through each field's Editable save, so the name on the linked
    Colleague follows along exactly as it does for inline edit.
    """
    user = request.user

    if request.method == "POST":
        form = ProfileNameForm(request.POST, instance=user)
        if form.is_valid():
            UserEditables.first_name.save(user, form.cleaned_data["first_name"])
            UserEditables.last_name.save(user, form.cleaned_data["last_name"])
            messages.success(request, "Je naam is aangepast.")
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("user-profile")
            return response
    else:
        form = ProfileNameForm(instance=user)

    form.fields["first_name"].widget.attrs["autofocus"] = True

    return render(
        request,
        "parts/profile_name_sheet.html",
        {
            "content": form,
            "form_post_url": reverse("profile-name-edit"),
        },
    )


def _own_colleague_or_404(request):
    colleague = getattr(request.user, "colleague", None)
    if colleague is None:
        raise Http404("Geen collegaprofiel om te bewerken")
    return colleague


@login_required
def profile_labels_edit(request):
    """All label categories of your own profile in one sheet.

    Onboarding asks the same question with the same fields, but saves each one
    when its step is left; here they land together under one "Opslaan".
    """
    colleague = _own_colleague_or_404(request)

    categories = list(label_categories_for_everyone().order_by("name"))

    if request.method == "POST":
        form = ProfileLabelsForm(request.POST, colleague=colleague, categories=categories)
        if form.is_valid():
            form.save()
            messages.success(request, "Je labels zijn aangepast.")
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("user-profile")
            return response
    else:
        form = ProfileLabelsForm(colleague=colleague, categories=categories)

    if form.fields:
        next(iter(form.fields.values())).widget.attrs["autofocus"] = True

    return render(
        request,
        "parts/profile_labels_sheet.html",
        {
            "content": form,
            "form_post_url": reverse("profile-labels-edit"),
        },
    )


def user_profile(request):
    """User's own profile page with editable fields and full assignment history."""
    user = request.user
    colleague = getattr(user, "colleague", None)

    # Side panel handling
    colleague_id = request.GET.get("collega")
    assignment_id = request.GET.get("opdracht")
    service_id = request.GET.get("aanvraag")
    panel_data = None

    if service_id:
        service = resolve_aanvraag_panel(request, service_id)
        if service is not None:
            panel_data = build_aanvraag_panel_data(service, request)
    elif assignment_id:
        assignment = resolve_panel_object(request, Assignment, assignment_id)
        if assignment is not None:
            panel_data = build_assignment_panel_data(assignment, request)
    elif colleague_id:
        panel_colleague = resolve_panel_object(request, Colleague, colleague_id)
        if panel_colleague is not None:
            panel_data = build_colleague_panel_data(panel_colleague, request)

    # HTMX partial responses for panel swaps
    if "HX-Request" in request.headers:
        hx_target = request.headers.get("HX-Target")
        if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container") and panel_data:
            return render(request, panel_data["panel_content_template"], {"panel_data": panel_data})

    label_categories = []
    for category in label_categories_for_everyone().order_by("name"):
        selected = list(colleague.labels.filter(category=category).order_by("name")) if colleague else []
        label_categories.append({"category": category, "labels": selected})

    assignment_list = get_colleague_assignments(request, colleague) if colleague else []

    return render(
        request,
        "user_profile.html",
        {
            "colleague": colleague,
            "label_categories": label_categories,
            "assignment_list": assignment_list,
            "panel_data": panel_data,
        },
    )


@require_POST
def onboarding_complete(request):
    """Marks the first-login onboarding wizard as done (completed or skipped).

    An HTMX request gets a 204 with a ``closeOnboarding`` trigger so the dialog
    closes in place; otherwise it redirects home.
    """
    user = request.user
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = timezone.now()
        user.save(update_fields=["onboarding_completed_at"])

    if "HX-Request" in request.headers:
        response = HttpResponse(status=204)
        response["HX-Trigger"] = "closeOnboarding"
        return response
    return redirect("home")


# The onboarding edit screen builds one form over the assignment plus your own
# role(s) from the same specs as inline edit, so save and audit behaviour stay
# identical.


def _onboarding_entry(request, public_id):
    """The onboarding entry for this assignment, or None when you are not on it."""
    colleague = getattr(request.user, "colleague", None)
    for entry in onboarding_assignments(colleague, request.user):
        if entry["assignment"].public_id == public_id:
            return entry
    return None


def _onboarding_edit_groups(request, entry, data=None):
    """Form groups for the edit screen: the assignment and each of your own roles.

    Every group gets a prefix so the role fields of multiple services don't
    collide on the same names.
    """
    assignment_specs, service_specs = onboarding_edit_specs(entry, request.user)
    groups = []

    if assignment_specs:
        form_cls, initial = build_combined_form_class(assignment_specs)
        groups.append(
            {
                # No heading: the screen title already names the assignment.
                "title": None,
                "specs": assignment_specs,
                "form": form_cls(data, initial=initial, prefix="opdracht"),
            }
        )

    services = entry["services"]
    for service, specs in service_specs:
        form_cls, initial = build_combined_form_class(specs)
        # Without edit rights on the role the form omits its field, so surface the
        # role read-only to keep the description in context.
        skill_editable = any(spec is ServiceEditables.skill for (_, spec, _) in specs)
        groups.append(
            {
                # A heading only when there is more than one role; otherwise the
                # field labels speak for themselves.
                "title": None if len(services) == 1 else f"Rol: {service.skill.name if service.skill else 'onbekend'}",
                "specs": specs,
                "form": form_cls(data, initial=initial, prefix=f"rol-{service.id}"),
                # None when editable (the form renders the field); otherwise the
                # role name, or "" so the template shows its dash fallback.
                "readonly_skill": None if skill_editable else (service.skill.name if service.skill else ""),
            }
        )

    return groups


def onboarding_assignment_edit(request, public_id):
    """Edit screen for one assignment inside the onboarding wizard."""
    entry = _onboarding_entry(request, public_id)
    if entry is None:
        raise Http404("Unknown assignment")

    groups = _onboarding_edit_groups(request, entry, data=request.POST if request.method == "POST" else None)
    if not groups:
        return HttpResponseForbidden()

    if request.method == "POST" and all(group["form"].is_valid() for group in groups):
        with transaction.atomic():
            for group in groups:
                save_edit_specs(request, group["specs"], group["form"].cleaned_data)
        # After-swap: closing re-reads the step from the DOM (see onboarding.js).
        entry = _onboarding_entry(request, public_id)
        response = render(request, "parts/onboarding/onboarding_assignment_box.html", {"entry": entry})
        response["HX-Retarget"] = f"#onboarding-assignment-{public_id}"
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger-After-Swap"] = "onboardingDetailClose"
        return response

    return render(
        request,
        "parts/onboarding/onboarding_assignment_form.html",
        {"entry": entry, "groups": groups},
    )
