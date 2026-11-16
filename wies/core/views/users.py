"""User management: list, create, edit, delete, CSV import and contract periods."""

from functools import cached_property

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    Q,
    Value,
)
from django.db.models.functions import Concat
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from wies.core.forms import (
    ContractPeriodForm,
    UserDeleteForm,
    UserForm,
)
from wies.core.models import (
    SUBGROEP_CATEGORY,
    Colleague,
    ContractPeriod,
    Label,
    LabelCategory,
    Suborganization,
)
from wies.core.permission_engine import Verb, has_permission
from wies.core.querysets import (
    annotate_placement_dates,
    annotate_sort_names,
)
from wies.core.roles import (
    role_label,
)
from wies.core.services.events import create_event
from wies.core.services.urls import current_page_url_on
from wies.core.services.users import (
    close_contract_periods,
    close_placements,
    contract_period_event,
    contract_period_snapshot,
    create_user,
    create_users_from_csv,
    update_user,
)

from ._common import CSV_TOO_LARGE_MSG, csv_too_large, sort_control_context
from .filters import Choice, ModelFacet, categories_with_labels, label_facets, model_choices, resolve_pk_facet
from .listing import FacetedListView, ListSearch

User = get_user_model()


class UserSearch(ListSearch):
    """The users in Beheer under the request's search and filters."""

    def scope(self):
        qs = User.objects.filter(is_superuser=False)
        if self.query:
            qs = qs.annotate(full_name=Concat("first_name", Value(" "), "last_name")).filter(
                Q(full_name__icontains=self.query)
                | Q(first_name__icontains=self.query)
                | Q(last_name__icontains=self.query)
                | Q(email__icontains=self.query)
            )
        return qs

    def build_facets(self):
        # ``Group.name`` is a key, so the database order is not the reader's A-Z.
        groups = sorted(Group.objects.all(), key=lambda group: role_label(group.name))
        return [
            # ?rol= carries Group pks: Group is Django's own model and has no public_id.
            ModelFacet(
                "rol",
                "Rol",
                resolve_pk_facet(Group, self.params.getlist("rol")),
                lookup="groups__id",
                choices=lambda: [Choice(str(group.pk), role_label(group.name), group.pk) for group in groups],
            ),
            *label_facets(
                self.resolver("labels", Label),
                categories_with_labels(LabelCategory.objects.all()),
                lookup="colleague__labels__id",
            ),
            # One onderdeel per colleague: OR within the group.
            ModelFacet(
                "onderdeel",
                "Onderdeel",
                self.resolver("onderdeel", Suborganization),
                lookup="colleague__suborganization_id",
                choices=lambda: model_choices(Suborganization.objects.all()),
            ),
        ]


class UserListView(PermissionRequiredMixin, FacetedListView):
    """User list with filtering and infinite scroll pagination."""

    permission_required = "rijksauth.view_user"
    search_class = UserSearch
    template_name = "user_admin.html"
    # Filter change: replace the result list (the sheet swaps OOB).
    results_template = "parts/user_results.html"
    rows_template = "parts/user_table_rows.html"
    filter_url_name = "admin-users"

    # ``?order=`` value -> (label, ordering); the default is the absence of the parameter.
    DEFAULT_SORT_LABEL = "Achternaam (A-Z)"
    DEFAULT_ORDERING = ("sort_last_name", "sort_first_name")
    SORT_OPTIONS = {
        "-last_name": ("Achternaam (Z-A)", ("-sort_last_name", "-sort_first_name")),
        "first_name": ("Voornaam (A-Z)", ("sort_first_name", "sort_last_name")),
        "-first_name": ("Voornaam (Z-A)", ("-sort_first_name", "-sort_last_name")),
        "-date_joined": ("Toegevoegd (nieuwste eerst)", ("-date_joined",)),
    }
    # Label categories shown on the row next to the onderdeel, by name (see SUBGROEP_CATEGORY).
    ROW_LABEL_CATEGORIES = (SUBGROEP_CATEGORY,)

    @cached_property
    def active_order(self) -> str:
        """The requested ``?order=``; empty for the default and for unknown values."""
        requested = self.request.GET.get("order", "")
        return requested if requested in self.SORT_OPTIONS else ""

    def page_source(self):
        ordering = self.SORT_OPTIONS[self.active_order][1] if self.active_order else self.DEFAULT_ORDERING
        return (
            annotate_sort_names(self.search.filtered)
            .select_related("colleague__suborganization")
            .prefetch_related("groups", "colleague__labels__category")
            .order_by(*ordering)
        )

    def row_context(self, page):
        return {"object_list": page.object_list, "row_label_categories": self.ROW_LABEL_CATEGORIES}

    def filter_context(self):
        return {**super().filter_context(), "search_field": "zoek", "search_placeholder": "Zoek op naam of email..."}

    def extra_context(self):
        return {
            **sort_control_context(
                self.active_order,
                [(value, label) for value, (label, _) in self.SORT_OPTIONS.items()],
                self.DEFAULT_SORT_LABEL,
            ),
            "primary_button": {
                "button_text": "Gebruiker toevoegen",
                "attrs": {
                    "hx-get": reverse("user-create"),
                    "hx-target": "#userFormModal",
                    "hx-push-url": "false",  # necessary because nested in htmx powered form
                },
            },
        }


