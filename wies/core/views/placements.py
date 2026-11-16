"""Wie zit waar: the placement list and editing a placement."""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cached_property
from typing import Any, ClassVar

from django.contrib import messages
from django.db.models import (
    Case,
    Count,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from wies.core.inline_edit.forms import (
    build_combined_form_class,
)
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Event,
    Label,
    Placement,
    Skill,
    Suborganization,
)
from wies.core.querysets import (
    annotate_placement_dates,
    label_categories_for_everyone,
)
from wies.core.services.placements import (
    filter_visible_placements,
    placement_edit_specs,
    save_placement_edit,
)
from wies.core.services.urls import PAGE_PARAM, rebuild_url, safe_return_path
from wies.core.visibility_rules import (
    evaluate_placement_visibility,
)

from ._common import build_panel_url, sort_control_context
from .filters import (
    Choice,
    Filter,
    OrgFilter,
    categories_with_labels,
    finalize_filter_groups,
    label_filters,
    model_choices,
    model_filter,
    select_multi_group,
)
from .listing import FacetedListView, ListSearch
from .panels import build_placement_edit_panel_data


@dataclass(frozen=True)
class SortOption:
    """One ``?order=`` of a weergave; ``value`` "" is the default, the absence of the param.

    ``field`` is a path on what the weergave pages over (a placement for
    persoon, an opdracht for opdracht). PostgreSQL puts NULLs last on ASC and
    first on DESC, unless ``nulls_last``.
    """

    value: str
    label: str
    field: str
    descending: bool = False
    nulls_last: bool = False
    # Where a group's key is a MAX or MIN over its rows (the persoon view), the
    # value that stands in for NULL when NULL must sort first, as on DESC.
    null_sentinel: Any = None

    def order(self, key: str | None = None):
        expression = F(key or self.field)
        if not self.descending:
            return expression.asc()
        return expression.desc(nulls_last=True) if self.nulls_last else expression.desc()


class PlacementSearch(ListSearch):
    """The placements on "Wie zit waar?" under the request's search and filters.

    The list is a current-state overview: only active placements, for every
    viewer alike. History and planned placements live on the profile and the
    side panels, not here.

    ``group_field`` is what a card is, so what the counts count: two colleagues
    on one assignment are two cards in the person view and one in the
    assignment view.
    """

    org_lookup = "service__assignment__organizations__id"

    def __init__(self, request, group_field: str):
        super().__init__(request)
        self.group_field = group_field

    @cached_property
    def today(self) -> date:
        return timezone.now().date()

    def facet_scopes(self):
        # Subgroep has no filter here, so a Subgroep label from an old link gets
        # the "Onbekend label" chip instead of filtering out of sight.
        return {Label: Label.objects.filter(category__in=label_categories_for_everyone())}

    @cached_property
    def scope(self):
        qs = Placement.objects.all()
        if self.excluded_org_ids:
            qs = qs.exclude(service__assignment__organizations__id__in=self.excluded_org_ids)
        if self.query:
            qs = qs.filter(
                Q(colleague__name__icontains=self.query)
                | Q(service__assignment__name__icontains=self.query)
                | Q(service__assignment__extra_info__icontains=self.query)
                | Q(service__assignment__organizations__label__icontains=self.query)
            )
        return filter_visible_placements(annotate_placement_dates(qs), self.today)

    # The filters

    @cached_property
    def org(self):
        return OrgFilter(
            self.resolver,
            self.params,
            apply_ids=lambda qs, ids: qs.filter(service__assignment__organizations__id__in=ids),
        )

    @cached_property
    def rol(self):
        return model_filter("rol", self.resolver("rol", Skill), "service__skill_id")

    @cached_property
    def onderdeel(self):
        # One onderdeel per colleague: OR within the selection.
        return model_filter("onderdeel", self.resolver("onderdeel", Suborganization), "colleague__suborganization_id")

    @cached_property
    def labels(self):
        return label_filters(self.resolver("labels", Label), "colleague__labels__id")

    @cached_property
    def loopt_af_options(self) -> dict[str, tuple[str, Q]]:
        """The "loopt af" choices, on the opdracht's end date. Cumulative: 6m includes 3m."""
        half_year = self.today + timedelta(days=182)
        return {
            "3m": ("Binnen 3 maanden", Q(service__assignment__end_date__lte=self.today + timedelta(days=91))),
            "6m": ("Binnen 6 maanden", Q(service__assignment__end_date__lte=half_year)),
            "6m+": ("Langer dan 6 maanden", Q(service__assignment__end_date__gt=half_year)),
        }

    @cached_property
    def loopt_af(self):
        # An unknown value filters nothing, so it is dropped rather than left
        # behind as a hidden input without a chip.
        values = [v for v in dict.fromkeys(self.params.getlist("loopt_af")) if v in self.loopt_af_options]
        either = Q()
        for value in values:
            either |= self.loopt_af_options[value][1]
        return Filter("loopt_af", active=bool(values), narrow=lambda qs: qs.filter(either), values=values)

    def filters(self):
        return [self.org, self.rol, self.onderdeel, *self.labels, self.loopt_af]

    # The sidebar

    @cached_property
    def filter_groups(self):
        return finalize_filter_groups(
            [
                self.org.group(self.org_counts()),
                select_multi_group(
                    "rol",
                    "Rol",
                    model_choices(Skill.objects.order_by("name")),
                    self.rol.values,
                    self.count("rol", "service__skill_id"),
                ),
                select_multi_group(
                    "onderdeel",
                    "Onderdeel",
                    model_choices(Suborganization.objects.all()),
                    self.onderdeel.values,
                    self.count("onderdeel", "colleague__suborganization_id"),
                ),
                *self.label_groups(
                    categories_with_labels(label_categories_for_everyone()), "colleague__labels__id", with_color=True
                ),
                select_multi_group(
                    "loopt_af",
                    "Loopt af",
                    [Choice(value, label, value) for value, (label, _) in self.loopt_af_options.items()],
                    self.loopt_af.values,
                    self.loopt_af_counts(),
                ),
            ]
        )

    def loopt_af_counts(self) -> dict[str, int]:
        """Cards per "loopt af" choice, each on its own, in one query."""
        base = self.filtered(skip="loopt_af")
        return Placement.objects.filter(pk__in=base.values("pk")).aggregate(
            **{
                value: Count(self.group_field, distinct=True, filter=condition)
                for value, (_, condition) in self.loopt_af_options.items()
            }
        )


