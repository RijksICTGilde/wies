"""Opdrachten: list, create, edit, delete, team members and CSV import."""

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
from django.views.generic.list import ListView

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
from wies.core.services.organizations import (
    get_top_org_options,
    org_counts_from_filtered,
)
from wies.core.services.placements import (
    create_assignments_from_csv,
)
from wies.core.services.urls import PAGE_PARAM, rebuild_url, safe_return_path, url_replacing_param

from ._common import (
    CSV_TOO_LARGE_MSG,
    PANEL_PARAMS,
    back_to_panel,
    build_panel_url,
    csv_too_large,
    is_side_panel_request,
    page_url_behind_panel,
)
from .filters import PublicIdFacetsMixin, finalize_filter_groups
from .panels import (
    assignment_create_button,
    build_assignment_create_panel_data,
    build_assignment_edit_panel_data,
    build_assignment_member_panel_data,
    resolve_side_panel,
)


class AssignmentListView(PublicIdFacetsMixin, ListView):
    """Aanvragen as cards: one per role nobody fills yet, and one per opdracht
    that has no role at all yet. Infinite scroll pagination."""

    model = Service
    template_name = "assignments.html"
    paginate_by = 60
    page_kwarg = "pagina"

    @cached_property
    def _search(self) -> str:
        return self.request.GET.get("zoek", "")

    @cached_property
    def _beschikbaar_vanaf(self) -> date | None:
        # An unparsable date filters nothing.
        try:
            return date.fromisoformat(self.request.GET.get("beschikbaar_vanaf", ""))
        except ValueError:
            return None

    def _assignments_matching_search(self):
        # A subquery: joined directly, an opdracht with two matching
        # opdrachtgevers would give each card twice.
        return Assignment.objects.filter(
            Q(name__icontains=self._search)
            | Q(extra_info__icontains=self._search)
            | Q(organizations__name__icontains=self._search)
            | Q(organizations__label__icontains=self._search)
            | Q(organizations__abbreviations__icontains=self._search)
        )

    def _get_base_queryset(self):
        qs = open_aanvragen()
        if self._search:
            qs = qs.filter(
                Q(skill__name__icontains=self._search)
                | Q(request_description__icontains=self._search)
                | Q(location__icontains=self._search)
                | Q(assignment__in=self._assignments_matching_search())
            )
        if self._beschikbaar_vanaf:
            # An aanvraag that starts per direct, has no start or has already
            # started can be filled any day, so it stays; one that starts later
            # has to start on or after the chosen date. Either way it must
            # still run on that date.
            vanaf = self._beschikbaar_vanaf
            qs = qs.filter(
                Q(starts_immediately=True)
                | Q(effective_start_date__isnull=True)
                | Q(effective_start_date__lte=timezone.now().date())
                | Q(effective_start_date__gte=vanaf),
                Q(effective_end_date__isnull=True) | Q(effective_end_date__gte=vanaf),
            )
        return qs

    @cached_property
    def _locations(self) -> dict[str, str]:
        return standplaats_labels(open_aanvragen())

    @cached_property
    def _selected_locations(self) -> list[str]:
        return known_standplaatsen(self.request.GET.getlist("standplaats"), self._locations)

    def _apply_filters(self, qs, *, exclude_filter=None):
        rol = self.facets("rol", Skill)
        if exclude_filter != "rol" and rol.requested:
            qs = qs.filter(skill_id__in=rol.ids)

        if exclude_filter != "standplaats" and self._selected_locations:
            qs = filter_on_standplaatsen(qs, self._selected_locations)

        if exclude_filter != "org":
            # Through the opdracht, for the same reason as the search above.
            qs = qs.filter(assignment__in=self.apply_org_filter(Assignment.objects.all(), "organizations__id__in"))

        return qs

    def _assignments_without_aanvraag(self, *, filter_on_org=True):
        """The opdrachten without a role, under the same search and
        opdrachtgever filter. A role, standplaats or date asks about an
        aanvraag, which they do not have, so it leaves them out."""
        if self.facets("rol", Skill).requested or self._selected_locations or self._beschikbaar_vanaf:
            return Assignment.objects.none()
        qs = assignments_without_aanvraag()
        if self._search:
            qs = qs.filter(pk__in=self._assignments_matching_search())
        if filter_on_org:
            qs = qs.filter(pk__in=self.apply_org_filter(Assignment.objects.all(), "organizations__id__in"))
        return qs

    def org_counts(self) -> Counter[int]:
        """Cards per opdrachtgever under every filter but the opdrachtgever's,
        for the sidebar and the opdrachtgever picker alike."""
        services = self._apply_filters(self._get_base_queryset(), exclude_filter="org")
        assignments = self._assignments_without_aanvraag(filter_on_org=False)
        return org_counts_from_filtered(services, Service, "assignment__organizations__id") + org_counts_from_filtered(
            assignments, Assignment, "organizations__id"
        )

    def get_queryset(self):
        """(created, opdracht id, aanvraag id) per card, newest opdracht first;
        the aanvraag id is None on an opdracht without one. A union, so paging
        and counting stay in the database; get_context_data loads the cards."""
        columns = ("card_created", "card_assignment", "card_service")
        aanvragen = (
            self._apply_filters(self._get_base_queryset())
            .annotate(
                card_created=F("assignment__created_at"), card_assignment=F("assignment_id"), card_service=F("id")
            )
            .values_list(*columns)
        )
        without_aanvraag = (
            self._assignments_without_aanvraag()
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
        without = self._assignments_without_aanvraag().count() if total else 0
        aanvragen = total - without
        text = f"{aanvragen} {'aanvraag' if aanvragen == 1 else 'aanvragen'}"
        if without:
            text += f" en {without} {'opdracht' if without == 1 else 'opdrachten'} zonder aanvraag"
        return text

    def get_template_names(self):
        if "HX-Request" in self.request.headers:
            if self.request.GET.get("filter_modal"):
                return ["parts/filter_options_modal.html"]
            if is_side_panel_request(self.request):
                # See PlacementListView.get_template_names.
                panel_data = getattr(self, "_panel_data", None)
                if panel_data:
                    return [panel_data["panel_content_template"]]
                return ["parts/assignment_panel_content.html"]
            if self.request.GET.get("pagina"):
                return ["parts/aanvraag_card_rows.html"]
            return ["parts/filter_and_card_container_assignments.html"]
        return ["assignments.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["render_filter_fields_oob"] = "HX-Request" in self.request.headers

        context["object_list"] = self._cards(context["object_list"])
        context["results_text"] = self._results_text(context["paginator"].count)

        context["filter_target_url"] = reverse("assignment-list")
        context["search_field"] = "zoek"
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters = {}
        if self._beschikbaar_vanaf:
            active_filters["beschikbaar_vanaf"] = self._beschikbaar_vanaf

        # rol filter supports multi-select (values are skill public_ids)
        rol_filter = self.facets("rol", Skill).active_values
        if rol_filter:
            active_filters["rol"] = rol_filter
        if self._selected_locations:
            active_filters["standplaats"] = set(self._selected_locations)

        # Role counts: exclude the role filter for cross-filtering. They count
        # aanvragen, so two for the same role on one opdracht count 2.
        base_qs = self._get_base_queryset()
        skill_counts = Counter(
            skill_id
            for skill_id in self._apply_filters(base_qs, exclude_filter="rol").values_list("skill_id", flat=True)
            if skill_id is not None
        )

        skill_options = [{"value": "", "label": ""}]
        skill_selected_values = []
        for skill in Skill.objects.order_by("name"):
            option = {"value": str(skill.public_id), "label": skill.name, "count": skill_counts.get(skill.id, 0)}
            if str(skill.public_id) in active_filters.get("rol", set()):
                option["selected"] = True
                skill_selected_values.append(str(skill.public_id))
            skill_options.append(option)

        # Standplaats counts: same cross-filter rule, without the standplaats filter.
        location_counts = Counter(
            standplaats_key(location)
            for location in self._apply_filters(base_qs, exclude_filter="standplaats").values_list(
                "location", flat=True
            )
        )
        location_options = [{"value": "", "label": ""}]
        for key, label in self._locations.items():
            option = {"value": key, "label": label, "count": location_counts.get(key, 0)}
            if key in self._selected_locations:
                option["selected"] = True
            location_options.append(option)

        # Organization filter (multi-select via modal)
        self.add_org_filter_context(context, active_filters)
        self.add_unknown_filter_chips(context, {"rol": Skill})

        # Org counts exclude the org filter, so the numbers reflect the other
        # active filters — same cross-filter rule as the skill counts above.
        org_counts = self.org_counts()

        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)
        context["client_modal_count_mode"] = "open_assignments"

        context["filter_groups"] = [
            {
                "type": "modal",
                "name": "organisatie",
                "label": "Opdrachtgever",
                "top_options": get_top_org_options(
                    set(self.facets("org", OrganizationUnit).ids),
                    org_counts,
                    selected_self_ids=set(self.facets("org_self", OrganizationUnit).ids),
                    selected_type_labels=set(self.org_type_filter),
                    selected_type_in=self.org_type_in_filter,
                ),
            },
            {
                "type": "select-multi",
                "name": "rol",
                "label": "Rol",
                "options": skill_options,
                "selected_values": skill_selected_values,
            },
            {
                "type": "select-multi",
                "name": "standplaats",
                "label": "Standplaats",
                "options": location_options,
                "selected_values": self._selected_locations,
            },
            {
                "type": "date",
                "name": "beschikbaar_vanaf",
                "label": "Beschikbaar vanaf",
            },
        ]
        finalize_filter_groups(context["filter_groups"])
        context["filter_modal_group_id"] = self.request.GET.get("filter_modal", "")

        # Build next page URL with all current filters
        if context.get("page_obj") and context["page_obj"].has_next():
            context["next_page_url"] = rebuild_url(
                "", self.request.GET, drop=PANEL_PARAMS, **{PAGE_PARAM: context["page_obj"].next_page_number()}
            )
        else:
            context["next_page_url"] = None

        # Opens the create sheet as a panel on the list itself via
        # ?nieuwe-opdracht, like an assignment card does. hx-push-url puts the URL
        # in the address bar so a reload reopens the sheet (see side_panel.js).
        context["primary_button"] = assignment_create_button(self.request)

        # Side panel; ?nieuwe-opdracht opens the empty create form on the list.
        context["panel_data"] = resolve_side_panel(self.request, allow_create=True)
        # See PlacementListView.get_context_data: get_template_names reads this.
        self._panel_data = context["panel_data"]
        return context


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
    return back_to_panel(return_path)


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
        return back_to_panel(path)

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
            # terug_url may point at an aanvraag or collega panel; keep its label.
            back_text=request.POST.get("back_text"),
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
    return back_to_panel(return_path)


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
    return back_to_panel(return_path)
