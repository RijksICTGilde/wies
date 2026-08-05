"""Assignment counts per primary opdrachtgever for the BM "Opdrachten" page.

Exploratory BM-feature (branch ``explore-bm-views``). Answers "how are our
assignments spread over clients?" by counting, per primary opdrachtgever
(``role="PRIMARY"``), how many assignments it owns — split into two groups:

- **ministeries**: ALL ministries, including those with 0 opdrachten.
- **agentschappen**: only agentschappen with at least 1 opdracht.

Each block gets a STABLE decorative colour keyed to the organisation id (not
its render position), so a given client always shows the same colour. Ministries
have no real house colours (shared rijkshuisstijl); the sole exception is
Defensie, which uses orange — flagged here so the template can special-case it.

No permission modelling (demo): every viewer sees every client.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from wies.core.models import AssignmentOrganizationUnit, OrganizationUnit, OrganizationUnitRole

# Size of the decorative palette defined in ``static/css/bm_opdrachten.css``
# (classes ``--c0`` … ``--c{PALETTE_LEN - 1}``). Colour index = org id % this.
PALETTE_LEN = 8


@dataclass
class ClientCount:
    """One block: a primary opdrachtgever with its assignment count."""

    name: str
    count: int
    color_index: int
    is_defensie: bool


def _display_name(org: OrganizationUnit) -> str:
    """Main abbreviation (e.g. "OCW"), falling back to label or name."""
    if org.abbreviations:
        return org.abbreviations[0]
    return org.label or org.name


def _is_defensie(org: OrganizationUnit) -> bool:
    """Whether this org is Defensie — the one ministry with a real house colour."""
    haystack = f"{' '.join(org.abbreviations)} {org.label} {org.name}".lower()
    return "defensie" in haystack


def _to_client_count(org: OrganizationUnit, counts: Counter[int]) -> ClientCount:
    return ClientCount(
        name=_display_name(org),
        count=counts.get(org.id, 0),
        color_index=org.id % PALETTE_LEN,
        is_defensie=_is_defensie(org),
    )


def assignments_per_primary_client() -> dict:
    """Assignment counts per primary opdrachtgever, split by org type.

    Returns ``{"ministeries": [ClientCount, ...], "agentschappen": [...]}``:
    - ministeries: ALL ministries, incl. count 0, sorted by name.
    - agentschappen: only those with count >= 1, sorted by count desc then name.
    """
    # PRIMARY-only counts per org id. (The plain ``organizations`` M2M would
    # also count INVOLVED parties, so we go through the role-carrying table.)
    counts: Counter[int] = Counter(
        AssignmentOrganizationUnit.objects.filter(role=OrganizationUnitRole.PRIMARY).values_list(
            "organization_id", flat=True
        )
    )

    # Filter on ``label`` (reliably capitalised "Ministerie"/"Agentschap"); the
    # live overheid.nl sync lowercases ``name`` ("ministerie"), so filtering on
    # ``name`` would match nothing. ``label`` is what the org filters use too.
    ministries = OrganizationUnit.objects.filter(organization_types__label="Ministerie").distinct()
    ministeries = sorted(
        (_to_client_count(org, counts) for org in ministries),
        key=lambda c: c.name.lower(),
    )

    agencies = OrganizationUnit.objects.filter(organization_types__label="Agentschap").distinct()
    agentschappen = sorted(
        (c for org in agencies if (c := _to_client_count(org, counts)).count >= 1),
        key=lambda c: (-c.count, c.name.lower()),
    )

    return {"ministeries": ministeries, "agentschappen": agentschappen}
