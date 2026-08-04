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


_BACKFILL_BATCH_SIZE = 1000


def backfill_public_ids(apps, app_label: str, model_names: list[str]) -> None:
    """Give every existing row its own public_id, in batches.

    Used by the migrations that introduce the column. It cannot be a plain
    ``AddField`` default: a callable default is evaluated once, so every existing
    row would get the same value and the unique constraint would reject it.
    OrganizationUnit holds the whole national register, hence ``bulk_update``
    rather than a save() per row.
    """
    for model_name in model_names:
        model = apps.get_model(app_label, model_name)
        batch = []
        for obj in model.objects.filter(public_id__isnull=True).iterator():
            obj.public_id = generate_public_id()
            batch.append(obj)
            if len(batch) >= _BACKFILL_BATCH_SIZE:
                model.objects.bulk_update(batch, ["public_id"])
                batch = []
        if batch:
            model.objects.bulk_update(batch, ["public_id"])


@dataclass(frozen=True)
class ResolvedFacet:
    """One filter facet's public_id tokens resolved against the database.

    ``requested`` is True as soon as the param appears in the URL, even when not
    a single token resolves. That is what makes an unknown or malformed value
    fail closed: the caller applies the filter with an empty id list and gets no
    rows, rather than dropping the filter and widening the result. A stale id in
    a shared or bookmarked URL must never quietly show more than it asks for.

    ``public_ids`` and ``ids`` hold only the tokens that match a real row, in URL
    order, deduplicated, and index-aligned with each other.
    """

    requested: bool
    public_ids: list[str] = field(default_factory=list)
    ids: list[int] = field(default_factory=list)


def resolve_facet(model: type[Model], tokens: list[str]) -> ResolvedFacet:
    """Resolve one facet's raw query-param values against ``model``."""
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
    for token in tokens:
        row_id = id_by_public_id.get(str(token))
        if row_id is None or str(token) in public_ids:
            continue
        public_ids.append(str(token))
        ids.append(row_id)
    return ResolvedFacet(requested=True, public_ids=public_ids, ids=ids)


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
