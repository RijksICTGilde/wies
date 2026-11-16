"""Wie zit waar: the placement list and editing a placement."""

import json
from collections import Counter
from datetime import timedelta

from django.contrib import messages
from django.db.models import (
    Case,
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
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic.list import ListView

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

from ._common import PANEL_PARAMS, build_panel_url, resolve_panel_object, sort_control_context
from .filters import PublicIdFacetsMixin, finalize_filter_groups
from .panels import (
    build_aanvraag_panel_data,
    build_assignment_panel_data,
    build_colleague_panel_data,
    build_placement_edit_panel_data,
    resolve_aanvraag_panel,
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


class PlacementListView(PublicIdFacetsMixin, ListView):
    """Placements as cards, grouped per person or per assignment."""

    model = Placement
    template_name = "placements.html"
    paginate_by = 60
    page_kwarg = "pagina"

    VIEW_DEFAULT = "persoon"
    VIEW_OPTIONS = [
        {"value": "persoon", "label": "Persoon", "icon": "person"},
        {"value": "opdracht", "label": "Opdracht", "icon": "business-suitcase"},
    ]

    # Pagination runs over these groups, not over placements, so a group never
    # straddles a page boundary and shows up half.
    GROUP_FIELD = {
        "persoon": "colleague_id",
        "opdracht": "service__assignment_id",
    }

    # Sorting on colleague name says nothing in the opdracht view, where one card
    # is a whole team.
    SORT_OPTIONS = {
        "persoon": ["name", "-name", "assignment", "-assignment", "end_date", "-end_date"],
        "opdracht": ["assignment", "-assignment", "end_date", "-end_date"],
    }
    SORT_LABELS = {
        "name": "Naam (A-Z)",
        "-name": "Naam (Z-A)",
        "assignment": "Opdracht (A-Z)",
        "-assignment": "Opdracht (Z-A)",
        "-end_date": "Einddatum (nieuwste eerst)",
        "end_date": "Einddatum (oudste eerst)",
    }
    # The default order is the absence of ?order=, so it has no value to label.
    DEFAULT_SORT_LABEL = {
        "persoon": "Startdatum (nieuwste eerst)",
        "opdracht": "Laatst gewijzigd",
    }

    @property
    def active_view(self) -> str:
        """The requested ?weergave=, falling back to the default for unknown values."""
        requested = self.request.GET.get("weergave") or ""
        valid = {option["value"] for option in self.VIEW_OPTIONS}
        return requested if requested in valid else self.VIEW_DEFAULT

    def _get_base_queryset(self):
        """Base queryset with search, ordering, and date filters applied."""
        excluded_org_ids = get_excluded_org_ids()
        qs = (
            Placement.objects.select_related("colleague", "service", "service__skill")
            .prefetch_related(
                "colleague__labels",
                Prefetch(
                    "service__assignment__organization_relations",
                    queryset=AssignmentOrganizationUnit.objects.annotate(
                        role_order=Case(
                            When(role="PRIMARY", then=0),
                            default=1,
                        )
                    )
                    .order_by("role_order")
                    .select_related("organization"),
                    to_attr="sorted_clients",
                ),
            )
            .order_by("-service__assignment__start_date")
        )
        if excluded_org_ids:
            qs = qs.exclude(service__assignment__organizations__id__in=excluded_org_ids)

        search_filter = self.request.GET.get("zoek")
        if search_filter:
            qs = qs.filter(
                Q(colleague__name__icontains=search_filter)
                | Q(service__assignment__name__icontains=search_filter)
                | Q(service__assignment__extra_info__icontains=search_filter)
                | Q(service__assignment__organizations__label__icontains=search_filter)
            )

        order_mapping = {
            "name": "colleague__name",
            "assignment": "service__assignment__name",
            "end_date": "service__assignment__end_date",
        }

        active_view = self.active_view
        sort_field = None
        order_param = self.request.GET.get("order")
        # A shared url can carry an order this view does not have.
        if order_param and order_param in self.SORT_OPTIONS[active_view]:
            descending = order_param.startswith("-")
            order_by = order_mapping.get(order_param.lstrip("-"))
            if order_by:
                sort_field = f"-{order_by}" if descending else order_by
        if sort_field is None:
            if active_view == "opdracht":
                # No modified-at on the model, so the audit log stands in. Nulls last:
                # events age out of retention.
                qs = qs.annotate(
                    last_change=Subquery(
                        Event.objects.filter(object_type="Assignment", object_id=OuterRef("service__assignment_id"))
                        .order_by("-timestamp")
                        .values("timestamp")[:1]
                    )
                )
                sort_field = F("last_change").desc(nulls_last=True)
            else:
                # Nulls last: a placement without a start date says nothing about
                # how recent it is.
                sort_field = F("actual_start_date").desc(nulls_last=True)

        qs = annotate_placement_dates(qs)

        # The group as tiebreaker keeps one person's or opdracht's placements
        # together when the sort itself ties.
        qs = qs.order_by(sort_field, self.GROUP_FIELD[active_view])

        # The list is a current-state overview: only active placements, for every
        # viewer alike. History and planned placements live on the profile and the
        # side panels, not here.
        return filter_visible_placements(qs, timezone.now().date())

    def _get_loopt_af_options(self, base_qs):
        """Builds the 'loopt af' filter options with cumulative counts.

        Counts distinct groups, not placements, so the number matches the cards
        the list will show: two colleagues on one assignment are two cards in the
        person view and one in the assignment view.
        """
        today = timezone.now().date()
        group_field = self.GROUP_FIELD[self.active_view]
        filtered_qs = self._apply_filters(base_qs, exclude_filter="loopt_af").distinct()

        def group_count(qs):
            return qs.values(group_field).distinct().count()

        presets = [
            ("3m", "Binnen 3 maanden", 91),
            ("6m", "Binnen 6 maanden", 182),
        ]
        options = [{"value": "", "label": ""}]
        for value, label, days in presets:
            end_date = today + timedelta(days=days)
            count = group_count(filtered_qs.filter(service__assignment__end_date__lte=end_date))
            options.append({"value": value, "label": label, "count": count})
        # "Longer than 6 months"
        half_year = today + timedelta(days=182)
        count_beyond = group_count(filtered_qs.filter(service__assignment__end_date__gt=half_year))
        options.append({"value": "6m+", "label": "Langer dan 6 maanden", "count": count_beyond})
        return options

    def org_counts(self) -> Counter[int]:
        """Groups per opdrachtgever under every filter but the opdrachtgever's,
        for the sidebar and the opdrachtgever picker alike.

        Counts the groups of the active ``?weergave=``, so the picker's numbers
        match the sidebar's next to it.
        """
        return org_counts_from_filtered(
            self._apply_filters(self._get_base_queryset(), exclude_filter="org").distinct(),
            Placement,
            "service__assignment__organizations__id",
            group_field=self.GROUP_FIELD[self.active_view],
        )

    def _apply_filters(self, qs, *, exclude_filter=None):
        """Applies all selection filters, optionally excluding one filter type.

        ``exclude_filter`` is "rol", "org", "onderdeel", "loopt_af", or a category_id
        (int) for labels.
        """
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

        # Filter by assignment end date (preset period)
        if exclude_filter != "loopt_af":
            loopt_af_values = set(self.request.GET.getlist("loopt_af"))
            if loopt_af_values:
                today = timezone.now().date()
                preset_days = {"3m": 91, "6m": 182}
                has_beyond = "6m+" in loopt_af_values
                bounded = {v for v in loopt_af_values if v in preset_days}
                half_year = today + timedelta(days=182)
                if bounded and has_beyond:
                    max_days = max(preset_days[v] for v in bounded)
                    end_date = today + timedelta(days=max_days)
                    qs = qs.filter(
                        Q(service__assignment__end_date__lte=end_date) | Q(service__assignment__end_date__gt=half_year)
                    )
                elif bounded:
                    max_days = max(preset_days[v] for v in bounded)
                    end_date = today + timedelta(days=max_days)
                    qs = qs.filter(service__assignment__end_date__lte=end_date)
                elif has_beyond:
                    qs = qs.filter(service__assignment__end_date__gt=half_year)

        return qs

    def facet_scopes(self) -> dict[type[Model], QuerySet]:
        # Subgroep has no filter here, so a Subgroep label from an old link gets
        # the "Onbekend label" chip instead of filtering out of sight.
        return {Label: Label.objects.filter(category__in=label_categories_for_everyone())}

    def get_queryset(self):
        """Applies the filters to the placements queryset."""
        if self.labels_match_nothing:
            return Placement.objects.none()
        return self._apply_filters(self._get_base_queryset()).distinct()

    def paginate_queryset(self, queryset, page_size):
        """Paginate on groups (persons or assignments), not on placements.

        A card shows one person or one assignment with all their placements, so
        paginating on placements would cut a group in half at the page boundary.
        """
        group_field = self.GROUP_FIELD[self.active_view]
        # A DISTINCT on the group field would have to select every sort column too.
        seen: set[int] = set()
        ordered_group_ids = [
            group_id
            for group_id in queryset.values_list(group_field, flat=True)
            if group_id not in seen and not seen.add(group_id)
        ]

        paginator = self.get_paginator(
            ordered_group_ids, page_size, orphans=self.get_paginate_orphans(), allow_empty_first_page=True
        )
        page = paginator.page(self._validated_page_number(paginator))
        page_group_ids = list(page.object_list)
        placements = list(queryset.filter(**{f"{group_field}__in": page_group_ids})) if page_group_ids else []
        return paginator, page, placements, page.has_other_pages()

    def _validated_page_number(self, paginator) -> int:
        """The requested ?pagina=, clamped to an existing page (1 on nonsense input)."""
        raw = self.kwargs.get(self.page_kwarg) or self.request.GET.get(self.page_kwarg) or 1
        try:
            number = int(raw)
        except TypeError, ValueError:
            return 1
        return max(1, min(number, paginator.num_pages))

    def get_template_names(self):
        """Returns the template for this request type."""
        if "HX-Request" in self.request.headers:
            if self.request.GET.get("filter_modal"):
                return ["parts/filter_options_modal.html"]
            hx_target = self.request.headers.get("HX-Target", "")
            if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container"):
                # panel_data picks its own template (e.g. the edit child sheet);
                # get_context_data has already stored it.
                panel_data = getattr(self, "_panel_data", None)
                if panel_data:
                    return [panel_data["panel_content_template"]]
                return ["parts/assignment_panel_content.html"]
            if self.request.GET.get("pagina"):
                return ["parts/placement_cards.html"]
            return ["parts/filter_and_table_container.html"]
        return ["placements.html"]

    def _view_url(self, value: str) -> str:
        """URL for a weergave: keeps the filters and search, drops page and order.

        The sort options differ per view, so an ?order= from the other view would
        not resolve here.
        """
        dropped = (self.page_kwarg, "order")
        if value == self.VIEW_DEFAULT:
            return rebuild_url(reverse("home"), self.request.GET, drop=(*dropped, "weergave"))
        return rebuild_url(reverse("home"), self.request.GET, drop=dropped, weergave=value)

    def _person_cards(self, placements) -> list[dict]:
        """One card per colleague, with the assignments they are placed on.

        A person on exactly one assignment opens that placement's panel; on more
        than one the card opens the colleague panel instead.
        """
        grouped: dict[int, list] = {}
        for placement in placements:
            grouped.setdefault(placement.colleague_id, []).append(placement)

        cards = []
        for rows in grouped.values():
            assignments = list(dict.fromkeys(row.service.assignment for row in rows))
            roles = list(dict.fromkeys(row.service.skill.name for row in rows if row.service.skill))
            single = assignments[0] if len(assignments) == 1 else None
            cards.append(
                {
                    "name": rows[0].colleague.name,
                    "assignment": single,
                    "assignments": assignments,
                    "roles": roles,
                    # A person opens the colleague panel, whatever their number
                    # of opdrachten; its cards lead on to each opdracht.
                    "panel_url": build_panel_url(self.request, collega=rows[0].colleague.public_id),
                }
            )
        return cards

    def _assignment_cards(self, placements) -> list[dict]:
        """One card per assignment, showing its FULL team.

        The team is prefetched separately rather than read off the filtered
        placements: a filter on role or label would otherwise silently shrink the
        team shown on the card to the people that matched the filter.

        Sidestepping the selection filters is the point here; sidestepping the
        visibility filter is not. This page is a current-state overview, so the
        team is the team as it stands today — the same rule the list itself
        follows, and without it a card would name people who left months ago or
        have not started yet.
        """
        assignments = list(dict.fromkeys(p.service.assignment for p in placements))
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
            clients = getattr(assignment, "sorted_clients", [])
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

    def get_context_data(self, **kwargs):
        """Adds the dynamic filter options."""
        context = super().get_context_data(**kwargs)
        context["render_filter_fields_oob"] = "HX-Request" in self.request.headers

        active_view = self.active_view
        context["active_view"] = active_view
        # The template compares against it rather than hardcoding the name, so
        # changing the default does not silently break the hidden field.
        context["default_view"] = self.VIEW_DEFAULT
        counts = {active_view: context["paginator"].count}
        filtered = self.get_queryset()
        context["view_options"] = [
            {
                **option,
                "url": self._view_url(option["value"]),
                "selected": option["value"] == active_view,
                "count": counts.get(option["value"])
                if option["value"] in counts
                else filtered.values(self.GROUP_FIELD[option["value"]]).distinct().count(),
            }
            for option in self.VIEW_OPTIONS
        ]
        placements = context["object_list"]
        if active_view == "opdracht":
            context["cards"] = self._assignment_cards(placements)
        else:
            context["cards"] = self._person_cards(placements)

        order_param = self.request.GET.get("order")
        active_order = order_param if order_param in self.SORT_OPTIONS[active_view] else ""
        context.update(
            sort_control_context(
                active_order,
                [(value, self.SORT_LABELS[value]) for value in self.SORT_OPTIONS[active_view]],
                self.DEFAULT_SORT_LABEL[active_view],
            )
        )

        context["filter_target_url"] = reverse("home")
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters: dict = {}

        loopt_af_values = set(self.request.GET.getlist("loopt_af"))
        if loopt_af_values:
            active_filters["loopt_af"] = loopt_af_values

        # Multi-select facets carry public_ids. A value that resolves to nothing
        # still counts, so an empty list always comes with a way to clear it.
        rol_filter = self.facets("rol", Skill).active_values
        if rol_filter:
            active_filters["rol"] = rol_filter

        label_filter = self.facets("labels", Label).active_values
        if label_filter:
            active_filters["labels"] = label_filter

        suborganization_filter = self.facets("onderdeel", Suborganization).active_values
        if suborganization_filter:
            active_filters["onderdeel"] = suborganization_filter

        # Organization filter (multi-select via modal)
        self.add_org_filter_context(context, active_filters)
        self.add_unknown_filter_chips(context, {"rol": Skill, "labels": Label, "onderdeel": Suborganization})

        # For each filter category, count on a queryset excluding that category's filter
        base_qs = self._get_base_queryset()
        group_field = self.GROUP_FIELD[active_view]

        label_filter_groups = []
        for category in label_categories_for_everyone():
            # Count with all filters EXCEPT this label category
            cat_filtered_qs = self._apply_filters(base_qs, exclude_filter=category.id).distinct()
            cat_label_counts = _facet_counts(cat_filtered_qs, "colleague__labels__id", group_field)

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

        # Onderdeel filter group (one per colleague; counts exclude its own filter)
        suborg_filtered_qs = self._apply_filters(base_qs, exclude_filter="onderdeel").distinct()
        suborg_counts = _facet_counts(suborg_filtered_qs, "colleague__suborganization_id", group_field)

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

        # Skill/role counts: exclude role filter
        skill_filtered_qs = self._apply_filters(base_qs, exclude_filter="rol").distinct()
        skill_counts = _facet_counts(skill_filtered_qs, "service__skill__id", group_field)

        skill_options = [{"value": "", "label": ""}]
        skill_selected_values = []
        for skill in Skill.objects.order_by("name"):
            option = {"value": str(skill.public_id), "label": skill.name, "count": skill_counts.get(skill.id, 0)}
            if str(skill.public_id) in active_filters.get("rol", set()):
                option["selected"] = True
                skill_selected_values.append(str(skill.public_id))
            skill_options.append(option)

        org_counts = self.org_counts()

        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)
        context["client_modal_count_mode"] = "placements"

        # TODO: this can be become an object to help defining correctly and performing extra preprocessing on context
        # introduce value_key, label_key:
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
            suborganization_filter_group,
            *label_filter_groups,
            {
                "type": "select-multi",
                "name": "loopt_af",
                "label": "Loopt af",
                "options": self._get_loopt_af_options(base_qs),
                "selected_values": list(loopt_af_values),
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

        colleague_id = self.request.GET.get("collega")
        assignment_id = self.request.GET.get("opdracht")
        service_id = self.request.GET.get("aanvraag")

        if service_id and not self.request.GET.get("teamlid"):
            service = resolve_aanvraag_panel(self.request, service_id)
            if service is not None:
                context["panel_data"] = build_aanvraag_panel_data(service, self.request)
        elif colleague_id and not assignment_id:
            colleague = resolve_panel_object(self.request, Colleague, colleague_id)
            if colleague is not None:
                context["panel_data"] = build_colleague_panel_data(colleague, self.request)
        elif assignment_id:
            assignment = resolve_panel_object(self.request, Assignment, assignment_id)
            if assignment is not None:
                context["panel_data"] = build_assignment_panel_data(assignment, self.request)
        # get_context_data runs before get_template_names, which reads the panel
        # template from here instead of deriving it again.
        self._panel_data = context.get("panel_data")
        return context


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

    fallback = build_panel_url(
        request, opdracht=placement.service.assignment.public_id, collega=placement.colleague.public_id
    )
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
