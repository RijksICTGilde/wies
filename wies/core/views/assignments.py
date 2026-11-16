"""Opdrachten: list, create, edit, delete, team members and CSV import."""

import json
from collections import Counter
from datetime import date
from functools import cached_property
from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    F,
    IntegerField,
    Prefetch,
    Q,
    Value,
)
from django.http import Http404, HttpResponse, HttpResponseForbidden, QueryDict
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from wies.core.editables.assignment import AssignmentEditables, skill_choices, visible_service_or_404
from wies.core.forms import ServiceForm
from wies.core.inline_edit.forms import (
    build_combined_form_class,
)
from wies.core.models import (
    Assignment,
    OrganizationUnit,
    Service,
    Skill,
)
from wies.core.permission_engine import Verb, has_permission
from wies.core.querysets import count_distinct
from wies.core.services.aanvragen import (
    AanvraagCard,
    aanvraag_card,
    assignments_without_aanvraag,
    filter_on_standplaatsen,
    known_standplaatsen,
    opdracht_without_aanvraag_card,
    open_aanvragen,
    standplaats_key,
    standplaats_labels,
)
from wies.core.services.assignments import (
    assignment_create_specs,
    assignment_edit_specs,
    create_assignment_from_specs,
    member_audit_event,
    save_service_from_form,
)
from wies.core.services.events import create_event
from wies.core.services.inline_edit_save import save_edit_specs
from wies.core.services.placements import (
    create_assignments_from_csv,
)
from wies.core.services.urls import safe_return_path, url_replacing_param

from ._common import (
    CSV_TOO_LARGE_MSG,
    build_panel_url,
    csv_too_large,
    page_url_behind_panel,
)
from .filters import (
    Choice,
    Filter,
    OrgFilter,
    finalize_filter_groups,
    model_choices,
    model_filter,
    select_multi_group,
)
from .listing import FacetedListView, ListSearch
from .panels import (
    assignment_create_button,
    build_assignment_create_panel_data,
    build_assignment_edit_panel_data,
    build_assignment_member_panel_data,
)


