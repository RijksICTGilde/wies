"""Filter facets, shared by the list views."""

from functools import cached_property
from typing import TYPE_CHECKING

from django.template.response import TemplateResponse

from wies.core.models import (
    Label,
    OrganizationUnit,
)
from wies.core.public_id import FacetResolver, parse_public_ids
from wies.core.services.organizations import (
    ORG_TYPE_PLURAL,
    get_ministry_nested_root_ids,
    get_org_descendant_ids,
    get_type_folder_root_ids,
    nested_folder_label,
)

if TYPE_CHECKING:
    from django.db.models import (
        Model,
        QuerySet,
    )

# Shown for a filter value that matches no row (a deleted or edited bookmark).
# The chip has to be there: it explains why the list is empty and lets the user
# click the filter away.
UNKNOWN_FACET_LABELS = {
    "org": "Onbekende opdrachtgever",
    "org_self": "Onbekende opdrachtgever",
    "org_type_in": "Onbekende opdrachtgever",
    "rol": "Onbekende rol",
    "labels": "Onbekend label",
    "onderdeel": "Onbekend onderdeel",
}


class PublicIdFacetsMixin:
    """Resolves the public_id filter params of a list view once per request.

    Every facet fails closed: a param that resolves to no row filters everything
    away instead of being dropped, and still counts as an active filter so the
    user gets a chip rather than an unexplained empty list. See ``ResolvedFacet``.
    """

    @cached_property
    def facets(self) -> FacetResolver:
        return FacetResolver(self.request, self.facet_scopes())

    def facet_scopes(self) -> dict[type[Model], QuerySet]:
        """Per model, the rows this view's facets may resolve to; see ``resolve_facet``."""
        return {}

    @cached_property
    def org_type_filter(self) -> list[str]:
        return [x for x in self.request.GET.getlist("org_type") if x]

    @cached_property
    def org_type_in_filter(self) -> list[tuple[str, str]]:
        """The scoped nested-folder facet: ``org_type_in=<ministry_public_id>:<type>``.

        One entry per selected nested folder (e.g. BZK → Agentschappen). Parsed
        into ``(ministry_public_id, type_name)`` pairs; values without both parts
        drop. A valid id is normalised to its canonical form so it matches
        ``str(public_id)`` lookups; an invalid one is kept as-is, so it matches
        nothing and gets an "Onbekende opdrachtgever" chip.
        """
        pairs: list[tuple[str, str]] = []
        for value in self.request.GET.getlist("org_type_in"):
            ministry_public_id, sep, type_name = value.partition(":")
            if sep and ministry_public_id and type_name:
                parsed = parse_public_ids([ministry_public_id])
                pairs.append((str(parsed[0]) if parsed else ministry_public_id, type_name))
        return pairs

    def apply_org_filter(self, qs, lookup: str):
        """Applies the opdrachtgever facets (``org``/``org_self``/``org_type``/``org_type_in``).

        ``lookup`` is the queryset path to the organization id, which differs per
        list view. ``org`` matches the whole subtree (plus units linked to it as
        their ministry, since those are not DB descendants), ``org_self`` only the
        org itself, ``org_type`` the roots in that top-level type folder of the
        picker plus their subtrees, and ``org_type_in`` every org of a type that
        nests under a given ministry.
        """
        org = self.facets("org", OrganizationUnit)
        org_self = self.facets("org_self", OrganizationUnit)
        if not (org.requested or org_self.requested or self.org_type_filter or self.org_type_in_filter):
            return qs
        matching_ids: set[int] = set(org_self.ids)
        if org.ids:
            matching_ids |= get_org_descendant_ids(org.ids)
            # Units that nest under a selected ministry are DB roots, not
            # descendants, so pull them (and their subtrees) in via the tooi link.
            ministry_toois = [
                tooi
                for tooi in OrganizationUnit.objects.filter(id__in=org.ids).values_list("tooi_identifier", flat=True)
                if tooi
            ]
            if ministry_toois:
                # Only the roots that actually nest under the ministry in the
                # picker (nestable main type), so the filter matches the tree and
                # the sidebar count — not every org merely linked via the tooi.
                linked_ids = get_ministry_nested_root_ids(ministry_toois)
                matching_ids |= get_org_descendant_ids(linked_ids)
        if self.org_type_filter:
            # Same folder contents as the picker, so the folder's count holds.
            matching_ids |= get_org_descendant_ids(get_type_folder_root_ids(self.org_type_filter))
        if self.org_type_in_filter:
            ministry_toois = {
                str(public_id): tooi
                for public_id, tooi in OrganizationUnit.objects.filter(
                    public_id__in=parse_public_ids([pid for pid, _ in self.org_type_in_filter])
                ).values_list("public_id", "tooi_identifier")
            }
            for ministry_public_id, type_name in self.org_type_in_filter:
                ministry_tooi = ministry_toois.get(ministry_public_id)
                if not ministry_tooi:
                    continue  # fail closed: unknown ministry matches nothing
                # Same nesting rule as the org facet, scoped to the chosen type; keys
                # on the MAIN type so a stichting with an incidental type is excluded.
                scoped_ids = get_ministry_nested_root_ids([ministry_tooi], type_name=type_name)
                matching_ids |= get_org_descendant_ids(scoped_ids)
        return qs.filter(**{lookup: matching_ids})

    def add_org_filter_context(self, context: dict, active_filters: dict) -> None:
        """Registers the opdrachtgever facets as active filters and builds their chips."""
        org = self.facets("org", OrganizationUnit)
        org_self = self.facets("org_self", OrganizationUnit)
        if org.active_values:
            active_filters["org"] = org.active_values
        if org_self.active_values:
            active_filters["org_self"] = org_self.active_values
        if self.org_type_filter:
            active_filters["org_type"] = self.org_type_filter
        if self.org_type_in_filter:
            active_filters["org_type_in"] = [f"{pid}:{label}" for pid, label in self.org_type_in_filter]
        context["org_chip_data"] = self._org_chips()

    def _org_chips(self) -> list[dict]:
        """Chips for the opdrachtgever facets, in the order they appear in the URL."""
        org = self.facets("org", OrganizationUnit)
        org_self = self.facets("org_self", OrganizationUnit)
        type_labels = self.org_type_filter
        type_in = self.org_type_in_filter
        labels: dict[str, str] = {}
        if org.ids or org_self.ids:
            labels = {
                str(public_id): label
                for public_id, label in OrganizationUnit.objects.filter(id__in=[*org.ids, *org_self.ids]).values_list(
                    "public_id", "label"
                )
            }
        # Ministry labels for the scoped nested-folder chips ("Agentschappen van BZK").
        ministry_labels: dict[str, str] = {}
        if type_in:
            ministry_labels = {
                str(public_id): ((abbreviations[0] if abbreviations else "") or label or name)
                for public_id, label, name, abbreviations in OrganizationUnit.objects.filter(
                    public_id__in=parse_public_ids([pid for pid, _ in type_in])
                ).values_list("public_id", "label", "name", "abbreviations")
            }
        chips: list[dict] = [
            {
                "param_name": "org",
                "param_value": public_id,
                "label": labels.get(public_id, UNKNOWN_FACET_LABELS["org"]),
            }
            for public_id in org.active_values
        ]
        chips.extend(
            {
                "param_name": "org_self",
                "param_value": public_id,
                "label": f"{labels[public_id]} (direct)" if public_id in labels else UNKNOWN_FACET_LABELS["org_self"],
            }
            for public_id in org_self.active_values
        )
        chips.extend(
            {
                "param_name": "org_type",
                "param_value": type_label,
                "label": ORG_TYPE_PLURAL.get(type_label, type_label),
            }
            for type_label in type_labels
        )
        chips.extend(
            {
                "param_name": "org_type_in",
                "param_value": f"{ministry_public_id}:{type_label}",
                "label": (
                    nested_folder_label(ministry_labels[ministry_public_id], type_label)
                    if ministry_public_id in ministry_labels
                    else UNKNOWN_FACET_LABELS["org_type_in"]
                ),
            }
            for ministry_public_id, type_label in type_in
        )
        return chips

    def add_unknown_filter_chips(self, context: dict, facets: dict[str, type[Model]]) -> None:
        """Chips for the values of ``facets`` that match no row.

        Regular chips are rendered by matching an active value against the filter
        group's options, so a value that no longer exists would render nothing at
        all. The org facets build their own chips and are excluded here.
        """
        context["unknown_chip_data"] = [
            {
                "param_name": param,
                "param_value": value,
                "label": UNKNOWN_FACET_LABELS[param],
            }
            for param, model in facets.items()
            for value in self.facets(param, model).unresolved
        ]

    @cached_property
    def labels_by_category(self) -> dict[int, list[int]]:
        """Selected label ids grouped by their category id."""
        labels = self.facets("labels", Label)
        if not labels.ids:
            return {}
        by_category: dict[int, list[int]] = {}
        for label in Label.objects.filter(id__in=labels.ids).values("id", "category_id"):
            by_category.setdefault(label["category_id"], []).append(label["id"])
        return by_category

    @property
    def labels_match_nothing(self) -> bool:
        """A ``?labels=`` was given but none of its values exist."""
        return self.facets("labels", Label).requested and not self.labels_by_category