class PlacementListView(FacetedListView):
    """Wie zit waar?: the placements as cards, one per person or one per opdracht.

    The weergave (``?weergave=``) is not a display toggle: it decides what a
    card is, so what is paged, sorted and counted. Each is its own view below;
    ``placement_list`` picks one per request.
    """

    template_name = "placements.html"
    results_template = "parts/filter_and_table_container.html"
    rows_template = "parts/placement_cards.html"
    filter_url_name = "home"
    side_panel = True

    weergave: ClassVar[str]
    label: ClassVar[str]
    icon: ClassVar[str]
    # What one card is: the field the cards are grouped, paged and counted on.
    group_field: ClassVar[str]
    default_sort: ClassVar[SortOption]
    sorts: ClassVar[tuple[SortOption, ...]]

    @classmethod
    def make_search(cls, request) -> PlacementSearch:
        return PlacementSearch(request, group_field=cls.group_field)

    @cached_property
    def sort(self) -> SortOption:
        """The requested sort; a shared url can carry an order this view does not have."""
        order = self.request.GET.get("order") or ""
        return next((sort for sort in self.sorts if sort.value == order), self.default_sort)

    def _view_url(self, view: type[PlacementListView]) -> str:
        """URL for a weergave: keeps the filters and search, drops page and order.

        The sort options differ per view, so an ?order= from the other view would
        not resolve here.
        """
        dropped = (PAGE_PARAM, "order")
        if view is DEFAULT_WEERGAVE:
            return rebuild_url(reverse("home"), self.request.GET, drop=(*dropped, "weergave"))
        return rebuild_url(reverse("home"), self.request.GET, drop=dropped, weergave=view.weergave)

    def controls(self):
        filtered = self.search.filtered()
        view_options = [
            {
                "value": view.weergave,
                "label": view.label,
                "icon": view.icon,
                "url": self._view_url(view),
                "selected": view is type(self),
                "count": self.page.paginator.count
                if view is type(self)
                else filtered.values(view.group_field).distinct().count(),
            }
            for view in WEERGAVEN.values()
        ]
        return {
            "active_view": self.weergave,
            # The template compares against it rather than hardcoding the name, so
            # changing the default does not silently break the hidden field.
            "default_view": DEFAULT_WEERGAVE.weergave,
            "view_options": view_options,
            "client_modal_count_mode": "placements",
            **sort_control_context(
                self.sort.value,
                [(sort.value, sort.label) for sort in self.sorts],
                self.default_sort.label,
            ),
        }