class AssignmentSearch(ListSearch):
    """The Aanvragen cards: one per open role nobody fills yet, and one per
    opdracht that has no role at all yet.

    The facets narrow the roles (``Service``). The opdrachten without a role
    run alongside under the same search and opdrachtgever filter; a role,
    standplaats or date asks about an aanvraag, which they do not have, so any
    of those leaves them out.
    """

    # Filters go through subqueries (the opdrachtgever via the opdracht, the
    # search likewise), so no facet repeats a role.
    distinct = False

    @cached_property
    def today(self) -> date:
        return timezone.now().date()

    def _assignments_matching_search(self):
        # A subquery: joined directly, an opdracht with two matching
        # opdrachtgevers would give each card twice.
        return Assignment.objects.filter(
            Q(name__icontains=self.query)
            | Q(extra_info__icontains=self.query)
            | Q(organizations__name__icontains=self.query)
            | Q(organizations__label__icontains=self.query)
            | Q(organizations__abbreviations__icontains=self.query)
        )

    @cached_property
    def scope(self):
        qs = open_aanvragen(self.excluded_org_ids)
        if self.query:
            qs = qs.filter(
                Q(skill__name__icontains=self.query)
                | Q(request_description__icontains=self.query)
                | Q(location__icontains=self.query)
                | Q(assignment__in=self._assignments_matching_search())
            )
        return qs

    # The filters

    @cached_property
    def org(self):
        return OrgFilter(
            self.resolver,
            self.params,
            # Through the opdracht, for the same reason as the search above.
            apply_ids=lambda qs, ids: qs.filter(assignment__in=Assignment.objects.filter(organizations__id__in=ids)),
        )

    @cached_property
    def rol(self):
        return model_filter("rol", self.resolver("rol", Skill), "skill_id")

    @cached_property
    def locations(self) -> dict[str, str]:
        """Every standplaats of an open aanvraag, by its key."""
        return standplaats_labels(open_aanvragen(self.excluded_org_ids))

    @cached_property
    def standplaats(self):
        # An unknown standplaats is dropped rather than emptying the list without a chip.
        keys = known_standplaatsen(self.params.getlist("standplaats"), self.locations)
        return Filter(
            "standplaats", active=bool(keys), narrow=lambda qs: filter_on_standplaatsen(qs, keys), values=keys
        )

    @cached_property
    def beschikbaar_vanaf(self):
        """An aanvraag that starts per direct, has no start or has already
        started can be filled any day, so it stays; one that starts later has to
        start on or after the chosen date. Either way it must still run on that
        date. An unparsable date filters nothing; the chip shows the date itself."""
        try:
            vanaf = date.fromisoformat(self.params.get("beschikbaar_vanaf", ""))
        except ValueError:
            return Filter("beschikbaar_vanaf", active=False, narrow=lambda qs: qs)
        return Filter(
            "beschikbaar_vanaf",
            active=True,
            narrow=lambda qs: qs.filter(
                Q(starts_immediately=True)
                | Q(effective_start_date__isnull=True)
                | Q(effective_start_date__lte=self.today)
                | Q(effective_start_date__gte=vanaf),
                Q(effective_end_date__isnull=True) | Q(effective_end_date__gte=vanaf),
            ),
            values=vanaf,
        )

    def filters(self):
        return [self.org, self.rol, self.standplaats, self.beschikbaar_vanaf]

    # The sidebar

    @cached_property
    def filter_groups(self):
        return finalize_filter_groups(
            [
                self.org.group(self.org_counts()),
                # Counts aanvragen, so two for the same role on one opdracht count 2.
                select_multi_group(
                    "rol",
                    "Rol",
                    model_choices(Skill.objects.order_by("name")),
                    self.rol.values,
                    self.count("rol", "skill_id"),
                ),
                select_multi_group(
                    "standplaats",
                    "Standplaats",
                    [Choice(key, label, key) for key, label in self.locations.items()],
                    self.standplaats.values,
                    Counter(
                        standplaats_key(location)
                        for location in self.filtered(skip="standplaats").values_list("location", flat=True)
                    ),
                ),
                {"type": "date", "name": "beschikbaar_vanaf", "label": "Beschikbaar vanaf"},
            ]
        )

    def assignments_without_aanvraag(self, *, filter_on_org: bool = True):
        """The opdrachten without a role, under the same search and opdrachtgever filter."""
        if self.rol.active or self.standplaats.active or self.beschikbaar_vanaf.active:
            return Assignment.objects.none()
        qs = assignments_without_aanvraag(self.excluded_org_ids)
        if self.query:
            qs = qs.filter(pk__in=self._assignments_matching_search())
        if filter_on_org and self.org.active:
            qs = qs.filter(pk__in=Assignment.objects.filter(organizations__id__in=self.org.matching_ids))
        return qs

    def org_counts(self) -> Counter:
        """Cards per opdrachtgever under every filter but the opdrachtgever's:
        the roles and the opdrachten without one together."""
        return count_distinct(self.filtered(skip="org"), "assignment__organizations__id") + count_distinct(
            self.assignments_without_aanvraag(filter_on_org=False), "organizations__id"
        )

    @cached_property
    def cards(self):
        """(created, opdracht id, aanvraag id) per card, newest opdracht first;
        the aanvraag id is None on an opdracht without one. A union, so paging
        and counting stay in the database."""
        columns = ("card_created", "card_assignment", "card_service")
        aanvragen = (
            self.filtered()
            .annotate(
                card_created=F("assignment__created_at"), card_assignment=F("assignment_id"), card_service=F("id")
            )
            .values_list(*columns)
        )
        without_aanvraag = (
            self.assignments_without_aanvraag()
            .annotate(
                card_created=F("created_at"),
                card_assignment=F("id"),
                card_service=Value(None, output_field=IntegerField()),
            )
            .values_list(*columns)
        )
        return aanvragen.union(without_aanvraag, all=True).order_by(
            F("card_created").desc(nulls_last=True), "card_assignment", "card_service"
        )