def _user_list_behind_sheet(request) -> str:
    """The user list with the filters, search and order the sheet was opened over."""
    return current_page_url_on(request, reverse("admin-users"))


@permission_required("rijksauth.add_user", raise_exception=True)
def user_create(request):
    """Creates a user: GET returns the form modal, POST processes the creation."""

    form_post_url = reverse("user-create")
    modal_title = "Nieuwe gebruiker"
    element_id = "userFormModal"

    # The sheet carries the first contract period, so creating is all or nothing:
    # whoever may not keep contract hours may not create a user through it.
    if not has_permission(Verb.UPDATE, ContractPeriod(), request.user):
        return HttpResponseForbidden()

    if request.method == "GET":
        form = UserForm(editor=request.user)
        form.fields["first_name"].widget.attrs["autofocus"] = True
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Voeg gebruiker toe",
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    if request.method == "POST":
        form = UserForm(request.POST, editor=request.user)
        if form.is_valid() and _create_user_with_contract_period(request, form):
            # HTMX needs HX-Redirect to force a full page redirect.
            messages.success(
                request, f"Gebruiker {form.cleaned_data['first_name']} {form.cleaned_data['last_name']} is toegevoegd."
            )
            if "HX-Request" in request.headers:
                response = HttpResponse(status=200)
                response["HX-Redirect"] = _user_list_behind_sheet(request)
                return response
            return redirect(_user_list_behind_sheet(request))
        # Re-render with errors; HTMX keeps the modal open.
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Voeg gebruiker toe",
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    return HttpResponse(status=405)


def _create_user_with_contract_period(request, form) -> bool:
    """Creates the user and, when filled in, its first contract period.

    One transaction: a period that does not validate (the colleague may be an
    existing one with periods of its own) leaves no user behind. Returns False
    with the error on the form then.
    """
    hours = form.cleaned_data.get("contract_hours_per_week")
    with transaction.atomic():
        user = create_user(
            request.user,
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            email=form.cleaned_data["email"],
            labels=form.cleaned_data.get("labels"),
            groups=form.cleaned_data.get("groups"),
            suborganization=form.cleaned_data.get("suborganization"),
            request=request,
        )
        if hours:
            period = ContractPeriod(
                colleague=user.colleague,
                hours_per_week=hours,
                start_date=form.cleaned_data["contract_start_date"],
            )
            try:
                period.full_clean()
            except ValidationError as e:
                transaction.set_rollback(True)
                for field, errors in e.message_dict.items():
                    form.add_error(f"contract_{field}" if f"contract_{field}" in form.fields else None, errors)
                return False
            period.save()
            contract_period_event(request, period, "create")
    return True