class PersoonListView(PlacementListView):
    """One card per colleague, with the opdrachten they are placed on.

    Paged on colleagues, not placements, so a person never straddles a page
    boundary. A colleague's place in the order is where their first placement
    lands under the sort: the MIN of an ascending field, the MAX of a
    descending one, over the placements that pass the filters. Both ignore
    NULL, which puts a colleague with only NULLs last, as PostgreSQL does on
    ASC and on DESC NULLS LAST.
    """

    weergave = "persoon"
    label = "Persoon"
    icon = "person"
    group_field = "colleague_id"
    # Nulls last: a placement without a start date says nothing about how recent it is.
    default_sort = SortOption("", "Startdatum (nieuwste eerst)", "actual_start_date", descending=True, nulls_last=True)
    sorts = (
        SortOption("name", "Naam (A-Z)", "colleague__name"),
        SortOption("-name", "Naam (Z-A)", "colleague__name", descending=True),
        SortOption("assignment", "Opdracht (A-Z)", "service__assignment__name"),
        SortOption("-assignment", "Opdracht (Z-A)", "service__assignment__name", descending=True),
        SortOption("end_date", "Einddatum (oudste eerst)", "service__assignment__end_date"),
        # Newest first puts an opdracht without end date on top, as DESC does
        # with NULL; MAX would skip the NULL, so it stands in as the latest date.
        SortOption(
            "-end_date",
            "Einddatum (nieuwste eerst)",
            "service__assignment__end_date",
            descending=True,
            null_sentinel=date.max,
        ),
    )

    def _group_key(self):
        sort = self.sort
        expression = F(sort.field) if sort.null_sentinel is None else Coalesce(sort.field, Value(sort.null_sentinel))
        return Max(expression) if sort.descending else Min(expression)

    def page_source(self):
        """The colleague ids in display order; the colleague id breaks ties."""
        return (
            self.search.filtered()
            .order_by()
            .values("colleague_id")
            .annotate(sort_key=self._group_key())
            .order_by(self.sort.order("sort_key"), "colleague_id")
            .values_list("colleague_id", flat=True)
        )

    def rows(self, page):
        colleague_ids = list(page.object_list)
        placements = (
            list(
                self.search.filtered()
                .filter(colleague_id__in=colleague_ids)
                .select_related("colleague", "service__assignment", "service__skill")
                .order_by(self.sort.order(), "colleague_id")
            )
            if colleague_ids
            else []
        )
        return {
            "object_list": placements,
            "cards": self._cards(placements, colleague_ids),
            "active_view": self.weergave,
        }

    def _cards(self, placements: list[Placement], colleague_ids: list[int]) -> list[dict]:
        """The card opens the colleague panel, whatever their number of
        opdrachten; its cards lead on to each opdracht. ``assignment`` is set
        only for a person on exactly one, so the card can name it and its period."""
        grouped: dict[int, list[Placement]] = {colleague_id: [] for colleague_id in colleague_ids}
        for placement in placements:
            grouped[placement.colleague_id].append(placement)
        cards = []
        for rows in grouped.values():
            if not rows:
                continue
            assignments = list(dict.fromkeys(row.service.assignment for row in rows))
            cards.append(
                {
                    "name": rows[0].colleague.name,
                    "assignment": assignments[0] if len(assignments) == 1 else None,
                    "assignments": assignments,
                    "roles": list(dict.fromkeys(row.service.skill.name for row in rows if row.service.skill)),
                    "panel_url": build_panel_url(self.request, collega=rows[0].colleague.public_id),
                }
            )
        return cards