class AssignmentListView(FacetedListView):
    """Aanvragen as cards. Infinite scroll pagination."""

    search_class = AssignmentSearch
    template_name = "assignments.html"
    results_template = "parts/filter_and_card_container_assignments.html"
    rows_template = "parts/aanvraag_card_rows.html"
    filter_url_name = "assignment-list"
    side_panel = True
    # ?nieuwe-opdracht opens the empty create form on the list.
    allow_create = True

    def page_source(self):
        return self.search.cards

    def rows(self, page):
        return {"object_list": self._cards(page.object_list)}

    def _cards(self, rows) -> list[AanvraagCard]:
        # The card shows the first opdrachtgever; ordered on pk, as
        # organizations.first() would pick it.
        by_pk = OrganizationUnit.objects.order_by("pk")
        services = (
            Service.objects.select_related("assignment", "skill")
            .prefetch_related(Prefetch("assignment__organizations", queryset=by_pk, to_attr="organizations_by_pk"))
            .in_bulk([service_id for _, _, service_id in rows if service_id])
        )
        assignments = Assignment.objects.prefetch_related(
            Prefetch("organizations", queryset=by_pk, to_attr="organizations_by_pk")
        ).in_bulk([assignment_id for _, assignment_id, service_id in rows if not service_id])
        cards = []
        for _, assignment_id, service_id in rows:
            # .get(): a card removed since the page was counted is skipped.
            if service_id and (service := services.get(service_id)):
                url = build_panel_url(self.request, aanvraag=service.public_id)
                cards.append(aanvraag_card(service, url))
            elif not service_id and (assignment := assignments.get(assignment_id)):
                url = build_panel_url(self.request, opdracht=assignment.public_id)
                cards.append(opdracht_without_aanvraag_card(assignment, url))
        return cards

    def _results_text(self, total: int) -> str:
        """ "12 aanvragen", or "12 aanvragen en 1 opdracht zonder aanvraag"."""
        without = self.search.assignments_without_aanvraag().count() if total else 0
        aanvragen = total - without
        text = f"{aanvragen} {'aanvraag' if aanvragen == 1 else 'aanvragen'}"
        if without:
            text += f" en {without} {'opdracht' if without == 1 else 'opdrachten'} zonder aanvraag"
        return text

    def controls(self):
        return {
            "results_text": self._results_text(self.page.paginator.count),
            "search_field": "zoek",
            "client_modal_count_mode": "open_assignments",
            # Opens the create sheet as a panel on the list itself via
            # ?nieuwe-opdracht, like an assignment card does. hx-push-url puts the
            # URL in the address bar so a reload reopens the sheet (see side_panel.js).
            "primary_button": assignment_create_button(self.request),
        }


@permission_required(
    [
        "core.add_assignment",
        "core.add_service",
        "core.add_placement",
        "core.add_colleague",
    ],
    raise_exception=True,
)
def assignment_import_csv(request):
    """Imports assignments from a CSV file, with their services, placements,
    colleagues and skills; see ``create_assignments_from_csv`` for the format."""
    if request.method == "GET":
        return render(request, "assignment_import.html")
    if request.method == "POST":
        if "csv_file" not in request.FILES:
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": ["Geen bestand geüpload. Upload een CSV-bestand."]}},
            )

        csv_file = request.FILES["csv_file"]

        if not csv_file.name.endswith(".csv"):
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": ["Ongeldig bestandstype. Upload een CSV-bestand."]}},
            )

        if csv_too_large(csv_file):
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": [CSV_TOO_LARGE_MSG]}},
            )

        try:
            csv_content = csv_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": ["Invalid CSV file encoding. Please use UTF-8."]}},
            )

        result = create_assignments_from_csv(request.user, csv_content, request=request)

        return render(request, "assignment_import.html", {"result": result})
    return HttpResponse(status=405)


