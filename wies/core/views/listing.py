"""The faceted lists: a search per request, and a view that renders its fragments.

Every list page (Wie zit waar?, Aanvragen, Gebruikers, Bezetting) is the same
thing: a selection narrowed by a search term and a set of filters, shown a
page at a time, with per-option counts in the filter panel. ``ListSearch`` is
that selection for one request, parsed once; ``FacetedListView`` answers the
requests the page makes, each with only the work that response needs.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar

from django.core.paginator import Page, Paginator
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views import View

from wies.core.models import Label
from wies.core.public_id import FacetResolver
from wies.core.querysets import count_distinct
from wies.core.services.organizations import get_excluded_org_ids
from wies.core.services.urls import PAGE_PARAM, rebuild_url

from ._common import PANEL_PARAMS, is_side_panel_request
from .filters import Choice, label_category_param, select_multi_group
from .panels import resolve_side_panel

if TYPE_CHECKING:
    from collections import Counter
    from collections.abc import Iterable, Sequence

    from django.db.models import Model, QuerySet
    from django.http import HttpRequest

    from wies.core.models import LabelCategory

    from .filters import Filter, OrgFilter


class ListSearch:
    """One list's selection for one request: scope, search term and filters.

    A subclass gives its ``scope`` (what the list can show at all, with the
    search applied), its ``filters()`` and its sidebar (``filter_groups``),
    written out in the order it shows. Everything is computed on first use and
    kept for the request, so a count, a chip and the page itself never parse
    the same parameter twice.
    """

    # Counts count distinct values of this field (one card per colleague, say)
    # instead of rows. None: every row is a card.
    group_field: str | None = None
    # Whether the filtered queryset needs a DISTINCT: a filter that joins a
    # to-many relation repeats rows otherwise.
    distinct: ClassVar[bool] = True
    # The opdrachtgever filter and its path to the organization id, on the lists that have one.
    org: OrgFilter | None = None
    org_lookup: ClassVar[str] = ""

    def __init__(self, request: HttpRequest):
        self.request = request
        self.params = request.GET
        self._filtered: dict[str | None, QuerySet] = {}
        self._counts: dict[tuple[str | None, str], Counter] = {}

    @cached_property
    def query(self) -> str:
        """The search term, stripped; empty for no search."""
        return self.params.get("zoek", "").strip()

    @cached_property
    def resolver(self) -> FacetResolver:
        return FacetResolver(self.request, self.facet_scopes())

    def facet_scopes(self) -> dict[type[Model], QuerySet]:
        """Per model, the rows this list's filters may resolve to; see ``resolve_facet``."""
        return {}

    @cached_property
    def excluded_org_ids(self) -> set[int]:
        return get_excluded_org_ids()

    @cached_property
    def scope(self) -> QuerySet:
        """What the list shows before any filter: the selection, not its order."""
        raise NotImplementedError

    def filters(self) -> list[Filter | OrgFilter]:
        raise NotImplementedError

    @cached_property
    def filter_groups(self) -> list[dict]:
        """The sidebar, top to bottom."""
        raise NotImplementedError

    def filtered(self, skip: str | None = None) -> QuerySet:
        """The scope under every active filter, or every one but the ``skip`` param."""
        if skip not in self._filtered:
            qs = self.scope
            for f in self.filters():
                if f.active and f.param != skip:
                    qs = f.narrow(qs)
            self._filtered[skip] = qs.distinct() if self.distinct else qs
        return self._filtered[skip]

    def count(self, skip: str | None, lookup: str) -> Counter:
        """Groups per value of ``lookup``, under every filter but the ``skip`` param.

        Skipping a filter that is not active skips nothing, so those counts
        share one query.
        """
        if not any(f.active and f.param == skip for f in self.filters()):
            skip = None
        if (skip, lookup) not in self._counts:
            self._counts[skip, lookup] = count_distinct(self.filtered(skip), lookup, self.group_field)
        return self._counts[skip, lookup]

    def org_counts(self) -> Counter:
        """Groups per opdrachtgever under every filter but the opdrachtgever's.

        For the sidebar and the opdrachtgever picker alike, so their numbers
        agree. Lists whose cards are not rows of one queryset override this.
        """
        return self.count("org", self.org_lookup)

    def label_groups(
        self,
        categories: Iterable[tuple[LabelCategory, list[Label]]],
        lookup: str,
        *,
        with_color: bool = False,
    ) -> list[dict]:
        """One sidebar group per label category, each counted without its own selection."""
        selected = self.resolver("labels", Label).active_values
        return [
            select_multi_group(
                "labels",
                category.name,
                [
                    Choice(
                        str(label.public_id),
                        label.name,
                        label.pk,
                        {"category_color": category.color} if with_color else {},
                    )
                    for label in labels
                ],
                selected,
                self.count(label_category_param(category.id), lookup),
            )
            for category, labels in categories
        ]

    @cached_property
    def active_filters(self) -> dict[str, Any]:
        """``{param: values}`` of every active filter, values in URL order."""
        active: dict[str, Any] = {}
        for f in self.filters():
            active.update(f.active_filters())
        return active

    @cached_property
    def unknown_chip_data(self) -> list[dict]:
        return [chip for f in self.filters() for chip in f.unknown_chips()]

    @cached_property
    def org_chip_data(self) -> list[dict]:
        return self.org.chips() if self.org else []


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

    A list gives its templates, ``page_source`` (what is paged), ``rows``
    (what a page of it renders as) and ``controls`` (what sits next to the
    results: sort, weergave, primary button).
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

    @classmethod
    def make_search(cls, request: HttpRequest) -> ListSearch:
        return cls.search_class(request)

    def get(self, request, *args, **kwargs):
        # The side panel: just the panel, the list underneath is not touched.
        if self.side_panel and is_side_panel_request(request) and self.panel_data:
            return self.respond(self.panel_data["panel_content_template"], {"panel_data": self.panel_data})
        self.search = self.make_search(request)
        if "HX-Request" in request.headers:
            # "Meer…": the full option list of one filter group.
            if request.GET.get("filter_modal"):
                return self.respond(self.filter_modal_template, self.filters_context())
            # "Meer tonen": the next page of rows.
            if request.GET.get(PAGE_PARAM):
                return self.respond(self.rows_template, self.rows_context())
            # A filter, sort or search change: the results, with the filter panel out of band.
            return self.respond(
                self.results_template,
                {**self.rows_context(), **self.filters_context(), **self.controls(), "render_filter_fields_oob": True},
            )
        return self.respond(
            self.template_name,
            {
                **self.rows_context(),
                **self.filters_context(),
                **self.controls(),
                "panel_data": self.panel_data if self.side_panel else None,
            },
        )

    def respond(self, template: str, context: dict) -> TemplateResponse:
        return TemplateResponse(self.request, template, context)

    @cached_property
    def panel_data(self) -> dict | None:
        return resolve_side_panel(self.request, allow_create=self.allow_create)

    def page_source(self) -> Sequence | QuerySet:
        """What is paged: a sliceable, countable sequence in display order."""
        raise NotImplementedError

    def rows(self, page: Page) -> dict:
        """What a page of ``page_source`` renders as (cards, rows, ...)."""
        raise NotImplementedError

    def controls(self) -> dict:
        """What sits next to the results (sort, weergave, primary button)."""
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
            **self.rows(page),
        }

    def filters_context(self) -> dict:
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
