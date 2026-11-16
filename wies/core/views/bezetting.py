"""The bezetting (occupancy) overview."""

from django.core.paginator import Paginator
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from wies.core.models import (
    Label,
    Suborganization,
)
from wies.core.public_id import resolve_facet
from wies.core.roles import (
    business_management_access_required,
)
from wies.core.services.occupancy import (
    STATUS_BENCH,
    STATUS_ENDS_SOON,
    STATUS_PARTIAL,
    STATUS_VALUES,
    bezetting_filter_groups,
    colleague_occupancy,
    horizon_days,
    labels_by_category,
    month_ticks,
    occupancy_summary,
    row_has_status,
    rows_in_display_order,
    timeline_horizon,
    today_marker_pct,
)
from wies.core.services.urls import PAGE_PARAM, rebuild_url

from ._common import PANEL_PARAMS, build_panel_url, is_side_panel_request
from .filters import finalize_filter_groups
from .panels import (
    assignment_create_button,
    resolve_side_panel,
)


def _bezetting_status_group(selected, summary):
    """The summary cards as a filter group, for when they do not fit the row.

    Same values and counts as the cards, so toggling either keeps one state.
    """
    options = [{"value": "", "label": ""}]
    for value, label, count in (
        (STATUS_BENCH, "Op de bank", summary["bench_count"]),
        (STATUS_PARTIAL, "Deels beschikbaar", summary["partial_count"]),
        (STATUS_ENDS_SOON, "Eindigt binnen 3 maanden", summary["ends_soon_count"]),
    ):
        option = {"value": value, "label": label, "count": count}
        if value in selected:
            option["selected"] = True
        options.append(option)
    real_options = options[1:]
    return {
        "type": "select-multi",
        "name": "status",
        "label": "Status",
        "options": options,
        "selected_values": list(selected),
        # Finalized by hand, outside finalize_filter_groups: that keeps the top
        # three by count and hides the rest behind "Meer…", which would drop a
        # status's hidden input and leave its card dead.
        "group_id": "status",
        "top_options": real_options,
        "has_more": False,
    }


BEZETTING_PAGE_SIZE = 60


@business_management_access_required
def bezetting(request):
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
    today = timezone.now().date()

    # Side panel: reuse the shared machinery. A row click opens the colleague
    # panel (?collega); links inside that panel open an opdracht (?opdracht)
    # panel, exactly like on "Wie zit waar?".
    panel_data = resolve_side_panel(request, allow_create=True)

    # HTMX panel requests return just the panel content, like WZW.
    if is_side_panel_request(request) and panel_data:
        return render(request, panel_data["panel_content_template"], {"panel_data": panel_data})

    # Onderdeel (suborganisation) and label-category filters, resolved from the URL.
    # Labels are OR within a category and AND between categories (like "Wie zit
    # waar?"); each label category becomes its own filter group under the shared
    # ``labels`` param, and the onderdeel is its own group.
    suborganization_facet = resolve_facet(Suborganization, request.GET.getlist("onderdeel"))
    labels = resolve_facet(Label, request.GET.getlist("labels"))
    labels_by_cat = labels_by_category(labels.ids)
    search = request.GET.get("zoek", "").strip()

    rows = colleague_occupancy(
        today, suborganization_ids=suborganization_facet.ids, labels_by_category=labels_by_cat, search=search
    )
    for row in rows:
        row.colleague.panel_url = build_panel_url(request, collega=row.colleague.public_id)

    # Summary-card counts follow onderdeel, labels and the search term (they all
    # narrowed the queryset above) but not the status filter, which is applied
    # after this: a card has to keep showing what it would select.
    summary = occupancy_summary(rows)

    # Status facet: the three summary cards, as independent OR-toggles. Derived
    # from the built rows (not a queryset column), so it filters here in-memory.
    selected_statuses = [s for s in request.GET.getlist("status") if s in STATUS_VALUES]
    if selected_statuses:
        rows = [r for r in rows if any(row_has_status(r, s) for s in selected_statuses)]

    # Filter sheet: one select-multi group per facet, with cross-filtered counts,
    # driving the shared filter panel (parts/filter_sidebar.html). No "Rol" group —
    # everyone on this page is a consultant.
    filter_groups = bezetting_filter_groups(suborganization_facet, labels, labels_by_cat)
    # Status also lives in the sheet, not only on the cards: on a narrow window
    # the cards are hidden, and a filter you cannot reach is a filter you cannot
    # switch off.
    finalize_filter_groups(filter_groups)
    filter_groups.insert(0, _bezetting_status_group(selected_statuses, summary))

    active_filters = {}
    if suborganization_facet.active_values:
        active_filters["onderdeel"] = suborganization_facet.active_values
    if labels.active_values:
        active_filters["labels"] = labels.active_values
    if selected_statuses:
        active_filters["status"] = selected_statuses

    page = Paginator(rows_in_display_order(rows), BEZETTING_PAGE_SIZE).get_page(request.GET.get("pagina"))
    next_page_url = (
        rebuild_url(request.path, request.GET, drop=PANEL_PARAMS, **{PAGE_PARAM: page.next_page_number()})
        if page.has_next()
        else None
    )

    context = {
        "rows": page.object_list,
        "row_count": page.paginator.count,
        "next_page_url": next_page_url,
        "search_filter": search,
        "panel_data": panel_data,
        "today_pct": today_marker_pct(),
        "horizon_days": horizon_days(),
        "today": today,
        "horizon": timeline_horizon(today),
        "month_ticks": month_ticks(today),
        **summary,
        "selected_statuses": selected_statuses,
        "filter_groups": filter_groups,
        "active_filters": active_filters,
        "filter_target_url": reverse("bezetting"),
        "filter_modal_group_id": request.GET.get("filter_modal", ""),
        "primary_button": assignment_create_button(request),
    }

    # HTMX filter change: return just the results block; the filter sheet swaps
    # back OOB (see parts/bezetting_results.html). The "Meer…" sheet reuses the
    # shared template, exactly like the user list.
    if "HX-Request" in request.headers:
        if request.GET.get("filter_modal"):
            return render(request, "parts/filter_options_modal.html", context)
        # "Meer tonen" replaces itself with the next page of rows.
        if request.GET.get("pagina"):
            return render(request, "parts/bezetting_rows.html", context)
        return render(request, "parts/bezetting_results.html", context)

    return render(request, "bezetting.html", context)