@permission_required("rijksauth.change_user", raise_exception=True)
def user_edit(request, public_id):
    """Edits a user: GET returns the populated form modal, POST processes the update."""
    edited_user = get_object_or_404(User, public_id=public_id, is_superuser=False)
    form_post_url = reverse("user-edit", args=[edited_user.public_id])
    modal_title = "Gebruiker wijzigen"
    element_id = "userFormModal"

    # Contract periods sit on the linked colleague; a user without one has
    # nothing to hang them on and gets no block.
    colleague = getattr(edited_user, "colleague", None)
    contract_block = _contract_periods_block(colleague, request.user) if colleague else None

    if request.method == "GET":
        form = UserForm(instance=edited_user, editor=request.user)
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "contract_block": contract_block,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Opslaan",
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    if request.method == "POST":
        form = UserForm(request.POST, instance=edited_user, editor=request.user)
        if form.is_valid():
            update_user(
                updater=request.user,
                user=edited_user,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
                labels=form.cleaned_data.get("labels"),
                groups=form.cleaned_data.get("groups"),
                suborganization=form.cleaned_data.get("suborganization"),
                request=request,
            )
            # HTMX needs HX-Redirect to force a full page redirect.
            messages.success(
                request, f"Gebruiker {form.cleaned_data['first_name']} {form.cleaned_data['last_name']} is aangepast."
            )
            if "HX-Request" in request.headers:
                response = HttpResponse(status=200)
                response["HX-Redirect"] = _user_list_behind_sheet(request)
                return response
            return redirect(_user_list_behind_sheet(request))
        # Re-render with errors; HTMX keeps the modal open.
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "contract_block": contract_block,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Opslaan",
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    return HttpResponse(status=405)


# Contract periods: the block on the user edit sheet and its add/edit/delete sheets.


def _contract_periods_block(colleague, user):
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
    return _contract_period_sheet(request, period, post_url, _contract_periods_block(colleague, request.user))


@login_required
def contract_period_edit(request, public_id):
    period = get_object_or_404(ContractPeriod.objects.select_related("colleague"), public_id=public_id)
    if not has_permission(Verb.UPDATE, period, request.user):
        return HttpResponseForbidden()
    post_url = reverse("contract-period-edit", args=[period.public_id])
    return _contract_period_sheet(request, period, post_url, _contract_periods_block(period.colleague, request.user))


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
    block = _contract_periods_block(colleague, request.user)
    return render(
        request, "parts/contract_period_saved.html", {"contract_block": block, "announce": "Contractperiode verwijderd"}
    )


def _colleague_delete_overview(colleague, today) -> list[dict] | None:
    """What ends and what lapses when the user goes, for the confirm dialog.

    Measured against today, and the headings say so: the dialog cannot know the
    day the beheerder will pick, so it lists what runs now and what is still to
    start, and the field's help text says what the chosen day does with each.
    Three groups, each a heading with title/detail rows: the contract and the
    placements apart, so they do not read as one kind of thing. The colleague
    profile itself stays, with this history.
    """
    if colleague is None:
        return None
    placements = annotate_placement_dates(colleague.placements.select_related("service__assignment", "service__skill"))
    contract, placed, lapses = [], [], []
    for period in colleague.contract_periods.all():
        hours = f"{period.hours_per_week} uur per week"
        if period.start_date > today:
            lapses.append({"title": f"Contract vanaf {date_format(period.start_date, 'j b Y')}", "detail": hours})
        elif period.end_date is None or period.end_date >= today:
            contract.append({"title": hours, "detail": f"sinds {date_format(period.start_date, 'j b Y')}"})
    for placement in placements:
        start, end = placement.actual_start_date, placement.actual_end_date
        service = placement.service
        role = service.skill.name if service.skill else "Plaatsing"
        if start is not None and start > today:
            lapses.append({"title": service.assignment.name, "detail": f"{role} · vanaf {date_format(start, 'j b Y')}"})
        elif end is None or end >= today:
            placed.append({"title": service.assignment.name, "detail": role})
    groups = [
        ("Lopend contract", contract),
        ("Lopende plaatsingen", placed),
        ("Begint later", lapses),
    ]
    return [{"heading": heading, "rows": rows} for heading, rows in groups if rows]


