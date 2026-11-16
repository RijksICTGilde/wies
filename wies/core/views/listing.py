"""The faceted lists: a search per request, and a view that renders its fragments.

Every list page (Wie zit waar?, Aanvragen, Gebruikers, Bezetting) is the same
thing: a selection narrowed by a search term and a set of facets, shown a page
at a time, with per-option counts in the filter panel. ``ListSearch`` is that
selection for one request, parsed once; ``FacetedListView`` answers the
requests the page makes, each with only the work that response needs.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar

from django.core.paginator import Page, Paginator
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views import View

from wies.core.public_id import FacetResolver
from wies.core.querysets import count_distinct
from wies.core.services.organizations import get_excluded_org_ids
from wies.core.services.urls import PAGE_PARAM, rebuild_url

from ._common import PANEL_PARAMS, is_side_panel_request
from .filters import Facet, OrgFacet, finalize_filter_groups
from .panels import resolve_side_panel

if TYPE_CHECKING:
    from collections import Counter
    from collections.abc import Sequence

    from django.db.models import Model, QuerySet
    from django.http import HttpRequest


class ListSearch:
    """One list's selection for one request: scope, search term and facets.

    Subclasses give the ``scope`` (what the list can show at all, with the
    search applied) and the ``build_facets``. Everything is computed on first
    use and kept for the request, so a count, a chip and the page itself never
    parse the same parameter twice.
    """

    # Counts count distinct values of this field (one card per colleague, say)
    # instead of rows. None: every row is a card.
    group_field: ClassVar[str | None] = None
    # Whether the filtered queryset needs a DISTINCT: a facet that joins a
    # to-many relation repeats rows otherwise.
    distinct: ClassVar[bool] = True
    # The path to the opdrachtgever id, for lists with that filter.
    org_lookup: ClassVar[str] = ""

    def __init__(self, request: HttpRequest):
        self.request = request
        self.params = request.GET
        self._counts: dict[tuple[str | None, str], Counter] = {}

    @cached_property
    def query(self) -> str:
        """The search term, stripped; empty for no search."""
        return self.params.get("zoek", "").strip()

    @cached_property
    def resolver(self) -> FacetResolver:
        return FacetResolver(self.request, self.facet_scopes())

    def facet_scopes(self) -> dict[type[Model], QuerySet]:
        """Per model, the rows this list's facets may resolve to; see ``resolve_facet``."""
        return {}

    @cached_property
    def excluded_org_ids(self) -> set[int]:
        return get_excluded_org_ids()

    def scope(self) -> QuerySet:
        """What the list shows before any facet: the selection, not its order."""
        raise NotImplementedError

    def build_facets(self) -> list[Facet]:
        raise NotImplementedError

    @cached_property
    def scoped(self) -> QuerySet:
        return self.scope()

    @cached_property
    def facets(self) -> list[Facet]:
        return self.build_facets()

    @cached_property
    def org(self) -> OrgFacet | None:
        return next((facet for facet in self.facets if isinstance(facet, OrgFacet)), None)

    def filtered_except(self, excluded: Facet | None) -> QuerySet:
        """The scope under every active facet but ``excluded``."""
        qs = self.scoped
        for facet in self.facets:
            if facet is not excluded and facet.active:
                qs = facet.apply(qs)
        return qs.distinct() if self.distinct else qs

    @cached_property
    def filtered(self) -> QuerySet:
        return self.filtered_except(None)

    def count_by(self, facet: Facet, lookup: str) -> Counter:
        """Groups per value of ``lookup``, under every facet but ``facet``.

        An inactive facet excludes nothing, so all of them share one query.
        """
        key = (facet.key if facet.active else None, lookup)
        if key not in self._counts:
            self._counts[key] = count_distinct(
                self.filtered_except(facet if facet.active else None), lookup, self.group_field
            )
        return self._counts[key]

    def org_counts(self) -> Counter:
        """Groups per opdrachtgever under every filter but the opdrachtgever's.

        For the sidebar and the opdrachtgever picker alike, so their numbers
        agree. Lists whose cards are not rows of one queryset override this.
        """
        return self.count_by(self.org, self.org_lookup)

    @cached_property
    def active_filters(self) -> dict[str, Any]:
        """``{param: values}`` of every active facet, values in URL order."""
        active: dict[str, Any] = {}
        for facet in self.facets:
            active.update(facet.active_filters())
        return active

    @cached_property
    def unknown_chip_data(self) -> list[dict]:
        return [chip for facet in self.facets for chip in facet.unknown_chips()]

    @cached_property
    def org_chip_data(self) -> list[dict]:
        return self.org.chips() if self.org else []

    @cached_property
    def filter_groups(self) -> list[dict]:
        groups = [group for facet in self.facets if (group := facet.group(facet.counts(self))) is not None]
        finalize_filter_groups(groups)
        return groups


