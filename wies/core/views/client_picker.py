"""The opdrachtgever picker modal, counting over the list views' own filters."""

from collections import Counter

from django.http import HttpResponseBadRequest
from django.shortcuts import render

from wies.core.models import (
    OrganizationUnit,
    Placement,
)
from wies.core.public_id import parse_public_ids
from wies.core.services.organizations import (
    ORG_TYPE_PLURAL,
    build_org_hierarchy,
    get_excluded_org_ids,
    nested_folder_label,
    org_counts_from_filtered,
)

from .assignments import AssignmentListView
from .placements import PlacementListView


def _build_current_selections(request) -> dict[str, str]:
    """Builds the current selections from the request params, for state restoration."""
    current_selections: dict[str, str] = {}

    org_public_ids = request.GET.getlist("org")
    for org in OrganizationUnit.objects.filter(public_id__in=parse_public_ids(org_public_ids)).values(
        "public_id", "label"
    ):
        current_selections[str(org["public_id"])] = org["label"]

    self_org_public_ids = request.GET.getlist("org_self")
    for org in OrganizationUnit.objects.filter(public_id__in=parse_public_ids(self_org_public_ids)).values(
        "public_id", "label"
    ):
        current_selections[f"self-{org['public_id']}"] = f'Direct onder "{org["label"]}"'

    for type_label in request.GET.getlist("org_type"):
        if type_label:
            current_selections[f"group-{type_label}"] = ORG_TYPE_PLURAL.get(type_label, type_label)

    # Scoped nested folders: re-check the "group-<ministry_public_id>-<type>" node.
    # Label matches the picker folder and the chip ("Adviescolleges van BZ"), so a
    # restored selection reads identically. Abbreviation, else label as fallback.
    nested = [value.partition(":") for value in request.GET.getlist("org_type_in")]
    nested = [(pid, tl) for pid, sep, tl in nested if sep and pid and tl]
    ministry_abbreviations: dict[str, str] = {
        str(public_id): ((abbreviations[0] if abbreviations else "") or label or name)
        for public_id, label, name, abbreviations in OrganizationUnit.objects.filter(
            public_id__in=parse_public_ids([pid for pid, _ in nested])
        ).values_list("public_id", "label", "name", "abbreviations")
    }
    for ministry_public_id, type_label in nested:
        abbreviation = ministry_abbreviations.get(ministry_public_id)
        if abbreviation is None:
            continue  # ministry not found → drop, same as a stale facet
        current_selections[f"group-{ministry_public_id}-{type_label}"] = nested_folder_label(abbreviation, type_label)

    return current_selections


def client_modal(request):
    """Returns the client tree selection modal (HTMX partial)."""
    excluded_org_ids = get_excluded_org_ids()
    count_mode = request.GET.get("count_mode")

    # count_mode "none" is the assignment-form org picker, not a filter list, so
    # the tree carries no counts (the whole org tree is shown, unpruned). The
    # filter modes count over the list's other active filters (sent along via
    # hx-include) so the tree matches the sidebar: borrow the list view's own
    # _apply_filters (single source of the predicates) rather than re-implementing
    # them here, which would drift.
    if count_mode == "none":
        org_self_counts = Counter()
    elif count_mode == "open_assignments":
        view = AssignmentListView()
        view.request = request
        org_self_counts = view.org_counts()
    elif count_mode == "placements":
        view = PlacementListView()
        view.request = request
        # The tree counts the same groups the sidebar does, and the sidebar
        # follows ?weergave=. Without this the modal counted placements whatever
        # the view, so its numbers sat next to sidebar numbers that disagreed.
        filtered_qs = view._apply_filters(view._get_base_queryset(), exclude_filter="org").distinct()
        org_self_counts = org_counts_from_filtered(
            filtered_qs,
            Placement,
            "service__assignment__organizations__id",
            group_field=view.GROUP_FIELD[view.active_view],
        )
    else:
        return HttpResponseBadRequest("Onbekende count_mode")
    hierarchy = build_org_hierarchy(org_self_counts, excluded_org_ids, prune_empty=count_mode != "none")
    current_selections = _build_current_selections(request)

    template = "parts/assignment_org_modal.html" if count_mode == "none" else "parts/client_modal.html"
    return render(
        request,
        template,
        {"hierarchy": hierarchy, "current_selections": current_selections},
    )
