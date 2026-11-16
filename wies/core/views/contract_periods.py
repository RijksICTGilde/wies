"""A colleague's contract periods: the block on the profile and user edit, and its add/edit/delete sheets."""

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from wies.core.forms import ContractPeriodForm
from wies.core.models import Colleague, ContractPeriod
from wies.core.permission_engine import Verb, has_permission
from wies.core.services.contract_periods import contract_period_event, contract_period_snapshot


def contract_periods_block(colleague, user):
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


def _contract_period_sheet(request, period, post_url, contract_block):
    """Add or edit one contract period in a sheet; a save swaps the block back in."""
    if request.method == "POST":
        before = contract_period_snapshot(period) if period.pk else None
        form = ContractPeriodForm(request.POST, instance=period)
        # One transaction: ending the running period is undone when the new
        # period turns out invalid (see ContractPeriodForm.end_running_period).
        with transaction.atomic():
            running_before = contract_period_snapshot(form.running) if form.running else None
            closed = form.end_running_period()
            if form.is_valid():
                form.save()
                if closed is not None:
                    contract_period_event(request, closed, "update", running_before)
                contract_period_event(request, period, "update" if before else "create", before)
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
    return _contract_period_sheet(request, period, post_url, contract_periods_block(colleague, request.user))


@login_required
def contract_period_edit(request, public_id):
    period = get_object_or_404(ContractPeriod.objects.select_related("colleague"), public_id=public_id)
    if not has_permission(Verb.UPDATE, period, request.user):
        return HttpResponseForbidden()
    post_url = reverse("contract-period-edit", args=[period.public_id])
    return _contract_period_sheet(request, period, post_url, contract_periods_block(period.colleague, request.user))


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
    before = contract_period_snapshot(period)
    period.delete()
    contract_period_event(request, period, "delete", before)
    block = contract_periods_block(colleague, request.user)
    return render(
        request, "parts/contract_period_saved.html", {"contract_block": block, "announce": "Contractperiode verwijderd"}
    )
