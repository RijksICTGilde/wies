"""Filter facets, shared by the list views.

A facet is one filter of a list: it narrows a queryset, says what it has
selected (for the chips and the hidden inputs) and builds its group for the
filter panel. ``ListSearch`` (``listing.py``) combines a list's facets and gives
each one its cross-filtered counts: the counts under every facet but its own,
so ticking an option never collapses its siblings to zero.

Every facet that takes a public_id fails closed: a value that resolves to no
row filters everything away instead of being dropped, and still counts as an
active filter, with an "Onbekend …" chip, so the user is not left on an
unexplained empty list. See ``ResolvedFacet``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import cached_property
from typing import TYPE_CHECKING, Any

from django.db.models import Count, Q

from wies.core.models import (
    Label,
    LabelCategory,
    OrganizationUnit,
)
from wies.core.public_id import FacetResolver, ResolvedFacet, parse_public_ids
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
    from collections import Counter
    from collections.abc import Callable, Hashable, Iterable, Mapping

    from django.db.models import Model, QuerySet
    from django.http import QueryDict

    from .listing import ListSearch

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


def unknown_chips(param: str, values: Iterable[str]) -> list[dict]:
    return [{"param_name": param, "param_value": value, "label": UNKNOWN_FACET_LABELS[param]} for value in values]


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


class Facet:
    """One filter of a list. Subclasses override what applies to them.

    ``key`` is unique within a list: it is what "every facet but this one"
    excludes. ``param`` is the URL parameter, which facets may share (one
    facet per label category, all under ``labels``).
    """

    key: str
    param: str

    @property
    def active(self) -> bool:
        """Whether ``apply`` narrows the queryset.

        Counts are shared between facets that are inactive, so this must be
        exactly "apply changes the result", including a fail-closed facet that
        resolved to nothing.
        """
        return False

    def apply(self, qs: QuerySet) -> QuerySet:
        return qs

    def active_filters(self) -> dict[str, Any]:
        """``{param: selected values}`` for the chips and the hidden inputs."""
        return {}

    def unknown_chips(self) -> list[dict]:
        return []

    def counts(self, search: ListSearch) -> Mapping[Hashable, int] | None:
        """Per-option counts under every facet but this one; None for no counts."""
        return None

    def group(self, counts: Mapping[Hashable, int] | None) -> dict | None:
        """The filter-panel group, or None for a facet without one."""
        return None


class ModelFacet(Facet):
    """A multi-select on a related model: OR within the selection."""

    def __init__(
        self,
        param: str,
        label: str,
        resolved: ResolvedFacet,
        *,
        lookup: str,
        choices: Callable[[], Iterable[Choice]],
        count_lookup: str | None = None,
    ):
        self.key = self.param = param
        self.label = label
        self.resolved = resolved
        self.lookup = lookup
        self.choices = choices
        self.count_lookup = count_lookup or lookup

    @property
    def active(self) -> bool:
        return self.resolved.requested

    def apply(self, qs):
        return qs.filter(**{f"{self.lookup}__in": self.resolved.ids})

    def active_filters(self):
        values = self.resolved.active_values
        return {self.param: values} if values else {}

    def unknown_chips(self):
        return unknown_chips(self.param, self.resolved.unresolved)

    def counts(self, search):
        return search.count_by(self, self.count_lookup)

    def group(self, counts):
        return select_multi_group(self.param, self.label, self.choices(), self.resolved.active_values, counts)


class LabelSelection(Facet):
    """The ``labels`` param as a whole: its chips, and failing closed.

    The label groups are one facet per category (``LabelCategoryFacet``); this
    one carries what belongs to the param rather than to a category. When labels
    were asked for and none of them exist, it empties the list and every count
    with it: the numbers then match the empty list next to them.
    """

    key = param = "labels"

    def __init__(self, resolved: ResolvedFacet):
        self.resolved = resolved

    @property
    def active(self) -> bool:
        return self.resolved.requested and not self.resolved.ids

    def apply(self, qs):
        return qs.none()

    def active_filters(self):
        values = self.resolved.active_values
        return {self.param: values} if values else {}

    def unknown_chips(self):
        return unknown_chips(self.param, self.resolved.unresolved)


class LabelCategoryFacet(Facet):
    """The labels of one category: OR within it, AND with the other categories.

    ``labels`` is None for a category that is filtered on but not shown (its
    labels are out of this list's scope): it still filters, it has no group.
    """

    param = "labels"

    def __init__(
        self,
        category_id: int,
        category_name: str,
        labels: list[Label] | None,
        selected_ids: list[int],
        resolved: ResolvedFacet,
        *,
        lookup: str,
        with_color: bool,
        color: str | None = None,
    ):
        self.key = f"labels:{category_id}"
        self.category_name = category_name
        self.labels = labels
        self.selected_ids = selected_ids
        self.resolved = resolved
        self.lookup = lookup
        self.extra = {"category_color": color} if with_color else {}

    @property
    def active(self) -> bool:
        return bool(self.selected_ids)

    def apply(self, qs):
        return qs.filter(**{f"{self.lookup}__in": self.selected_ids})

    def counts(self, search):
        return None if self.labels is None else search.count_by(self, self.lookup)

    def group(self, counts):
        if self.labels is None:
            return None
        choices = [Choice(str(label.public_id), label.name, label.pk, self.extra) for label in self.labels]
        return select_multi_group(self.param, self.category_name, choices, self.resolved.active_values, counts)


def label_facets(
    resolved: ResolvedFacet,
    groups: Iterable[tuple[LabelCategory, list[Label]]],
    *,
    lookup: str,
    with_color: bool = False,
) -> list[Facet]:
    """The facets behind ``?labels=``: one per shown category, in ``groups`` order.

    A selected label whose category is not shown still filters, through a facet
    without a group.
    """
    selected_by_category: dict[int, list[int]] = {}
    if resolved.ids:
        for label_id, category_id in Label.objects.filter(id__in=resolved.ids).values_list("id", "category_id"):
            selected_by_category.setdefault(category_id, []).append(label_id)
    facets: list[Facet] = [LabelSelection(resolved)]
    shown: set[int] = set()
    for category, labels in groups:
        shown.add(category.id)
        facets.append(
            LabelCategoryFacet(
                category.id,
                category.name,
                labels,
                selected_by_category.get(category.id, []),
                resolved,
                lookup=lookup,
                with_color=with_color,
                color=category.color,
            )
        )
    facets.extend(
        LabelCategoryFacet(category_id, "", None, ids, resolved, lookup=lookup, with_color=False)
        for category_id, ids in selected_by_category.items()
        if category_id not in shown
    )
    return facets


def categories_with_labels(categories: QuerySet[LabelCategory]) -> list[tuple[LabelCategory, list[Label]]]:
    """Each category with its labels, in their model order, in two queries."""
    return [(category, list(category.labels.all())) for category in categories.prefetch_related("labels")]


@dataclass(frozen=True)
class Preset:
    value: str
    label: str
    q: Q


class PresetFacet(Facet):
    """Fixed choices that each stand for a condition; OR between the chosen ones.

    Counts are cumulative per preset (each option counts what it would select on
    its own), in one query. An unknown value is dropped: it filters nothing, so
    keeping it would only leave a chip-less hidden input behind.
    """

    def __init__(self, param: str, label: str, presets: list[Preset], values: list[str]):
        self.key = self.param = param
        self.label = label
        self.presets = presets
        known = {preset.value for preset in presets}
        self.values = [value for value in dict.fromkeys(values) if value in known]

    @property
    def active(self) -> bool:
        return bool(self.values)

    def apply(self, qs):
        condition = Q()
        for preset in self.presets:
            if preset.value in self.values:
                condition |= preset.q
        return qs.filter(condition)

    def active_filters(self):
        return {self.param: self.values} if self.values else {}

    def counts(self, search):
        base = search.filtered_except(self)
        rows = base.model.objects.filter(pk__in=base.values("pk"))
        group = search.group_field or "pk"
        return rows.aggregate(**{preset.value: Count(group, distinct=True, filter=preset.q) for preset in self.presets})

    def group(self, counts):
        choices = [Choice(preset.value, preset.label, preset.value) for preset in self.presets]
        return select_multi_group(self.param, self.label, choices, self.values, counts)


class KeyFacet(Facet):
    """A multi-select on plain string keys (standplaats): unknown keys drop.

    ``labels`` maps every known key to its label; ``apply`` gets the selected
    keys, ``count`` the cross-filtered queryset.
    """

    def __init__(
        self,
        param: str,
        label: str,
        labels: Mapping[str, str],
        selected: list[str],
        *,
        apply: Callable[[QuerySet, list[str]], QuerySet],
        count: Callable[[QuerySet], Counter],
    ):
        self.key = self.param = param
        self.label = label
        self.labels = labels
        self.selected = selected
        self._apply = apply
        self._count = count

    @property
    def active(self) -> bool:
        return bool(self.selected)

    def apply(self, qs):
        return self._apply(qs, self.selected)

    def active_filters(self):
        return {self.param: self.selected} if self.selected else {}

    def counts(self, search):
        return self._count(search.filtered_except(self))

    def group(self, counts):
        choices = [Choice(key, label, key) for key, label in self.labels.items()]
        return select_multi_group(self.param, self.label, choices, self.selected, counts)


class DateFacet(Facet):
    """A single date (``beschikbaar_vanaf``); an unparsable value filters nothing.

    Its active value is the date itself, not a list: the chip formats it.
    """

    def __init__(self, param: str, label: str, raw: str, *, apply: Callable[[QuerySet, date], QuerySet]):
        self.key = self.param = param
        self.label = label
        try:
            self.value: date | None = date.fromisoformat(raw)
        except ValueError:
            self.value = None
        self._apply = apply

    @property
    def active(self) -> bool:
        return self.value is not None

    def apply(self, qs):
        return self._apply(qs, self.value)

    def active_filters(self):
        return {self.param: self.value} if self.value else {}

    def group(self, counts):
        return {"type": "date", "name": self.param, "label": self.label}


ORG_PARAMS = ("org", "org_self", "org_type", "org_type_in")


class OrgFacet(Facet):
    """The opdrachtgever facets (``org``/``org_self``/``org_type``/``org_type_in``).

    One facet for the four params: together they select one set of
    organizations, and the picker and its quick options treat them as one
    filter. ``org`` matches the whole subtree (plus units linked to it as their
    ministry, since those are not DB descendants), ``org_self`` only the org
    itself, ``org_type`` the roots in that top-level type folder of the picker
    plus their subtrees, and ``org_type_in`` every org of a type that nests under
    a given ministry.

    ``apply_ids`` narrows a queryset to rows of the matching organizations; it
    differs per list (a join, or a subquery where a join would duplicate rows).
    """

    key = param = "org"

    def __init__(
        self,
        resolver: FacetResolver,
        params: QueryDict,
        *,
        apply_ids: Callable[[QuerySet, set[int]], QuerySet],
        label: str = "Opdrachtgever",
    ):
        self.org = resolver("org", OrganizationUnit)
        self.org_self = resolver("org_self", OrganizationUnit)
        self.types = [value for value in params.getlist("org_type") if value]
        self.type_in = self._parse_type_in(params.getlist("org_type_in"))
        self._apply_ids = apply_ids
        self.label = label

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

    @property
    def active(self) -> bool:
        return bool(self.org.requested or self.org_self.requested or self.types or self.type_in)

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

    def apply(self, qs):
        return self._apply_ids(qs, self.matching_ids)

    def active_filters(self):
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

    def counts(self, search):
        return search.org_counts()

    def group(self, counts):
        return {
            "type": "modal",
            "name": "organisatie",
            "label": self.label,
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


def finalize_filter_groups(filter_groups: list[dict], *, top_n: int = 3) -> None:
    """Post-processes the select-multi groups in place for the top-N + "Meer" modal.

    Each group gets a unique ``group_id`` (the key the modal opens by),
    ``top_options`` (the ``top_n`` options by count, selected ones kept visible)
    and ``has_more``. The full alphabetical ``options`` list is kept for the modal.
    A group that already has a ``group_id`` is left as it is.
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
