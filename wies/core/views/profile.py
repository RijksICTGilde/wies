"""Your own profile: name, theme, labels, contract periods and onboarding."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_POST

from wies.core.forms import (
    ContractPeriodForm,
    ProfileLabelsForm,
    ProfileNameForm,
)
from wies.core.inline_edit.forms import (
    build_combined_form_class,
)
from wies.core.models import (
    Assignment,
    Colleague,
    ContractPeriod,
)
from wies.core.permission_engine import Verb, has_permission
from wies.core.querysets import (
    label_categories_for_everyone,
)
from wies.core.services.assignments import (
    assignment_edit_specs,
)
from wies.core.services.events import create_event
from wies.core.services.inline_edit_save import save_edit_specs

from ._common import _resolve_panel_object
from .panels import (
    _build_aanvraag_panel_data,
    _build_assignment_panel_data,
    _build_colleague_panel_data,
    _get_colleague_assignments,
    _resolve_aanvraag_panel,
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
    from wies.core.editables.user import UserEditables  # noqa: PLC0415 — mirrors the other editable imports here

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


def _contract_block(colleague, user):
    """Context for parts/contract_periods_block.html, or None for a viewer who
    may not read the hours."""
    if not has_permission(Verb.READ, ContractPeriod(colleague=colleague), user):
        return None
    today = timezone.now().date()
    periods = colleague.contract_periods.all()
    # exists(), not bool(): the add/edit sheet builds this block before it saves
    # and renders it after, so the queryset must stay unevaluated until then.
    if periods.exists():
        empty_text = ""
    else:
        empty_text = "Niet ingevuld. De overzichten voor business managers rekenen dan zonder deze uren."
    return {
        "colleague": colleague,
        "periods": periods,
        # For the label: a running period reads "t/m heden", one still to start "Vanaf".
        "today": today,
        "can_edit": has_permission(Verb.UPDATE, ContractPeriod(colleague=colleague), user),
        "add_url": reverse("contract-period-add", args=[colleague.public_id]),
        "empty_text": empty_text,
    }


def _contract_period_event(request, period, action, before=None):
    """Logs a contract-period change on the colleague the hours belong to.

    On the colleague, not the user: the colleague outlives the user, and the
    hours of someone who has left are exactly what must stay traceable. Nothing
    displays these events yet.
    """
    after = None if action == "delete" else _contract_period_snapshot(period)
    create_event(
        object_type="Colleague",
        action="update",
        source="user",
        object_id=period.colleague_id,
        user=request.user,
        request=request,
        context={"field_name": "contract_periods", "action": action, "before": before, "after": after},
    )


def _contract_period_snapshot(period):
    return {
        "hours_per_week": period.hours_per_week,
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat() if period.end_date else None,
    }


def _contract_period_sheet(request, period, post_url, contract_block):
    """Add or edit one contract period in a sheet; a save swaps the block back in."""
    if request.method == "POST":
        before = _contract_period_snapshot(period) if period.pk else None
        form = ContractPeriodForm(request.POST, instance=period)
        # One transaction: ending the running period is undone when the new
        # period turns out invalid (see ContractPeriodForm.end_running_period).
        with transaction.atomic():
            running_before = _contract_period_snapshot(form.running) if form.running else None
            closed = form.end_running_period()
            if form.is_valid():
                form.save()
                if closed is not None:
                    _contract_period_event(request, closed, "update", running_before)
                _contract_period_event(request, period, "update" if before else "create", before)
                return render(
                    request,
                    "parts/contract_period_saved.html",
                    {"contract_block": contract_block, "announce": "Contractperiode opgeslagen"},
                )
            transaction.set_rollback(True)
        if form.running is not None:
            # The rollback undid the database write, not the end_date set on the
            # object the banner renders from.
            form.running.refresh_from_db()
    else:
        form = ContractPeriodForm(instance=period)

    form.fields["hours_per_week"].widget.attrs["autofocus"] = True
    title = "Contractperiode wijzigen" if period.pk else "Contractperiode toevoegen"
    return render(
        request,
        "parts/contract_period_sheet.html",
        {"content": form, "form_post_url": post_url, "sheet_title": title},
    )


@login_required
def contract_period_add(request, colleague_public_id):
    colleague = get_object_or_404(Colleague, public_id=colleague_public_id)
    period = ContractPeriod(colleague=colleague)
    if not has_permission(Verb.UPDATE, period, request.user):
        return HttpResponseForbidden()
    post_url = reverse("contract-period-add", args=[colleague.public_id])
    return _contract_period_sheet(request, period, post_url, _contract_block(colleague, request.user))


@login_required
def contract_period_edit(request, public_id):
    period = get_object_or_404(ContractPeriod.objects.select_related("colleague"), public_id=public_id)
    if not has_permission(Verb.UPDATE, period, request.user):
        return HttpResponseForbidden()
    post_url = reverse("contract-period-edit", args=[period.public_id])
    return _contract_period_sheet(request, period, post_url, _contract_block(period.colleague, request.user))


@login_required
def contract_period_delete(request, public_id):
    """GET asks in the shared confirm modal; POST deletes and swaps the block back
    in through the same response as a save, which also empties the mount the
    modal sits in."""
    period = get_object_or_404(ContractPeriod.objects.select_related("colleague"), public_id=public_id)
    if not has_permission(Verb.UPDATE, period, request.user):
        return HttpResponseForbidden()
    if request.method != "POST":
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Contractperiode verwijderen?",
                "dialog_supporting": (
                    f"De periode van {period.hours_per_week} uur vanaf {date_format(period.start_date, 'j b Y')} "
                    "verdwijnt uit de geschiedenis. Een periode afsluiten kan ook met een einddatum."
                ),
                "confirm_label": "Verwijder periode",
                "cancel_label": "Behoud periode",
                "form_post_url": reverse("contract-period-delete", args=[period.public_id]),
            },
        )
    colleague = period.colleague
    before = _contract_period_snapshot(period)
    period.delete()
    _contract_period_event(request, period, "delete", before)
    block = _contract_block(colleague, request.user)
    return render(
        request, "parts/contract_period_saved.html", {"contract_block": block, "announce": "Contractperiode verwijderd"}
    )


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
    panel_data = None

    if request.GET.get("aanvraag") and not request.GET.get("teamlid"):
        service = _resolve_aanvraag_panel(request, request.GET["aanvraag"])
        if service is not None:
            panel_data = _build_aanvraag_panel_data(service, request)
    elif assignment_id:
        assignment = _resolve_panel_object(request, Assignment, assignment_id)
        if assignment is not None:
            panel_data = _build_assignment_panel_data(assignment, request)
    elif colleague_id:
        panel_colleague = _resolve_panel_object(request, Colleague, colleague_id)
        if panel_colleague is not None:
            panel_data = _build_colleague_panel_data(panel_colleague, request)

    # HTMX partial responses for panel swaps
    if "HX-Request" in request.headers:
        hx_target = request.headers.get("HX-Target")
        if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container") and panel_data:
            return render(request, panel_data["panel_content_template"], {"panel_data": panel_data})

    label_categories = []
    for category in label_categories_for_everyone().order_by("name"):
        selected = list(colleague.labels.filter(category=category).order_by("name")) if colleague else []
        label_categories.append({"category": category, "labels": selected})

    assignment_list = _get_colleague_assignments(request, colleague) if colleague else []

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
    from wies.core.context_processors import _onboarding_assignments  # noqa: PLC0415 — avoids import cycle

    colleague = getattr(request.user, "colleague", None)
    for entry in _onboarding_assignments(colleague, request.user):
        if entry["assignment"].public_id == public_id:
            return entry
    return None


def _onboarding_edit_groups(request, entry, data=None):
    """Form groups for the edit screen: the assignment and each of your own roles.

    Every group gets a prefix so the role fields of multiple services don't
    collide on the same names. The Business Manager is deliberately left out:
    here they are the contact person, not something you set yourself.
    """
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle
    from wies.core.editables.service import ServiceEditables  # noqa: PLC0415

    assignment = entry["assignment"]
    groups = []

    assignment_specs = [
        (editable_set, spec, obj)
        for (editable_set, spec, obj) in assignment_edit_specs(assignment, request.user)
        if spec is not AssignmentEditables.owner
    ]
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
    for service in services:
        service_specs = [
            (ServiceEditables, spec, service)
            for spec in (ServiceEditables.skill, ServiceEditables.description, ServiceEditables.hours_per_week)
            if has_permission(Verb.UPDATE, service, request.user, spec)
        ]
        if not service_specs:
            continue
        form_cls, initial = build_combined_form_class(service_specs)
        # Without edit rights on the role the form omits its field, so surface the
        # role read-only to keep the description in context.
        skill_editable = any(spec is ServiceEditables.skill for (_, spec, _) in service_specs)
        groups.append(
            {
                # A heading only when there is more than one role; otherwise the
                # field labels speak for themselves.
                "title": None if len(services) == 1 else f"Rol: {service.skill.name if service.skill else 'onbekend'}",
                "specs": service_specs,
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
