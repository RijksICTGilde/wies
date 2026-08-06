"""The ``public_id`` shown in URLs; the integer PK stays internal.

A UUIDv4, the industry-standard opaque unguessable identifier, so URLs never
expose the sequential PK. Rationale (and why it is a separate column, not the PK)
in ``features/public_id.md``.
"""

from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import Model
    from django.http import HttpRequest


def generate_public_id() -> uuid.UUID:
    return uuid.uuid4()


def parse_public_ids(values) -> list[uuid.UUID]:
    """Parse URL/filter tokens into UUIDs, silently dropping unparseable ones.

    Filter facets (``?org=``/``?rol=``/``?labels=``) take raw query params; a
    ``UUIDField`` lookup would otherwise raise on a non-UUID value, so junk is
    dropped here and simply matches nothing."""
    parsed = []
    for value in values:
        with contextlib.suppress(ValueError, TypeError):
            parsed.append(uuid.UUID(str(value)))
    return parsed


@dataclass(frozen=True)
class ResolvedFacet:
    """One filter facet's public_id tokens resolved against the database.

    ``requested`` is True once the param carries at least one non-empty value,
    even when none of them resolves. That is what makes an unknown or malformed
    value fail closed: the caller applies the filter with an empty id list and
    gets no rows, rather than dropping the filter and widening the result. A
    stale id in a shared or bookmarked URL must never quietly show more than it
    asks for.

    An empty value (``?org=``) is no selection at all, not a selection that
    matched nothing, so it leaves ``requested`` False.

    ``public_ids`` and ``ids`` hold the tokens that match a real row, in URL
    order, deduplicated, and index-aligned with each other. ``unresolved`` holds
    the rest: they filter everything away, but the caller must still surface them
    as an active filter, otherwise the user is left on an empty list with nothing
    to see or clear.
    """

    requested: bool
    public_ids: list[str] = field(default_factory=list)
    ids: list[int] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    @property
    def active_values(self) -> list[str]:
        """Every value that is filtering, whether it resolved or not."""
        return [*self.public_ids, *self.unresolved]


def resolve_facet(model: type[Model], tokens: list[str]) -> ResolvedFacet:
    """Resolve one facet's raw query-param values against ``model``."""
    tokens = [str(token) for token in tokens if str(token).strip()]
    if not tokens:
        return ResolvedFacet(requested=False)
    id_by_public_id = {
        str(public_id): row_id
        for public_id, row_id in model.objects.filter(public_id__in=parse_public_ids(tokens)).values_list(
            "public_id", "id"
        )
    }
    public_ids: list[str] = []
    ids: list[int] = []
    unresolved: list[str] = []
    for token in tokens:
        if token in public_ids or token in unresolved:
            continue
        row_id = id_by_public_id.get(token)
        if row_id is None:
            unresolved.append(token)
            continue
        public_ids.append(token)
        ids.append(row_id)
    return ResolvedFacet(requested=True, public_ids=public_ids, ids=ids, unresolved=unresolved)


class FacetResolver:
    """Resolves a request's public_id filter params, once per facet.

    List views call ``_apply_filters`` once per facet to compute the cross-filter
    counts, so resolving inline would repeat the same lookup on every call.
    """

    def __init__(self, request: HttpRequest):
        self._request = request
        self._cache: dict[tuple[str, type[Model]], ResolvedFacet] = {}

    def __call__(self, param: str, model: type[Model]) -> ResolvedFacet:
        key = (param, model)
        if key not in self._cache:
            self._cache[key] = resolve_facet(model, self._request.GET.getlist(param))
        return self._cache[key]