def _placement_snapshot(placement) -> dict:
    return {
        "assignment": placement.service.assignment.name,
        "assignment_id": placement.service.assignment_id,
        "skill": placement.service.skill.name if placement.service.skill else None,
        "start_date": placement.start_date.isoformat() if placement.start_date else None,
        "end_date": placement.end_date.isoformat() if placement.end_date else None,
    }


@permission_required("rijksauth.delete_user", raise_exception=True)
def user_delete(request, public_id):
    """Deletes a user, after the confirmation modal."""
    user = get_object_or_404(User, public_id=public_id, is_superuser=False)
    colleague = getattr(user, "colleague", None)
    today = timezone.now().date()

    def render_modal(form):
        return render(
            request,
            "parts/user_delete_modal.html",
            {
                "content": form,
                "dialog_supporting": (
                    f"Weet je zeker dat je {user.first_name} {user.last_name} wilt verwijderen? "
                    "Dit is niet terug te draaien." + (" Het collegaprofiel blijft bestaan." if colleague else "")
                ),
                "delete_overview": _colleague_delete_overview(colleague, today),
                "form_post_url": reverse("user-delete", kwargs={"public_id": public_id}),
            },
        )

    if request.method == "GET":
        return render_modal(UserDeleteForm(initial={"left_on": today}, colleague=colleague) if colleague else None)
    if request.method == "POST":
        form = UserDeleteForm(request.POST, colleague=colleague) if colleague else None
        if form is not None and not form.is_valid():
            return render_modal(form)
        label_names = [label.name for label in colleague.labels.all()] if colleague else []
        # The colleague outlives the user (SET_NULL) and drops off Bezetting with
        # the user. The contract and the placements end here so the colleague
        # panel, the opdrachten and the history say when the work stopped.
        # Capture the int PK before delete() nulls it; Event.object_id keeps
        # referencing the internal id, not the public_id.
        user_pk = user.id
        # One transaction: a contract ended without the user gone, or a user
        # gone without a trace, would both be worse than the failure itself.
        with transaction.atomic():
            left_on = form.cleaned_data["left_on"] if colleague else None
            ended, dropped = close_contract_periods(colleague, left_on) if left_on else (None, [])
            placements_ended, placements_dropped = (
                close_placements(colleague, left_on, request) if left_on else ([], [])
            )
            context = {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "label_names": label_names,
                "group_names": [role_label(g.name) for g in user.groups.all()],
                "left_on": left_on.isoformat() if left_on else None,
                "contract_ended": contract_period_snapshot(ended) if ended else None,
                "contract_dropped": [contract_period_snapshot(p) for p in dropped],
                "placements_ended": [_placement_snapshot(p) for p in placements_ended],
                "placements_dropped": [_placement_snapshot(p) for p in placements_dropped],
            }
            user.delete()
            create_event(
                object_type="User",
                action="delete",
                source="user",
                object_id=user_pk,
                user=request.user,
                request=request,
                context=context,
            )
        name = f"{user.first_name} {user.last_name}".strip() or user.email
        messages.success(request, f"{name} is verwijderd.")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = _user_list_behind_sheet(request)
        return response
    return HttpResponse(status=405)


@permission_required("rijksauth.add_user", raise_exception=True)
def user_import_csv(request):
    """Imports users from a CSV file; see ``create_users_from_csv`` for the format."""
    if request.method == "GET":
        return render(request, "user_import.html")
    if request.method == "POST":
        if "csv_file" not in request.FILES:
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": ["Geen bestand geüpload. Upload een CSV-bestand."]}},
            )

        csv_file = request.FILES["csv_file"]

        if not csv_file.name.endswith(".csv"):
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": ["Ongeldig bestandstype. Upload een CSV-bestand."]}},
            )

        if csv_too_large(csv_file):
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": [CSV_TOO_LARGE_MSG]}},
            )

        try:
            csv_content = csv_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": ["Ongeldige bestandscodering. Gebruik UTF-8."]}},
            )

        result = create_users_from_csv(request.user, csv_content, request=request)

        return render(request, "user_import.html", {"result": result})
    return HttpResponse(status=405)
