"""The ``public_id`` shown in URLs; the integer PK stays internal.

A UUIDv4 — the industry-standard opaque, unguessable identifier — so URLs never
expose the sequential PK. Rationale (and why it is a separate column, not the PK)
in ``features/public_id.md``.
"""

import contextlib
import uuid


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
