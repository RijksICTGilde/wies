"""Wie zit waar: the placement list and editing a placement."""

import json
from collections import Counter
from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    Model,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    When,
)
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.decorators.http import require_POST
from django.views.generic import View

from wies.core.inline_edit.forms import (
    build_combined_form_class,
)
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Event,
    Label,
    OrganizationUnit,
    Placement,
    Skill,
    Suborganization,
)
from wies.core.querysets import (
    annotate_placement_dates,
    label_categories_for_everyone,
)
from wies.core.services.dates import datum_nl
from wies.core.services.organizations import (
    get_excluded_org_ids,
    get_top_org_options,
    org_counts_from_filtered,
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

from ._common import PANEL_PARAMS, build_panel_url, count_label, is_side_panel_request, sort_control_context
from .client_picker import client_modal_response, is_client_modal_request
from .filters import PublicIdFacetsMixin, filter_modal_response, finalize_filter_groups, is_filter_modal_request
from .panels import (
    build_placement_edit_panel_data,
    resolve_side_panel,
    side_panel_response,
)


def _facet_counts(filtered_qs, facet_lookup: str, group_field: str) -> Counter[int]:
    """Counts distinct groups per facet value, not placements.

    The list shows one card per colleague or per assignment, so a sidebar that
    counted placements would report a higher number than the list has cards.

    Re-keys on distinct placement ids first: projecting straight off a
    .distinct() queryset emits SELECT DISTINCT on the projected columns only,
    which drops rows that differ elsewhere.
    """
    rows = Placement.objects.filter(id__in=filtered_qs.values_list("id", flat=True))
    pairs = rows.values_list(facet_lookup, group_field).distinct()
    return Counter(fid for fid, _ in pairs if fid is not None)


def _period_text(assignments: list[Assignment]) -> str:
    """The card's period row: "tot aug 2027", "Geen einddatum" or, for more than
    one assignment, "Meerdere periodes"."""
    if len(assignments) > 1:
        return "Meerdere periodes"
    end_date = assignments[0].end_date
    return f"tot {datum_nl(end_date, 'b Y')}" if end_date else "Geen einddatum"


LOOPT_AF_DAYS = {"3m": 91, "6m": 182}


class PlacementFilters(PublicIdFacetsMixin):
    """The search and selection filters of "Wie zit waar?", for both weergaven.

    A colleague and an opdracht are both selected through their current
    placements, so this is the one definition of a placement that matches.
    """

    def __init__(self, request):
        self.request = request

    def facet_scopes(self) -> dict[type[Model], QuerySet]:
        # Subgroep has no filter here, so a Subgroep label from an old link gets
        # the "Onbekend label" chip instead of filtering out of sight.
        return {Label: Label.objects.filter(category__in=label_categories_for_everyone())}

    @cached_property
    def search(self) -> str:
        return self.request.GET.get("zoek") or ""

    @cached_property
    def loopt_af_values(self) -> set[str]:
        """The ``?loopt_af=`` presets that filter; anything else is ignored, as before."""
        return set(self.request.GET.getlist("loopt_af")) & {"3m", "6m", "6m+"}

    def placement_facet_active(self, exclude_filter=None) -> bool:
        """Whether a filter that only a placement can match is set (rol, opdrachtgever, loopt af)."""
        org = self.facets("org", OrganizationUnit)
        org_self = self.facets("org_self", OrganizationUnit)
        org_active = org.requested or org_self.requested or self.org_type_filter or self.org_type_in_filter
        return bool(
            (exclude_filter != "rol" and self.facets("rol", Skill).requested)
            or (exclude_filter != "org" and org_active)
            or (exclude_filter != "loopt_af" and self.loopt_af_values)
        )

    def matching_placements(self, *, exclude_filter=None):
        """The current placements that pass the search and the filters.

        ``exclude_filter`` leaves one filter out, for the count next to its own
        options: "rol", "org", "onderdeel", "loopt_af", or a category_id (int)
        for labels.

        The list is a current-state overview: only active placements, for every
        viewer alike. History and planned placements live on the profile and the
        side panels, not here. Unordered and not distinct: callers re-key on ids
        or ask whether one exists.
        """
        qs = annotate_placement_dates(Placement.objects.all())
        excluded_org_ids = get_excluded_org_ids()
        if excluded_org_ids:
            qs = qs.exclude(service__assignment__organizations__id__in=excluded_org_ids)

        if self.search:
            qs = qs.filter(
                Q(colleague__name__icontains=self.search)
                | Q(service__assignment__name__icontains=self.search)
                | Q(service__assignment__extra_info__icontains=self.search)
                | Q(service__assignment__organizations__label__icontains=self.search)
            )

        rol = self.facets("rol", Skill)
        if exclude_filter != "rol" and rol.requested:
            qs = qs.filter(service__skill_id__in=rol.ids)

        if exclude_filter != "org":
            qs = self.apply_org_filter(qs, "service__assignment__organizations__id__in")

        # Label filter: OR within category, AND between categories
        for cat_id, cat_label_ids in self.labels_by_category.items():
            if exclude_filter != cat_id:
                qs = qs.filter(colleague__labels__id__in=cat_label_ids)

        # Onderdeel filter: OR within the group (one onderdeel per colleague)
        suborganization_facet = self.facets("onderdeel", Suborganization)
        if exclude_filter != "onderdeel" and suborganization_facet.requested:
            qs = qs.filter(colleague__suborganization_id__in=suborganization_facet.ids)

        if exclude_filter != "loopt_af" and self.loopt_af_values:
            qs = qs.filter(self._loopt_af_condition())

        return filter_visible_placements(qs, timezone.now().date())

    def _loopt_af_condition(self) -> Q:
        """The opdracht end date within the chosen presets ("6m+" is beyond half a year)."""
        today = timezone.now().date()
        half_year = today + timedelta(days=LOOPT_AF_DAYS["6m"])
        condition = Q()
        bounded = [LOOPT_AF_DAYS[v] for v in self.loopt_af_values if v in LOOPT_AF_DAYS]
        if bounded:
            condition |= Q(service__assignment__end_date__lte=today + timedelta(days=max(bounded)))
        if "6m+" in self.loopt_af_values:
            condition |= Q(service__assignment__end_date__gt=half_year)
        return condition


class _Overview:
    """One weergave of "Wie zit waar?": what a card is, and how the list sorts and counts.

    Subclasses set the subject and the placement field that groups placements
    into that subject, so every sidebar count is a count of cards.
    """

    GROUP_FIELD: str
    SORT_OPTIONS: list[str]
    DEFAULT_SORT_LABEL: str
    COUNT_NOUNS: tuple[str, str]
    EMPTY_TEXT: str

    def __init__(self, filters: PlacementFilters):
        self.filters = filters
        self.request = filters.request

    @cached_property
    def order(self) -> str:
        """The requested ?order=, or "" for the default: a shared url can carry another weergave's."""
        order = self.request.GET.get("order") or ""
        return order if order in self.SORT_OPTIONS else ""

    def queryset(self, *, exclude_filter=None) -> QuerySet:
        raise NotImplementedError

    def listed(self) -> QuerySet:
        """The subjects in the list.

        A label filter that resolves to no label empties the list (fail closed);
        the sidebar counts carry on without it, so the user can clear the chip.
        """
        if self.filters.labels_match_nothing:
            return self.queryset().none()
        return self.queryset()

    def placement_counts(self, facet_lookup: str, *, exclude_filter) -> Counter[int]:
        """Cards per value of a placement facet, under every filter but its own."""
        return _facet_counts(
            self.filters.matching_placements(exclude_filter=exclude_filter), facet_lookup, self.GROUP_FIELD
        )

    def colleague_counts(self, field: str, *, exclude_filter) -> Counter[int]:
        """Cards per value of a colleague field (labels, onderdeel)."""
        return self.placement_counts(f"colleague__{field}", exclude_filter=exclude_filter)

    def org_counts(self) -> Counter[int]:
        """Cards per opdrachtgever under every filter but the opdrachtgever's,
        for the sidebar and the opdrachtgever picker alike."""
        return org_counts_from_filtered(
            self.filters.matching_placements(exclude_filter="org"),
            Placement,
            "service__assignment__organizations__id",
            group_field=self.GROUP_FIELD,
        )

    def loopt_af_options(self) -> list[dict]:
        """The 'loopt af' filter options, each with the cards it would leave."""
        today = timezone.now().date()
        matching = self.filters.matching_placements(exclude_filter="loopt_af")

        def card_count(condition):
            return matching.filter(condition).values(self.GROUP_FIELD).distinct().count()

        options = [{"value": "", "label": ""}]
        for value, label in (("3m", "Binnen 3 maanden"), ("6m", "Binnen 6 maanden")):
            end_date = today + timedelta(days=LOOPT_AF_DAYS[value])
            count = card_count(Q(service__assignment__end_date__lte=end_date))
            options.append({"value": value, "label": label, "count": count})
        half_year = today + timedelta(days=LOOPT_AF_DAYS["6m"])
        count_beyond = card_count(Q(service__assignment__end_date__gt=half_year))
        options.append({"value": "6m+", "label": "Langer dan 6 maanden", "count": count_beyond})
        return options


class ColleagueOverview(_Overview):
    """The persoon weergave: one card per colleague.

    A colleague is listed for a placement that matches, or, with an account,
    for having no current placement at all, so a new account can find itself.
    """

    GROUP_FIELD = "colleague_id"
    SORT_OPTIONS = ["name", "-name", "assignment", "-assignment", "end_date", "-end_date"]
    DEFAULT_SORT_LABEL = "Startdatum (nieuwste eerst)"
    COUNT_NOUNS = ("collega", "collega's")
    EMPTY_TEXT = "Geen collega's gevonden"

    # The placement that decides where a colleague sorts: (field, descending, nulls_last).
    # Nulls last on the default: a placement without a start date says nothing
    # about how recent it is.
    PLACEMENT_SORT = {
        "": ("actual_start_date", True, True),
        "assignment": ("service__assignment__name", False, None),
        "-assignment": ("service__assignment__name", True, None),
        "end_date": ("service__assignment__end_date", False, None),
        "-end_date": ("service__assignment__end_date", True, None),
    }

    def queryset(self, *, exclude_filter=None) -> QuerySet:
        matching = self.filters.matching_placements(exclude_filter=exclude_filter)
        listed = Q(Exists(matching.filter(colleague=OuterRef("pk"))))
        # Rol, opdrachtgever and loopt af ask about a placement, which these
        # colleagues do not have.
        if not self.filters.placement_facet_active(exclude_filter):
            listed |= self._without_current_placement(exclude_filter)
        return Colleague.objects.filter(listed)

    def _without_current_placement(self, exclude_filter) -> Q:
        """Colleagues with an account and no current placement, under the filters
        a colleague matches on their own: the search on name, labels, onderdeel.

        A placement at a hidden organization still counts as current: a
        "Nu geen opdracht" card would otherwise give away that it exists.
        """
        current = filter_visible_placements(
            annotate_placement_dates(Placement.objects.filter(colleague=OuterRef("pk"))), timezone.now().date()
        )
        condition = Q(user__isnull=False, user__is_active=True) & Q(~Exists(current))
        if self.filters.search:
            condition &= Q(name__icontains=self.filters.search)
        # A subquery per category: one join would need a single label in all of them.
        for cat_id, cat_label_ids in self.filters.labels_by_category.items():
            if exclude_filter != cat_id:
                condition &= Q(pk__in=Colleague.objects.filter(labels__id__in=cat_label_ids).values("pk"))
        suborganization_facet = self.filters.facets("onderdeel", Suborganization)
        if exclude_filter != "onderdeel" and suborganization_facet.requested:
            condition &= Q(suborganization_id__in=suborganization_facet.ids)
        return condition

    def colleague_counts(self, field: str, *, exclude_filter) -> Counter[int]:
        # On the colleagues themselves, so the ones without a placement count too.
        pairs = self.queryset(exclude_filter=exclude_filter).values_list(field, "id").distinct()
        return Counter(fid for fid, _ in pairs if fid is not None)

    def _placement_order(self):
        field, descending, nulls_last = self.PLACEMENT_SORT.get(self.order, self.PLACEMENT_SORT[""])
        expression = F(field).desc(nulls_last=nulls_last) if descending else F(field).asc(nulls_last=nulls_last)
        return field, expression

    def page_queryset(self) -> QuerySet:
        """The listed colleagues in list order, with what their cards show."""
        qs = self.listed().select_related("suborganization")
        field, placement_order = self._placement_order()
        matching = self.filters.matching_placements()
        qs = qs.prefetch_related(
            Prefetch(
                "placements",
                queryset=annotate_placement_dates(Placement.objects.filter(id__in=matching.values("id")))
                .select_related("service__assignment", "service__skill")
                .order_by(placement_order, "id"),
                to_attr="current_placements",
            )
        )
        if self.order in ("name", "-name"):
            # Colleagues without a placement fall in among the others.
            return qs.order_by(self.order, "id")
        # The colleague sorts where their first matching placement would.
        first = matching.filter(colleague=OuterRef("pk")).order_by(placement_order)
        qs = qs.annotate(has_placement=Exists(first), sort_key=Subquery(first.values(field)[:1]))
        _, descending, nulls_last = self.PLACEMENT_SORT.get(self.order, self.PLACEMENT_SORT[""])
        key = F("sort_key").desc(nulls_last=nulls_last) if descending else F("sort_key").asc(nulls_last=nulls_last)
        # Without a placement there is nothing to sort on, so those come last, by name.
        return qs.order_by(F("has_placement").desc(), key, "name", "id")

    def cards(self, colleagues: list[Colleague]) -> list[dict]:
        """One card per colleague, its text ready to render.

        A placed colleague's card names the assignments they are placed on and
        their period; one without says "Nu geen opdracht", or how many current
        opdrachten they manage as business manager.
        """
        owned = self._owned_counts([c.id for c in colleagues if not c.current_placements])
        return [self._card(colleague, owned.get(colleague.id, 0)) for colleague in colleagues]

    def _card(self, colleague: Colleague, owned_count: int) -> dict:
        placements = colleague.current_placements
        assignments = list(dict.fromkeys(p.service.assignment for p in placements))
        if not assignments:
            # "Nu": a planned placement may be in the panel, not on the card.
            assignment_text = (
                f"Business Manager van {count_label(owned_count, 'opdracht', 'opdrachten')}"
                if owned_count
                else "Nu geen opdracht"
            )
        elif len(assignments) == 1:
            assignment_text = assignments[0].name
        else:
            assignment_text = count_label(len(assignments), "opdracht", "opdrachten")
        return {
            "name": colleague.name,
            "suborganization": colleague.suborganization,
            "roles": list(dict.fromkeys(p.service.skill.name for p in placements if p.service.skill)),
            "assignment_text": assignment_text,
            "period_text": _period_text(assignments) if assignments else "",
            # A person opens the colleague panel, whatever their number of
            # opdrachten; its cards lead on to each opdracht.
            "panel_url": build_panel_url(self.request, collega=colleague.public_id),
        }

    def _owned_counts(self, colleague_ids: list[int]) -> dict[int, int]:
        """Current opdrachten per business manager, for the cards without a placement.

        Ended opdrachten stay out: the card names no history, which is only for
        the colleague and business managers to see, in the panel. So every
        viewer gets the same card.
        """
        if not colleague_ids:
            return {}
        today = timezone.now().date()
        current = Q(owned_assignments__end_date__isnull=True) | Q(owned_assignments__end_date__gte=today)
        # Like the list itself, an opdracht at a hidden organization does not count,
        # also when it has a visible one too: a subquery, as a negated join would
        # judge each organization row on its own.
        excluded_org_ids = get_excluded_org_ids()
        if excluded_org_ids:
            hidden = Assignment.objects.filter(organizations__id__in=excluded_org_ids)
            current &= ~Q(owned_assignments__in=hidden)
        return dict(
            Colleague.objects.filter(id__in=colleague_ids)
            .annotate(owned_count=Count("owned_assignments", filter=current, distinct=True))
            .values_list("id", "owned_count")
        )


class AssignmentOverview(_Overview):
    """The opdracht weergave: one card per opdracht with a placement that matches."""

    GROUP_FIELD = "service__assignment_id"
    # Sorting on colleague name says nothing here, where one card is a whole team.
    SORT_OPTIONS = ["assignment", "-assignment", "end_date", "-end_date"]
    DEFAULT_SORT_LABEL = "Laatst gewijzigd"
    COUNT_NOUNS = ("opdracht", "opdrachten")
    EMPTY_TEXT = "Geen opdrachten gevonden"

    SORT_FIELDS = {"assignment": "name", "end_date": "end_date"}

    def queryset(self, *, exclude_filter=None) -> QuerySet:
        matching = self.filters.matching_placements(exclude_filter=exclude_filter)
        return Assignment.objects.filter(Exists(matching.filter(service__assignment=OuterRef("pk"))))

    def page_queryset(self) -> QuerySet:
        """The listed opdrachten in list order, with their opdrachtgevers primary first."""
        qs = self.listed().prefetch_related(
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
        if self.order:
            field = F(self.SORT_FIELDS[self.order.lstrip("-")])
            key = field.desc() if self.order.startswith("-") else field.asc()
        else:
            # No modified-at on the model, so the audit log stands in. Nulls last:
            # events age out of retention.
            qs = qs.annotate(
                last_change=Subquery(
                    Event.objects.filter(object_type="Assignment", object_id=OuterRef("pk"))
                    .order_by("-timestamp")
                    .values("timestamp")[:1]
                )
            )
            key = F("last_change").desc(nulls_last=True)
        return qs.order_by(key, "id")

    def cards(self, assignments: list[Assignment]) -> list[dict]:
        """One card per assignment, showing its FULL team.

        The team is fetched separately rather than read off the matching
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
                timezone.now().date(),
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


class PlacementOverviewView(View):
    """Wie zit waar?: one card per colleague or per opdracht (``?weergave=``)."""

    template_name = "placements.html"
    paginate_by = 60
    page_kwarg = PAGE_PARAM
    # Set by ui_handlers.js when the banner is dismissed.
    MISSING_OPDRACHTEN_COOKIE = "wies_missing_opdrachten_dismissed"

    VIEW_DEFAULT = "persoon"
    VIEW_OPTIONS = [
        {"value": "persoon", "label": "Persoon", "icon": "person"},
        {"value": "opdracht", "label": "Opdracht", "icon": "business-suitcase"},
    ]
    OVERVIEWS: dict[str, type[_Overview]] = {"persoon": ColleagueOverview, "opdracht": AssignmentOverview}

    SORT_LABELS = {
        "name": "Naam (A-Z)",
        "-name": "Naam (Z-A)",
        "assignment": "Opdracht (A-Z)",
        "-assignment": "Opdracht (Z-A)",
        "-end_date": "Einddatum (nieuwste eerst)",
        "end_date": "Einddatum (oudste eerst)",
    }

    def get(self, request, *args, **kwargs):
        if is_filter_modal_request(request):
            return filter_modal_response(request, self._filter_groups(self._active_filters()))  # "Meer..."
        if is_client_modal_request(request):
            return client_modal_response(request, self.org_counts())  # opdrachtgever "Meer..."
        # The target, not a panel param: after a page load with ?collega=, the
        # weergave toggle and sort links keep it in their url, and want the results.
        if is_side_panel_request(request):
            return side_panel_response(request)

        # The templates nest: the page holds the results, the results hold the
        # cards. Each layer's context builds on the one inside it.
        htmx = "HX-Request" in request.headers
        if htmx and request.GET.get(self.page_kwarg):
            return TemplateResponse(request, "parts/placement_cards.html", self._cards_context())  # "Meer tonen"
        if htmx:
            # A filter change.
            return TemplateResponse(request, "parts/placement_results.html", self._results_context())
        return TemplateResponse(request, self.template_name, self._page_context())

    @property
    def active_view(self) -> str:
        """The requested ?weergave=, falling back to the default for unknown values."""
        requested = self.request.GET.get("weergave") or ""
        return requested if requested in self.OVERVIEWS else self.VIEW_DEFAULT

    @cached_property
    def filters(self) -> PlacementFilters:
        return PlacementFilters(self.request)

    @cached_property
    def overview(self) -> _Overview:
        return self.OVERVIEWS[self.active_view](self.filters)

    def org_counts(self) -> Counter[int]:
        """Cards per opdrachtgever in the active weergave, for the opdrachtgever picker."""
        return self.overview.org_counts()

    def _view_url(self, value: str) -> str:
        """URL for a weergave: keeps the filters and search, drops page and order.

        The sort options differ per view, so an ?order= from the other view would
        not resolve here.
        """
        dropped = (self.page_kwarg, "order")
        if value == self.VIEW_DEFAULT:
            return rebuild_url(reverse("home"), self.request.GET, drop=(*dropped, "weergave"))
        return rebuild_url(reverse("home"), self.request.GET, drop=dropped, weergave=value)

    def _active_filters(self) -> dict:
        """The selected values per filter, opdrachtgever aside (``add_org_filter_context`` adds it)."""
        active_filters: dict = {}

        loopt_af_values = set(self.request.GET.getlist("loopt_af"))
        if loopt_af_values:
            active_filters["loopt_af"] = loopt_af_values

        # Multi-select facets carry public_ids. A value that resolves to nothing
        # still counts, so an empty list always comes with a way to clear it.
        rol_filter = self.filters.facets("rol", Skill).active_values
        if rol_filter:
            active_filters["rol"] = rol_filter

        label_filter = self.filters.facets("labels", Label).active_values
        if label_filter:
            active_filters["labels"] = label_filter

        suborganization_filter = self.filters.facets("onderdeel", Suborganization).active_values
        if suborganization_filter:
            active_filters["onderdeel"] = suborganization_filter
        return active_filters

    def _filter_groups(self, active_filters: dict) -> list[dict]:
        """The sidebar's filter groups, each option with the cards it would leave.

        The "Meer..." sheet needs nothing else, so it is built from these alone.
        """
        overview = self.overview
        filters = self.filters

        # Each filter category counts the cards under every filter except its own.
        label_filter_groups = []
        for category in label_categories_for_everyone():
            cat_label_counts = overview.colleague_counts("labels__id", exclude_filter=category.id)

            options = [{"value": "", "label": ""}]
            selected_values = []
            for label in Label.objects.filter(category=category):
                options.append(
                    {
                        "value": str(label.public_id),
                        "label": f"{label.name}",
                        "category_color": category.color,
                        "count": cat_label_counts.get(label.id, 0),
                    }
                )
                if str(label.public_id) in active_filters.get("labels", set()):
                    options[-1]["selected"] = True
                    selected_values.append(str(label.public_id))

            label_filter_groups.append(
                {
                    "type": "select-multi",
                    "name": "labels",
                    "label": category.name,
                    "options": options,
                    "selected_values": selected_values,
                }
            )

        # Onderdeel filter group (one per colleague)
        suborg_counts = overview.colleague_counts("suborganization_id", exclude_filter="onderdeel")

        suborganization_options = [{"value": "", "label": ""}]
        suborganization_selected_values = []
        for suborganization in Suborganization.objects.all():
            suborganization_options.append(
                {
                    "value": str(suborganization.public_id),
                    "label": suborganization.name,
                    "count": suborg_counts.get(suborganization.id, 0),
                }
            )
            if str(suborganization.public_id) in active_filters.get("onderdeel", set()):
                suborganization_options[-1]["selected"] = True
                suborganization_selected_values.append(str(suborganization.public_id))

        suborganization_filter_group = {
            "type": "select-multi",
            "name": "onderdeel",
            "label": "Onderdeel",
            "options": suborganization_options,
            "selected_values": suborganization_selected_values,
        }

        skill_counts = overview.placement_counts("service__skill__id", exclude_filter="rol")

        skill_options = [{"value": "", "label": ""}]
        skill_selected_values = []
        for skill in Skill.objects.order_by("name"):
            option = {"value": str(skill.public_id), "label": skill.name, "count": skill_counts.get(skill.id, 0)}
            if str(skill.public_id) in active_filters.get("rol", set()):
                option["selected"] = True
                skill_selected_values.append(str(skill.public_id))
            skill_options.append(option)

        org_counts = overview.org_counts()

        # TODO: this can be become an object to help defining correctly and performing extra preprocessing on context
        # introduce value_key, label_key:
        filter_groups = [
            {
                "type": "modal",
                "name": "organisatie",
                "label": "Opdrachtgever",
                "top_options": get_top_org_options(
                    set(filters.facets("org", OrganizationUnit).ids),
                    org_counts,
                    selected_self_ids=set(filters.facets("org_self", OrganizationUnit).ids),
                    selected_type_labels=set(filters.org_type_filter),
                    selected_type_in=filters.org_type_in_filter,
                ),
            },
            {
                "type": "select-multi",
                "name": "rol",
                "label": "Rol",
                "options": skill_options,
                "selected_values": skill_selected_values,
            },
            suborganization_filter_group,
            *label_filter_groups,
            {
                "type": "select-multi",
                "name": "loopt_af",
                "label": "Loopt af",
                "options": overview.loopt_af_options(),
                "selected_values": list(active_filters.get("loopt_af", [])),
            },
        ]
        finalize_filter_groups(filter_groups)
        return filter_groups

    def _cards_context(self) -> dict:
        """The page of cards and the link to the next one: all that "Meer tonen" renders."""
        # get_page clamps a page number that is out of range or no number at all.
        paginator = Paginator(self.overview.page_queryset(), self.paginate_by)
        page = paginator.get_page(self.request.GET.get(self.page_kwarg))
        next_page_url = (
            rebuild_url("", self.request.GET, drop=PANEL_PARAMS, **{PAGE_PARAM: page.next_page_number()})
            if page.has_next()
            else None
        )
        return {
            "result_count": paginator.count,
            "cards": self.overview.cards(list(page.object_list)),
            "active_view": self.active_view,
            "next_page_url": next_page_url,
        }

    def _results_context(self) -> dict:
        """The cards plus what a filter change re-renders around them: the weergave
        toggle, the sort control, the chips and the filter sidebar (swapped in out of band)."""
        overview = self.overview
        filters = self.filters
        active_view = self.active_view
        context = self._cards_context()
        result_count = context["result_count"]
        context |= {
            "render_filter_fields_oob": "HX-Request" in self.request.headers,
            # The template compares against it rather than hardcoding the name, so
            # changing the default does not silently break the hidden field.
            "default_view": self.VIEW_DEFAULT,
            "view_options": [
                {
                    **option,
                    "url": self._view_url(option["value"]),
                    "selected": option["value"] == active_view,
                    "count": result_count
                    if option["value"] == active_view
                    else self.OVERVIEWS[option["value"]](filters).listed().count(),
                }
                for option in self.VIEW_OPTIONS
            ],
            "result_announcement": count_label(result_count, *overview.COUNT_NOUNS),
            "empty_text": overview.EMPTY_TEXT,
            **sort_control_context(
                overview.order,
                [(value, self.SORT_LABELS[value]) for value in overview.SORT_OPTIONS],
                overview.DEFAULT_SORT_LABEL,
            ),
            "filter_target_url": reverse("home"),
            "search_filter": self.request.GET.get("zoek"),
        }

        active_filters = self._active_filters()
        context["filter_groups"] = self._filter_groups(active_filters)
        # The chips; the opdrachtgever one also adds its value to active_filters.
        filters.add_org_filter_context(context, active_filters)
        filters.add_unknown_filter_chips(context, {"rol": Skill, "labels": Label, "onderdeel": Suborganization})
        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)
        return context

    def _page_context(self) -> dict:
        """The results plus what only the full page has: the side panel and the
        missing-opdrachten banner."""
        return self._results_context() | {
            # A full page load with ?collega= or ?opdracht= opens the panel too.
            "panel_data": resolve_side_panel(self.request),
            "missing_opdrachten_cookie": self.MISSING_OPDRACHTEN_COOKIE,
            "show_missing_opdrachten_banner": self.MISSING_OPDRACHTEN_COOKIE not in self.request.COOKIES,
        }


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
        panel_data = build_placement_edit_panel_data(
            placement, request, form=form, parent_url=return_path, back_text=request.POST.get("back_text")
        )
        return render(request, "parts/placement_edit_panel_content.html", {"panel_data": panel_data})

    save_placement_edit(request, placement, specs, form.cleaned_data)
    # The panel that HX-Location fetches swaps the banner in out of band.
    messages.success(request, f"Plaatsing van {placement.colleague.name} is aangepast.")

    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response
