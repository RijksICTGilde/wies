"""The opdrachtgever tree: the filter lists' "Meer..." sheet and the assignment form's org picker."""

from collections import Counter

from django.shortcuts import render
from django.template.response import TemplateResponse

from wies.core.models import (
    OrganizationUnit,
)
from wies.core.public_id import parse_public_ids
from wies.core.services.organizations import (
    ORG_TYPE_PLURAL,
    build_org_hierarchy,
    get_excluded_org_ids,
    nested_folder_label,
)


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


def is_client_modal_request(request) -> bool:
    """An opdrachtgever "Meer..." click on a filter list: htmx asks for the org tree."""
    return "HX-Request" in request.headers and bool(request.GET.get("client_modal"))


def client_modal_response(request, org_self_counts: Counter[int]) -> TemplateResponse:
    """The opdrachtgever tree for a filter list, counted by that list.

    The list view returns this from its own ``get()`` with its own
    ``org_counts()``, so the tree counts what the sidebar counts (including the
    weergave on "Wie zit waar?") without this module knowing the list views.
    Orgs without cards are pruned.
    """
    hierarchy = build_org_hierarchy(org_self_counts, get_excluded_org_ids(), prune_empty=True)
    return TemplateResponse(
        request,
        "parts/client_modal.html",
        {"hierarchy": hierarchy, "current_selections": _build_current_selections(request)},
    )


def client_modal(request):
    """The org picker of the assignment form (HTMX partial).

    Not a filter list, so the tree carries no counts and shows the whole org
    tree, unpruned. The filter lists' tree is ``client_modal_response``.
    """
    hierarchy = build_org_hierarchy(Counter(), get_excluded_org_ids(), prune_empty=False)
    return render(
        request,
        "parts/assignment_org_modal.html",
        {"hierarchy": hierarchy, "current_selections": _build_current_selections(request)},
    )