def assignment_delete(request, public_id):
    assignment = get_object_or_404(Assignment, public_id=public_id)
    if not has_permission(Verb.DELETE, assignment, request.user):
        return HttpResponseForbidden()

    if request.method == "GET":
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Opdracht verwijderen?",
                "dialog_supporting": (
                    f"Weet je zeker dat je opdracht '{assignment.name}' wilt verwijderen? "
                    "Verwijderen is permanent en niet terug te draaien."
                ),
                "confirm_label": "Verwijder opdracht",
                "cancel_label": "Behoud opdracht",
                "form_post_url": reverse("assignment-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        name = assignment.name
        # Capture the int PK before delete() nulls it; Event.object_id keeps
        # referencing the internal id, not the public_id.
        assignment_pk = assignment.id
        # Snapshot related rows before they cascade away.
        context = _assignment_audit_snapshot(assignment)
        # Atomic so a failed audit insert rolls back the delete: losing the
        # opdracht without a trace would be the worst outcome.
        with transaction.atomic():
            assignment.delete()
            create_event(
                object_type="Assignment",
                action="delete",
                source="user",
                object_id=assignment_pk,
                user=request.user,
                request=request,
                context=context,
            )
        messages.success(request, f"Opdracht '{name}' succesvol verwijderd")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = page_url_behind_panel(request)
        return response
    return HttpResponse(status=405)


def _assignment_audit_snapshot(assignment) -> dict:
    """Snapshot for the create/delete audit event: every rol with who fills it
    (``"Java (Robbert)"``) or ``"open"``, plus the opdrachtgevers and the name.
    One entry per rol, so placements aren't duplicated."""
    services = []
    for s in assignment.services.select_related("skill").prefetch_related("placements__colleague"):
        rol = s.skill.name if s.skill_id else s.description
        names = [p.colleague.name for p in s.placements.all()]
        services.append(f"{rol} ({', '.join(names) if names else 'open'})")
    organizations = [rel.organization.label or rel.organization.name for rel in assignment.organization_relations.all()]
    snapshot = {"name": assignment.name}
    if services:
        snapshot["services"] = services
    if organizations:
        snapshot["organizations"] = organizations
    return snapshot


@require_POST
def assignment_edit_view(request, public_id):
    """Saves the combined assignment form of the child sheet.

    Same contract as placement_edit_view: HX-Location back to the parent URL on
    success, the form with messages on errors. POST-only.
    """
    assignment = Assignment.objects.filter(public_id=public_id).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    # ?veld= limits the save to that one field, so a single-field sheet does not
    # silently carry the other fields along.
    only = request.GET.get("veld") or None
    specs = assignment_edit_specs(assignment, request.user, only=only)
    if not specs:
        return HttpResponseForbidden()

    fallback = build_panel_url(request, opdracht=assignment.public_id)
    return_path = safe_return_path(request.POST.get("terug_url"), fallback)

    form_cls, _ = build_combined_form_class(specs)
    form = form_cls(request.POST)
    if not form.is_valid():
        panel_data = build_assignment_edit_panel_data(assignment, request, form=form, parent_url=return_path)
        return render(request, "parts/assignment_edit_panel_content.html", {"panel_data": panel_data})

    with transaction.atomic():
        save_edit_specs(request, specs, form.cleaned_data)

    # The panel that HX-Location fetches swaps the banner in out of band.
    assignment.refresh_from_db(fields=["name"])
    messages.success(request, f'Opdracht "{assignment.name}" is aangepast.')
    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


@require_POST
def assignment_create_sheet(request):
    """Creates the assignment from the create sheet and sends the client to its
    panel via HX-Location. Roles are added afterwards in that panel. The empty
    form itself is rendered by AssignmentListView (?nieuwe-opdracht), so it lives
    on the list URL like the object panels and survives a reload."""
    if not request.user.has_perm("core.add_assignment"):
        return HttpResponseForbidden()

    specs = assignment_create_specs()
    form_cls, _ = build_combined_form_class(specs)
    return_to = safe_return_path(request.POST.get("terug_url"), reverse("assignment-list"))

    form = form_cls(request.POST)
    if form.is_valid():
        with transaction.atomic():
            assignment = create_assignment_from_specs(form.cleaned_data)
        create_event(
            object_type="Assignment",
            action="create",
            source="user",
            object_id=assignment.id,
            user=request.user,
            request=request,
            context=_assignment_audit_snapshot(assignment),
        )
        sep = "&" if "?" in return_to else "?"
        path = f"{return_to}{sep}opdracht={assignment.public_id}"
        # base.html does not reload on the panel swap that follows HX-Location,
        # so assignment_panel_content.html swaps the banner in separately (OOB).
        # No link to the opdracht: HX-Location opens its panel already.
        messages.success(request, f'Opdracht "{assignment.name}" is aangemaakt. Voeg een aanvraag toe.')
        response = HttpResponse(status=204)
        response["HX-Location"] = json.dumps({"path": path, "target": "#side-panel-content", "swap": "innerHTML"})
        return response

    # Invalid: re-render the fragment with messages. parent_url is the sanitised
    # return address, so terug_url survives a failed submit.
    panel_data = build_assignment_create_panel_data(request, form, parent_url=return_to)
    return render(request, "parts/assignment_create_panel_content.html", {"panel_data": panel_data})


@require_POST
def assignment_member_edit_view(request, public_id):
    """Saves one team member from the child sheet, editing or adding.

    The form posts a single formset row, which mutates exactly that one service
    (and its placement). Same contract as assignment_edit_view.
    """
    assignment = Assignment.objects.filter(public_id=public_id).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return HttpResponseForbidden()

    fallback = build_panel_url(request, opdracht=assignment.public_id)
    return_path = safe_return_path(request.POST.get("terug_url"), fallback)

    def rerender(form):
        panel_data = build_assignment_member_panel_data(
            assignment,
            request,
            member_form=form,
            member_heading=request.POST.get("member_heading") or "Teamlid wijzigen",
            parent_url=return_path,
        )
        return render(request, "parts/assignment_member_edit_panel_content.html", {"panel_data": panel_data})

    form = ServiceForm(request.POST, skill_choices=skill_choices())
    if not form.is_valid():
        return rerender(form)

    # Editing an existing row: gate the target on the viewer's visible rows, so a
    # row hidden by the visibility rules is as unreachable for an edit as it is
    # for the sheet. A new row (no service_public_id) has nothing to hide yet.
    if form.cleaned_data.get("service_public_id"):
        visible_service_or_404(assignment, request, form.cleaned_data["service_public_id"])

    try:
        with member_audit_event(request, assignment):
            save_service_from_form(assignment, form)
    except ValidationError as exc:
        for message in exc.messages:
            form.add_error(None, message)
        return rerender(form)

    # A filled aanvraag has no panel (it would 404 and htmx would leave the sheet
    # open), so return to its opdracht's panel instead.
    if form.cleaned_data.get("is_filled") == "ingevuld" and "aanvraag" in QueryDict(urlsplit(return_path).query):
        return_path = url_replacing_param(return_path, "aanvraag", opdracht=str(assignment.public_id))
    verb = "aangepast" if form.cleaned_data.get("service_public_id") else "toegevoegd"
    messages.success(request, f"Teamlid is {verb}.")
    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


@require_POST
def assignment_member_delete_view(request, public_id, service_public_id):
    """Deletes one team member, after the confirmation dialog in the panel."""
    assignment = Assignment.objects.filter(public_id=public_id).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return HttpResponseForbidden()

    # Resolved through the viewer's visible rows, so a row hidden by the
    # visibility rules is as unreachable for deletion as it is for the sheet;
    # a foreign id 404s rather than emitting a no-op audit event.
    service = visible_service_or_404(assignment, request, service_public_id)

    with member_audit_event(request, assignment):
        service.delete()

    messages.success(request, "Teamlid is verwijderd.")

    return_path = safe_return_path(
        request.POST.get("terug_url"), build_panel_url(request, opdracht=assignment.public_id)
    )
    # A deleted aanvraag has no panel (it would 404 and htmx would leave the sheet
    # open), so return to its opdracht's panel instead.
    if "aanvraag" in QueryDict(urlsplit(return_path).query):
        return_path = url_replacing_param(return_path, "aanvraag", opdracht=str(assignment.public_id))
    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response