def clamped_page(paginator: Paginator, raw: str | None) -> Page:
    """The requested page, clamped to the pages that exist; page 1 on nonsense.

    A stale "Meer tonen" link or an edited URL lands on a real page rather
    than a 404: the list it belongs to may simply have shrunk since.
    """
    try:
        number = int(raw or 1)
    except ValueError:
        number = 1
    return paginator.page(max(1, min(number, paginator.num_pages)))


class FacetedListView(View):
    """A list page and the fragments it requests, each built from one ``ListSearch``.

    - a side-panel request (``HX-Target: side-panel-content``): the panel only;
      the list is not touched
    - ``?filter_modal=<group_id>``: the full option list of one filter group
    - ``?pagina=N`` (htmx): the next page of rows, for "Meer tonen"
    - any other htmx request (a filter, sort or search change): the results,
      with the filter panel out of band
    - a plain request: the whole page

    Subclasses give the templates, ``page_source`` (what to paginate) and
    ``row_context`` (what a page of it renders as), and add their own
    controls in ``extra_context``.
    """

    search_class: ClassVar[type[ListSearch]]
    template_name: ClassVar[str]
    results_template: ClassVar[str]
    rows_template: ClassVar[str]
    filter_modal_template: ClassVar[str] = "parts/filter_options_modal.html"
    filter_url_name: ClassVar[str]
    page_size: ClassVar[int] = 60
    # Whether the panel params (?collega=, ?opdracht=, ...) open a side panel here.
    side_panel: ClassVar[bool] = False
    # Whether ?nieuwe-opdracht opens the create form as that panel.
    allow_create: ClassVar[bool] = False

    def get(self, request, *args, **kwargs):
        if self.side_panel and is_side_panel_request(request):
            panel_data = self.panel_data
            if panel_data:
                return self.respond(panel_data["panel_content_template"], {"panel_data": panel_data})
        self.search = self.search_class(request)
        if "HX-Request" in request.headers:
            if request.GET.get("filter_modal"):
                return self.respond(self.filter_modal_template, self.filter_context())
            if request.GET.get(PAGE_PARAM):
                return self.respond(self.rows_template, self.rows_context())
            return self.respond(self.results_template, {**self.results_context(), "render_filter_fields_oob": True})
        return self.respond(self.template_name, self.page_context())

    def respond(self, template: str, context: dict) -> TemplateResponse:
        return TemplateResponse(self.request, template, context)

    @cached_property
    def panel_data(self) -> dict | None:
        return resolve_side_panel(self.request, allow_create=self.allow_create)

    def page_source(self) -> Sequence | QuerySet:
        """What is paged: a sliceable, countable sequence in display order."""
        raise NotImplementedError

    def row_context(self, page: Page) -> dict:
        """What a page of ``page_source`` renders as (cards, rows, ...)."""
        raise NotImplementedError

    def extra_context(self) -> dict:
        """The list's own controls next to the results (sort, primary button, ...)."""
        return {}

    @cached_property
    def page(self) -> Page:
        return clamped_page(Paginator(self.page_source(), self.page_size), self.request.GET.get(PAGE_PARAM))

    def rows_context(self) -> dict:
        page = self.page
        next_page_url = (
            rebuild_url(self.request.path, self.request.GET, drop=PANEL_PARAMS, **{PAGE_PARAM: page.next_page_number()})
            if page.has_next()
            else None
        )
        return {
            "page_obj": page,
            "paginator": page.paginator,
            "is_paginated": page.has_other_pages(),
            "next_page_url": next_page_url,
            **self.row_context(page),
        }

    def filter_context(self) -> dict:
        search = self.search
        return {
            "filter_groups": search.filter_groups,
            "active_filters": search.active_filters,
            "active_filter_count": len(search.active_filters),
            "org_chip_data": search.org_chip_data,
            "unknown_chip_data": search.unknown_chip_data,
            "filter_target_url": reverse(self.filter_url_name),
            "filter_modal_group_id": self.request.GET.get("filter_modal", ""),
            "search_filter": self.request.GET.get("zoek"),
        }

    def results_context(self) -> dict:
        return {**self.rows_context(), **self.filter_context(), **self.extra_context()}

    def page_context(self) -> dict:
        context = self.results_context()
        if self.side_panel:
            context["panel_data"] = self.panel_data
        return context
