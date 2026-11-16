"""The filters of the list pages, and the dicts their sidebar groups render from.

A ``Filter`` is one URL parameter's selection and how it narrows a queryset.
``ListSearch`` (``listing.py``) applies a list's filters, and counts each
sidebar option under every filter but its own, so ticking an option never
collapses its siblings to zero. Each list writes its sidebar out itself, from
``select_multi_group`` and the counts.

Every filter that takes a public_id fails closed: a value that resolves to no
row filters everything away instead of being dropped, and still counts as an
active filter, with an "Onbekend …" chip, so the user is not left on an
unexplained empty list. See ``ResolvedFacet``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any

from wies.core.models import (
    Label,
    OrganizationUnit,
)
from wies.core.public_id import ResolvedFacet, parse_public_ids
from wies.core.services.organizations import (
    ORG_TYPE_PLURAL,
    get_ministry_nested_root_ids,
    get_org_descendant_ids,
    get_top_org_options,
    get_type_folder_root_ids,
    ministry_short_labels,
    nested_folder_label,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterable, Mapping

    from django.db.models import Model, QuerySet
    from django.http import QueryDict

    from wies.core.models import LabelCategory
    from wies.core.public_id import FacetResolver

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


@dataclass(frozen=True)
class Filter:
    """One filter of a list: what is selected, and how that narrows the rows.

    ``param`` is the URL parameter, and the name a count skips it by.
    ``active`` says whether ``narrow`` changes the result; a value that
    resolved to nothing is active too (it empties the list). ``values`` are
    what the chips and hidden inputs show, in URL order (a date for a date
    filter); ``unknown`` the values that resolved to nothing.
    """

    param: str
    active: bool
    narrow: Callable[[QuerySet], QuerySet]
    values: Any = ()
    unknown: list[str] = field(default_factory=list)

    def active_filters(self) -> dict[str, Any]:
        return {self.param: self.values} if self.values else {}

    def unknown_chips(self) -> list[dict]:
        return [
            {"param_name": self.param, "param_value": value, "label": UNKNOWN_FACET_LABELS[self.param]}
            for value in self.unknown
        ]


def model_filter(param: str, resolved: ResolvedFacet, lookup: str) -> Filter:
    """A multi-select on related rows (rol, onderdeel): OR within the selection."""
    return Filter(
        param,
        active=resolved.requested,
        narrow=lambda qs: qs.filter(**{f"{lookup}__in": resolved.ids}),
        values=resolved.active_values,
        unknown=resolved.unresolved,
    )


def resolve_pk_facet(model: type[Model], tokens: list[str]) -> ResolvedFacet:
    """``resolve_facet`` for a model without a public_id, keyed on its pk.

    Only for models whose pk is no secret (Django's Group); same fail-closed
    contract as the public_id facets.
    """
    tokens = [token.strip() for token in tokens if token.strip()]
    if not tokens:
        return ResolvedFacet(requested=False)
    existing = {
        str(pk) for pk in model.objects.filter(pk__in=[t for t in tokens if t.isdigit()]).values_list("pk", flat=True)
    }
    public_ids: list[str] = []
    unresolved: list[str] = []
    for token in dict.fromkeys(tokens):
        (public_ids if token in existing else unresolved).append(token)
    return ResolvedFacet(requested=True, public_ids=public_ids, ids=[int(t) for t in public_ids], unresolved=unresolved)


def label_category_param(category_id: int) -> str:
    """The name a count skips one label category by: each category is its own sidebar group."""
    return f"labels:{category_id}"


def label_filters(resolved: ResolvedFacet, lookup: str) -> list[Filter]:
    """The filters behind ``?labels=``: OR within a category, AND between categories.

    One filter per category with a selected label, so a category's counts can
    leave out its own selection; plus one for the param as a whole, which
    carries the chips and empties the list when labels were asked for and none
    of them exist.
    """
    by_category: dict[int, list[int]] = {}
    if resolved.ids:
        for label_id, category_id in Label.objects.filter(id__in=resolved.ids).values_list("id", "category_id"):
            by_category.setdefault(category_id, []).append(label_id)
    return [
        Filter(
            "labels",
            active=resolved.requested and not resolved.ids,
            narrow=lambda qs: qs.none(),
            values=resolved.active_values,
            unknown=resolved.unresolved,
        ),
        *(
            Filter(
                label_category_param(category_id),
                active=True,
                narrow=lambda qs, ids=ids: qs.filter(**{f"{lookup}__in": ids}),
            )
            for category_id, ids in by_category.items()
        ),
    ]


@dataclass(frozen=True)
class Choice:
    """One option of a select-multi group.

    ``value`` is the URL token, ``key`` what the counts are keyed on (usually
    the pk), ``extra`` lands on the option as is (e.g. ``category_color``).
    """

    value: str
    label: str
    key: Hashable
    extra: Mapping[str, Any] = field(default_factory=dict)


def model_choices(rows: Iterable[Model], label: Callable[[Model], str] = lambda row: row.name) -> list[Choice]:
    """Choices for rows that carry a public_id, in the order given."""
    return [Choice(str(row.public_id), label(row), row.pk) for row in rows]


def select_multi_group(
    name: str,
    label: str,
    choices: Iterable[Choice],
    selected: Iterable[str],
    counts: Mapping[Hashable, int] | None,
) -> dict:
    """The select-multi group dict the filter templates read.

    The leading empty option is the "nothing chosen" entry the templates skip;
    ``selected_values`` follow option order. Without ``counts`` the options
    carry no count at all, which the templates render as no number.
    """
    selected = set(selected)
    options: list[dict] = [{"value": "", "label": ""}]
    selected_values: list[str] = []
    for choice in choices:
        option = {"value": choice.value, "label": choice.label, **choice.extra}
        if counts is not None:
            option["count"] = counts.get(choice.key, 0)
        if choice.value in selected:
            option["selected"] = True
            selected_values.append(choice.value)
        options.append(option)
    return {
        "type": "select-multi",
        "name": name,
        "label": label,
        "options": options,
        "selected_values": selected_values,
    }


def categories_with_labels(categories: QuerySet[LabelCategory]) -> list[tuple[LabelCategory, list[Label]]]:
    """Each category with its labels, in their model order, in two queries."""
    return [(category, list(category.labels.all())) for category in categories.prefetch_related("labels")]


class OrgFilter:
    """The opdrachtgever filter (``org``/``org_self``/``org_type``/``org_type_in``).

    One filter for the four params: together they select one set of
    organizations, and the picker and its quick options treat them as one
    filter. ``org`` matches the whole subtree (plus units linked to it as their
    ministry, since those are not DB descendants), ``org_self`` only the org
    itself, ``org_type`` the roots in that top-level type folder of the picker
    plus their subtrees, and ``org_type_in`` every org of a type that nests under
    a given ministry.

    ``apply_ids`` narrows a queryset to rows of the matching organizations; it
    differs per list (a join, or a subquery where a join would duplicate rows).
    """

    param = "org"

    def __init__(
        self, resolver: FacetResolver, params: QueryDict, *, apply_ids: Callable[[QuerySet, set[int]], QuerySet]
    ):
        self.org = resolver("org", OrganizationUnit)
        self.org_self = resolver("org_self", OrganizationUnit)
        self.types = [value for value in params.getlist("org_type") if value]
        self.type_in = self._parse_type_in(params.getlist("org_type_in"))
        self.active = bool(self.org.requested or self.org_self.requested or self.types or self.type_in)
        self._apply_ids = apply_ids

    @staticmethod
    def _parse_type_in(values: list[str]) -> list[tuple[str, str]]:
        """``org_type_in=<ministry_public_id>:<type>``: one nested folder (BZK → Agentschappen).

        Values without both parts drop. A valid id is normalised to its
        canonical form so it matches ``str(public_id)`` lookups; an invalid one
        is kept as-is, so it matches nothing and gets an "Onbekende
        opdrachtgever" chip.
        """
        pairs: list[tuple[str, str]] = []
        for value in values:
            ministry_public_id, sep, type_name = value.partition(":")
            if sep and ministry_public_id and type_name:
                parsed = parse_public_ids([ministry_public_id])
                pairs.append((str(parsed[0]) if parsed else ministry_public_id, type_name))
        return pairs

    @cached_property
    def matching_ids(self) -> set[int]:
        """The organizations the selection matches; the tree is loaded once per request."""
        matching: set[int] = set(self.org_self.ids)
        if self.org.ids:
            matching |= get_org_descendant_ids(self.org.ids)
            # Units that nest under a selected ministry are DB roots, not
            # descendants, so pull them (and their subtrees) in via the tooi link.
            ministry_toois = [
                tooi
                for tooi in OrganizationUnit.objects.filter(id__in=self.org.ids).values_list(
                    "tooi_identifier", flat=True
                )
                if tooi
            ]
            if ministry_toois:
                # Only the roots that actually nest under the ministry in the
                # picker (nestable main type), so the filter matches the tree and
                # the sidebar count — not every org merely linked via the tooi.
                matching |= get_org_descendant_ids(get_ministry_nested_root_ids(ministry_toois))
        if self.types:
            # Same folder contents as the picker, so the folder's count holds.
            matching |= get_org_descendant_ids(get_type_folder_root_ids(self.types))
        if self.type_in:
            ministry_toois = {
                str(public_id): tooi
                for public_id, tooi in OrganizationUnit.objects.filter(
                    public_id__in=parse_public_ids([pid for pid, _ in self.type_in])
                ).values_list("public_id", "tooi_identifier")
            }
            for ministry_public_id, type_name in self.type_in:
                ministry_tooi = ministry_toois.get(ministry_public_id)
                if not ministry_tooi:
                    continue  # fail closed: unknown ministry matches nothing
                # Same nesting rule as the org facet, scoped to the chosen type; keys
                # on the MAIN type so a stichting with an incidental type is excluded.
                scoped_ids = get_ministry_nested_root_ids([ministry_tooi], type_name=type_name)
                matching |= get_org_descendant_ids(scoped_ids)
        return matching

    def narrow(self, qs: QuerySet) -> QuerySet:
        return self._apply_ids(qs, self.matching_ids)

    def active_filters(self) -> dict[str, list[str]]:
        active: dict[str, list[str]] = {}
        if self.org.active_values:
            active["org"] = self.org.active_values
        if self.org_self.active_values:
            active["org_self"] = self.org_self.active_values
        if self.types:
            active["org_type"] = self.types
        if self.type_in:
            active["org_type_in"] = [f"{pid}:{label}" for pid, label in self.type_in]
        return active

    def unknown_chips(self) -> list[dict]:
        """None: the chips below carry their own "Onbekende opdrachtgever" label."""
        return []

    def group(self, counts) -> dict:
        """The sidebar group: the top opdrachtgevers by ``counts``, the rest in the picker."""
        return {
            "type": "modal",
            "name": "organisatie",
            "label": "Opdrachtgever",
            "top_options": get_top_org_options(
                set(self.org.ids),
                counts,
                selected_self_ids=set(self.org_self.ids),
                selected_type_labels=set(self.types),
                selected_type_in=self.type_in,
            ),
        }

    def chips(self) -> list[dict]:
        """Chips for the opdrachtgever params, per param in the order they appear in the URL.

        These carry their own labels (and stand in for the unknown chips too):
        an opdrachtgever has no option list to match a value against.
        """
        labels: dict[str, str] = {}
        if self.org.ids or self.org_self.ids:
            labels = {
                str(public_id): label
                for public_id, label in OrganizationUnit.objects.filter(
                    id__in=[*self.org.ids, *self.org_self.ids]
                ).values_list("public_id", "label")
            }
        # Ministry labels for the scoped nested-folder chips ("Agentschappen van BZK").
        ministry_labels = ministry_short_labels([pid for pid, _ in self.type_in]) if self.type_in else {}
        chips: list[dict] = [
            {
                "param_name": "org",
                "param_value": public_id,
                "label": labels.get(public_id, UNKNOWN_FACET_LABELS["org"]),
            }
            for public_id in self.org.active_values
        ]
        chips.extend(
            {
                "param_name": "org_self",
                "param_value": public_id,
                "label": f"{labels[public_id]} (direct)" if public_id in labels else UNKNOWN_FACET_LABELS["org_self"],
            }
            for public_id in self.org_self.active_values
        )
        chips.extend(
            {
                "param_name": "org_type",
                "param_value": type_label,
                "label": ORG_TYPE_PLURAL.get(type_label, type_label),
            }
            for type_label in self.types
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
            for ministry_public_id, type_label in self.type_in
        )
        return chips


def finalize_filter_groups(filter_groups: list[dict], *, top_n: int = 3) -> list[dict]:
    """Post-processes the select-multi groups in place for the top-N + "Meer" modal.

    Each group gets a unique ``group_id`` (the key the modal opens by),
    ``top_options`` (the ``top_n`` options by count, selected ones kept visible)
    and ``has_more``. The full alphabetical ``options`` list is kept for the modal.
    A group that already has a ``group_id`` is left as it is. Returns the
    groups, for use in an expression.
    """
    label_seq = 0
    for group in filter_groups:
        if group.get("type") != "select-multi" or "group_id" in group:
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
    return filter_groups
