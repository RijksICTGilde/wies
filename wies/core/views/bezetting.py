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
from .filters import (
    Choice,
    Filter,
    finalize_filter_groups,
    label_filters,
    model_choices,
    model_filter,
    select_multi_group,
)
from .listing import FacetedListView, ListSearch
from .panels import assignment_create_button

BEZETTING_PAGE_SIZE = 60

STATUS_LABELS = {
    STATUS_BENCH: "Op de bank",
    STATUS_PARTIAL: "Deels beschikbaar",
    STATUS_ENDS_SOON: "Eindigt binnen 3 maanden",
}


class BezettingSearch(ListSearch):
    """The consultants on the timeline under the request's search and filters.

    Labels are OR within a category and AND between categories, like "Wie zit
    waar?"; each label category is its own sidebar group under the shared
    ``labels`` param, and the onderdeel is its own group. No "Rol" group:
    everyone on this page is a consultant. The filters offer only the values a
    consultant has.

    The status is not a column but derived from the built timeline rows, so it
    filters those rows, after the queryset.
    """

    @cached_property
    def today(self):
        return timezone.now().date()

    @cached_property
    def scope(self):
        qs = consultant_colleagues()
        if self.query:
            # Like the search box on the user list.
            qs = qs.filter(Q(name__icontains=self.query) | Q(email__icontains=self.query))
        return qs

    # The filters

    @cached_property
    def labels(self):
        return label_filters(self.resolver("labels", Label), "labels__id")

    @cached_property
    def onderdeel(self):
        return model_filter("onderdeel", self.resolver("onderdeel", Suborganization), "suborganization_id")

    @cached_property
    def status(self):
        # Not active: it narrows the rows below, not the queryset.
        selected = [status for status in self.params.getlist("status") if status in STATUS_VALUES]
        return Filter("status", active=False, narrow=lambda qs: qs, values=selected)

    def filters(self):
        return [*self.labels, self.onderdeel, self.status]

    # The rows

    @cached_property
    def all_rows(self):
        """Every consultant under the queryset filters, before the status filter."""
        rows = colleague_occupancy(self.today, self.filtered())
        for row in rows:
            row.colleague.panel_url = build_panel_url(self.request, collega=row.colleague.public_id)
        return rows

    @cached_property
    def summary(self) -> dict:
        """Follows the search and the filters, but not the status filter, which
        is applied after it: a card has to keep showing what it would select."""
        return occupancy_summary(self.all_rows)

    @cached_property
    def rows(self):
        """Most pressing first; the status cards as independent OR-toggles."""
        rows = self.all_rows
        if self.status.values:
            rows = [r for r in rows if any(row_has_status(r, s) for s in self.status.values)]
        return rows_in_display_order(rows)

    # The sidebar

    @cached_property
    def filter_groups(self):
        used_labels = (
            Label.objects.filter(colleagues__user__groups__name=ROLE_CONSULTANT)
            .distinct()
            .select_related("category")
            .order_by("category__name", Lower("name"))
        )
        categories: dict[int, tuple] = {}
        for label in used_labels:
            categories.setdefault(label.category_id, (label.category, []))[1].append(label)
        return finalize_filter_groups(
            [
                self._status_group(),
                *self.label_groups(categories.values(), "labels__id"),
                select_multi_group(
                    "onderdeel",
                    "Onderdeel",
                    model_choices(
                        Suborganization.objects.filter(colleagues__user__groups__name=ROLE_CONSULTANT).distinct()
                    ),
                    self.onderdeel.values,
                    self.count("onderdeel", "suborganization_id"),
                ),
            ]
        )

    def _status_group(self) -> dict:
        """The summary cards as a filter group, for when they do not fit the row.

        Status also lives in the sheet, not only on the cards: on a narrow
        window the cards are hidden, and a filter you cannot reach is a filter
        you cannot switch off. Same values and counts as the cards, so toggling
        either keeps one state. All three always show: finalize_filter_groups
        would keep the top three by count and hide the rest behind "Meer…",
        which would drop a status's hidden input and leave its card dead.
        """
        counts = {
            STATUS_BENCH: self.summary["bench_count"],
            STATUS_PARTIAL: self.summary["partial_count"],
            STATUS_ENDS_SOON: self.summary["ends_soon_count"],
        }
        choices = [Choice(status, label, status) for status, label in STATUS_LABELS.items()]
        group = select_multi_group("status", "Status", choices, self.status.values, counts)
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

    def page_source(self):
        return self.search.rows

    def rows(self, page):
        return {
            "rows": page.object_list,
            "row_count": page.paginator.count,
            "today_pct": today_marker_pct(),
            "horizon_days": horizon_days(),
            "month_ticks": month_ticks(self.search.today),
        }

    def controls(self):
        return {
            "today": self.search.today,
            "horizon": timeline_horizon(self.search.today),
            **self.search.summary,
            "selected_statuses": self.search.status.values,
            "primary_button": assignment_create_button(self.request),
        }