class OpdrachtListView(PlacementListView):
    """One card per opdracht with a placement that passes the filters, showing its FULL team.

    Pages the opdrachten themselves: every sort here is a field of the
    opdracht, so the filtered placements only decide which opdrachten are in.
    """

    weergave = "opdracht"
    label = "Opdracht"
    icon = "business-suitcase"
    group_field = "service__assignment_id"
    # No modified-at on the model, so the audit log stands in. Nulls last:
    # events age out of retention.
    default_sort = SortOption("", "Laatst gewijzigd", "last_change", descending=True, nulls_last=True)
    # Sorting on colleague name says nothing here, where one card is a whole team.
    sorts = (
        SortOption("assignment", "Opdracht (A-Z)", "name"),
        SortOption("-assignment", "Opdracht (Z-A)", "name", descending=True),
        SortOption("end_date", "Einddatum (oudste eerst)", "end_date"),
        SortOption("-end_date", "Einddatum (nieuwste eerst)", "end_date", descending=True),
    )

    def page_source(self):
        assignments = Assignment.objects.filter(id__in=self.search.filtered().values("service__assignment_id"))
        if self.sort.field == "last_change":
            assignments = assignments.annotate(
                last_change=Subquery(
                    Event.objects.filter(object_type="Assignment", object_id=OuterRef("pk"))
                    .order_by("-timestamp")
                    .values("timestamp")[:1]
                )
            )
        return assignments.order_by(self.sort.order(), "id").prefetch_related(
            Prefetch(
                "organization_relations",
                queryset=AssignmentOrganizationUnit.objects.annotate(
                    role_order=Case(When(role="PRIMARY", then=0), default=1)
                )
                .order_by("role_order")
                .select_related("organization"),
                to_attr="sorted_clients",
            )
        )

    def rows(self, page):
        assignments = list(page.object_list)
        return {"object_list": assignments, "cards": self._cards(assignments), "active_view": self.weergave}

    def _cards(self, assignments) -> list[dict]:
        """The team is fetched separately rather than read off the filtered
        placements: a filter on role or label would otherwise silently shrink the
        team shown on the card to the people that matched the filter.

        Sidestepping the selection filters is the point here; sidestepping the
        visibility filter is not. This page is a current-state overview, so the
        team is the team as it stands today — the same rule the list itself
        follows, and without it a card would name people who left months ago or
        have not started yet.
        """
        teams: dict[int, list[dict]] = {a.id: [] for a in assignments}
        seen: set[tuple[int, int]] = set()
        team_rows = (
            filter_visible_placements(
                annotate_placement_dates(Placement.objects.filter(service__assignment_id__in=teams)),
                self.search.today,
            )
            .select_related("colleague", "service__skill")
            .order_by("colleague__name")
        )
        for row in team_rows:
            key = (row.service.assignment_id, row.colleague_id)
            if key not in seen:
                seen.add(key)
                role = row.service.skill.name if row.service.skill else ""
                teams[row.service.assignment_id].append({"name": row.colleague.name, "role": role})

        cards = []
        for assignment in assignments:
            clients = assignment.sorted_clients
            cards.append(
                {
                    "name": assignment.name,
                    "assignment": assignment,
                    "client": (clients[0].organization.label or clients[0].organization.name) if clients else "",
                    "extra_clients": max(len(clients) - 1, 0),
                    "panel_url": build_panel_url(self.request, opdracht=assignment.public_id),
                    "team": teams[assignment.id],
                }
            )
        return cards


WEERGAVEN: dict[str, type[PlacementListView]] = {view.weergave: view for view in (PersoonListView, OpdrachtListView)}
DEFAULT_WEERGAVE = PersoonListView


def weergave_view(request) -> type[PlacementListView]:
    """The view of the requested ?weergave=, the default for unknown values."""
    return WEERGAVEN.get(request.GET.get("weergave") or "", DEFAULT_WEERGAVE)


def placement_list(request, *args, **kwargs):
    """ "Wie zit waar?": hands the request to the view of its weergave."""
    return weergave_view(request).as_view()(request, *args, **kwargs)


@require_POST
def placement_edit_view(request, public_id):
    """Saves the combined edit form of the placement child sheet.

    Reached from the UI only by a placed consultant ("Taken wijzigen",
    ``?veld=skill``); the role, hours and period branches stay for a business
    manager's POST, whose sheet is "Teamlid wijzigen" now.

    On success the client is sent back to the parent URL via HX-Location, which
    re-renders the panel through the normal panel route. Rendering the parent
    panel here is not possible: panel URLs are built from ``request.path``, which
    is the POST path, so its buttons would point back at this endpoint. On errors
    the form returns with messages. POST-only, so a GET can never show an empty
    form.
    """
    placement = (
        Placement.objects.select_related("colleague", "service__assignment", "service__skill")
        .filter(public_id=public_id)
        .first()
    )
    if placement is None:
        raise Http404("Unknown placement")
    today = timezone.now().date()
    if not evaluate_placement_visibility(
        placement.start_date, placement.end_date, placement.colleague_id, request, today
    ).visible:
        raise Http404("Unknown placement")

    # ?veld= limits the save to that one field, so a single-field sheet does not
    # silently carry the other fields along.
    only = request.GET.get("veld") or None
    specs = placement_edit_specs(placement, request.user, only=only)
    if not specs:
        return HttpResponseForbidden()

    fallback = build_panel_url(request, opdracht=placement.service.assignment.public_id)
    return_path = safe_return_path(request.POST.get("terug_url"), fallback)

    form_cls, _ = build_combined_form_class(specs)
    form = form_cls(request.POST)
    if not form.is_valid():
        panel_data = build_placement_edit_panel_data(placement, request, form=form, parent_url=return_path)
        return render(request, "parts/placement_edit_panel_content.html", {"panel_data": panel_data})

    save_placement_edit(request, placement, specs, form.cleaned_data)
    # The panel that HX-Location fetches swaps the banner in out of band.
    messages.success(request, f"Plaatsing van {placement.colleague.name} is aangepast.")

    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response