def finalize_filter_groups(filter_groups: list[dict], *, top_n: int = 3) -> None:
    """Post-processes the select-multi groups in place for the top-N + "Meer" modal.

    Each group gets a unique ``group_id`` (the key the modal opens by),
    ``top_options`` (the ``top_n`` options by count, selected ones kept visible)
    and ``has_more``. The full alphabetical ``options`` list is kept for the modal.
    """
    label_seq = 0
    for group in filter_groups:
        if group.get("type") != "select-multi":
            continue
        # Unique key — "labels" repeats per category, so disambiguate.
        if group["name"] == "labels":
            group["group_id"] = f"labels-{label_seq}"
            label_seq += 1
        else:
            group["group_id"] = group["name"]

        real_options = [o for o in group["options"] if o.get("value")]
        selected = set(group.get("selected_values", []))
        by_count = sorted(real_options, key=lambda o: (-o.get("count", 0), o.get("label", "")))
        # The top-N is fixed on count regardless of selection; a selected option
        # outside it is appended rather than displacing one. Same rule as
        # get_top_org_options.
        top = list(by_count[:top_n])
        top_values = {o["value"] for o in top}
        top.extend(o for o in by_count if o["value"] in selected and o["value"] not in top_values)
        group["top_options"] = top
        group["has_more"] = len(real_options) > len(top)


def is_filter_modal_request(request) -> bool:
    """A "Meer..." click: htmx asks for the full option list of one filter group."""
    return "HX-Request" in request.headers and bool(request.GET.get("filter_modal"))


def filter_modal_response(request, filter_groups: list[dict]) -> TemplateResponse:
    """The "Meer..." sheet for the group ``?filter_modal=`` names.

    The sheet reads nothing but the groups, so a list view returns this before
    it builds its page of results.
    """
    return TemplateResponse(
        request,
        "parts/filter_options_modal.html",
        {"filter_groups": filter_groups, "filter_modal_group_id": request.GET.get("filter_modal", "")},
    )
