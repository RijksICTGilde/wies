"""The bezetting (occupancy) overview."""

from functools import cached_property

from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.decorators import method_decorator

from wies.core.models import (
    Label,
    Suborganization,
)
from wies.core.roles import (
    ROLE_CONSULTANT,
    business_management_access_required,
)
from wies.core.services.occupancy import (
    STATUS_BENCH,
    STATUS_ENDS_SOON,
    STATUS_PARTIAL,
    STATUS_VALUES,
    colleague_occupancy,
    consultant_colleagues,
    horizon_days,
    month_ticks,
    occupancy_summary,
    row_has_status,
    rows_in_display_order,
    timeline_horizon,
    today_marker_pct,
)

from ._common import build_panel_url
from .filters import Choice, ModelFacet, label_facets, model_choices, select_multi_group
from .listing import FacetedListView, ListSearch
from .panels import assignment_create_button


class BezettingSearch(ListSearch):
    """The consultants on the timeline under the request's search and filters.

    Labels are OR within a category and AND between categories, like "Wie zit
    waar?"; each label category is its own filter group under the shared
    ``labels`` param, and the onderdeel is its own group. No "Rol" group:
    everyone on this page is a consultant. The filters offer only the values a
    consultant has.
    """

    def scope(self):
        qs = consultant_colleagues()
        if self.query:
            # Like the search box on the user list.
            qs = qs.filter(Q(name__icontains=self.query) | Q(email__icontains=self.query))
        return qs

    def build_facets(self):
        used_labels = (
            Label.objects.filter(colleagues__user__groups__name=ROLE_CONSULTANT)
            .distinct()
            .select_related("category")
            .order_by("category__name", Lower("name"))
        )
        by_category: dict[int, tuple] = {}
        for label in used_labels:
            by_category.setdefault(label.category_id, (label.category, []))[1].append(label)
        return [
            *label_facets(self.resolver("labels", Label), by_category.values(), lookup="labels__id"),
            ModelFacet(
                "onderdeel",
                "Onderdeel",
                self.resolver("onderdeel", Suborganization),
                lookup="suborganization_id",
                choices=lambda: model_choices(
                    Suborganization.objects.filter(colleagues__user__groups__name=ROLE_CONSULTANT).distinct()
                ),
            ),
        ]


BEZETTING_PAGE_SIZE = 60


def _status_group(selected: list[str], summary: dict) -> dict:
    """The summary cards as a filter group, for when they do not fit the row.

    Same values and counts as the cards, so toggling either keeps one state.
    Finalized here rather than by finalize_filter_groups: that keeps the top
    three by count and hides the rest behind "Meer…", which would drop a
    status's hidden input and leave its card dead.
    """
    choices = [
        Choice(STATUS_BENCH, "Op de bank", STATUS_BENCH),
        Choice(STATUS_PARTIAL, "Deels beschikbaar", STATUS_PARTIAL),
        Choice(STATUS_ENDS_SOON, "Eindigt binnen 3 maanden", STATUS_ENDS_SOON),
    ]
    counts = {
        STATUS_BENCH: summary["bench_count"],
        STATUS_PARTIAL: summary["partial_count"],
        STATUS_ENDS_SOON: summary["ends_soon_count"],
    }
    group = select_multi_group("status", "Status", choices, selected, counts)
    group.update(group_id="status", top_options=group["options"][1:], has_more=False)
    return group


@method_decorator(business_management_access_required, name="dispatch")
class BezettingListView(FacetedListView):
    """ "Bezetting" — the business-manager occupancy timeline.

    Rows are colleagues, sorted most-pressing first (bench → full). A row click
    opens the shared colleague side panel via the ``collega`` param, exactly like
    the "Wie zit waar?" table.

    Paged from the in-memory row list, not the queryset: the sort order is a
    derived property of the built rows, not a column. So every page costs the
    same database work and only the HTML shrinks, which is what the paging is
    for here. Moving it into the queryset means moving the sort into annotations
    and is its own change.
    """

    search_class = BezettingSearch
    template_name = "bezetting.html"
    # HTMX filter change: just the results block; the filter sheet swaps back
    # OOB. The "Meer…" sheet reuses the shared template, like the user list.
    results_template = "parts/bezetting_results.html"
    # "Meer tonen" replaces itself with the next page of rows.
    rows_template = "parts/bezetting_rows.html"
    filter_url_name = "bezetting"
    page_size = BEZETTING_PAGE_SIZE
    side_panel = True
    allow_create = True

    @cached_property
    def today(self):
        return timezone.now().date()

    @cached_property
    def all_rows(self):
        rows = colleague_occupancy(self.today, self.search.filtered)
        for row in rows:
            row.colleague.panel_url = build_panel_url(self.request, collega=row.colleague.public_id)
        return rows

    @cached_property
    def summary(self) -> dict:
        """Follows the search and the filters, but not the status filter, which
        is applied after it: a card has to keep showing what it would select."""
        return occupancy_summary(self.all_rows)

    @cached_property
    def selected_statuses(self) -> list[str]:
        return [status for status in self.request.GET.getlist("status") if status in STATUS_VALUES]

    def page_source(self):
        # Status is derived from the built rows (not a queryset column), so it
        # filters here, in memory: the three cards as independent OR-toggles.
        rows = self.all_rows
        if self.selected_statuses:
            rows = [r for r in rows if any(row_has_status(r, s) for s in self.selected_statuses)]
        return rows_in_display_order(rows)

    def row_context(self, page):
        return {
            "rows": page.object_list,
            "row_count": page.paginator.count,
            "today_pct": today_marker_pct(),
            "horizon_days": horizon_days(),
            "month_ticks": month_ticks(self.today),
        }

    def filter_context(self):
        context = super().filter_context()
        # Status also lives in the sheet, not only on the cards: on a narrow
        # window the cards are hidden, and a filter you cannot reach is a filter
        # you cannot switch off.
        context["filter_groups"] = [_status_group(self.selected_statuses, self.summary), *context["filter_groups"]]
        if self.selected_statuses:
            context["active_filters"] = {**context["active_filters"], "status": self.selected_statuses}
            context["active_filter_count"] = len(context["active_filters"])
        context["search_filter"] = self.search.query
        return context

    def extra_context(self):
        return {
            "today": self.today,
            "horizon": timeline_horizon(self.today),
            **self.summary,
            "selected_statuses": self.selected_statuses,
            "primary_button": assignment_create_button(self.request),
        }
