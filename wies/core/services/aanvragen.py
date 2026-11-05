"""Aanvragen: the open roles on an opdracht that nobody fills yet."""

from collections import Counter
from dataclasses import dataclass

from django.db.models import Exists, OuterRef, QuerySet
from django.db.models.functions import Lower, Trim

from wies.core.models import Assignment, Service
from wies.core.querysets import annotate_service_dates
from wies.core.services.dates import date_range_text, request_period_text
from wies.core.services.organizations import get_excluded_org_ids

# How many placed colleagues the aanvraag panel names; the rest is a count.
TEAM_NAMES_SHOWN = 2


def open_aanvragen() -> QuerySet[Service]:
    """Every open, unfilled role, with its effective dates. Hides
    intelligence-service orgs, as the placement list does."""
    qs = annotate_service_dates(Service.objects.filter(status="OPEN", placements__isnull=True))
    excluded_org_ids = get_excluded_org_ids()
    if excluded_org_ids:
        qs = qs.exclude(assignment__organizations__id__in=excluded_org_ids)
    return qs


def assignments_without_aanvraag() -> QuerySet[Assignment]:
    """Opdrachten without any role yet, such as one just entered. Aanvragen
    lists them, or they could not be found anywhere once created.

    ``~Exists``, not ``services__isnull=True``: that is a LEFT JOIN and gives
    duplicate rows as soon as a filter also joins the opdrachtgevers.
    """
    qs = Assignment.objects.filter(~Exists(Service.objects.filter(assignment=OuterRef("pk"))))
    excluded_org_ids = get_excluded_org_ids()
    if excluded_org_ids:
        qs = qs.exclude(organizations__id__in=excluded_org_ids)
    return qs


def aanvraag_role(service: Service) -> str | None:
    """The role an aanvraag asks for. The OTYS sync sets no skill; it puts the
    role from the vacancy title in ``description``."""
    if service.skill_id:
        return service.skill.name
    if service.source == "otys_iir":
        return service.description or None
    return None


def team_names_text(rows: list[dict]) -> str:
    """Who is on the opdracht now, from ``visible_service_rows``: "Anke de
    Vries, Bram Jansen en 3 anderen". A colleague in two roles counts once."""
    names = list(dict.fromkeys(row["colleague"].name for row in rows if row["placement"] and not row.get("historical")))
    if not names:
        return "Nog niemand geplaatst"
    shown, rest = names[:TEAM_NAMES_SHOWN], len(names) - TEAM_NAMES_SHOWN
    if rest <= 0:
        return " en ".join(shown)
    return f"{', '.join(shown)} en {rest} {'ander' if rest == 1 else 'anderen'}"


def standplaats_key(location: str) -> str:
    """Case- and space-insensitive, so "Den Haag" and "den haag " are one standplaats."""
    return location.strip().lower()


def standplaats_labels(services: QuerySet[Service]) -> dict[str, str]:
    """Every standplaats in ``services`` by ``standplaats_key``, sorted. The
    label is the most common spelling; on a tie, the capitalised one."""
    spellings = Counter(
        location.strip() for location in services.exclude(location="").values_list("location", flat=True)
    )
    labels = {}
    for spelling, _ in sorted(spellings.items(), key=lambda item: (-item[1], item[0])):
        labels.setdefault(standplaats_key(spelling), spelling)
    return dict(sorted(labels.items()))


def known_standplaatsen(requested: list[str], labels: dict[str, str]) -> list[str]:
    """The requested standplaatsen that exist; an unknown one is dropped
    rather than emptying the list without a chip to undo it."""
    return sorted({standplaats_key(value) for value in requested} & labels.keys())


def filter_on_standplaatsen(services: QuerySet[Service], keys: list[str]) -> QuerySet[Service]:
    return services.annotate(location_key=Lower(Trim("location"))).filter(location_key__in=keys)


@dataclass(frozen=True)
class AanvraagCard:
    """One card on Aanvragen: an open aanvraag, or an opdracht without one."""

    title: str
    opdracht: str
    link_name: str
    panel_url: str
    org_label: str | None
    period_text: str
    location: str = ""
    hours_per_week: int | None = None


def _first_org_label(assignment: Assignment) -> str | None:
    # Needs the ``organizations_by_pk`` prefetch: the first opdrachtgever on pk,
    # as organizations.first() would pick it.
    first_org = next(iter(assignment.organizations_by_pk), None)
    return (first_org.label or first_org.name) if first_org else None


def aanvraag_card(service: Service, panel_url: str) -> AanvraagCard:
    role = aanvraag_role(service)
    return AanvraagCard(
        title=role or "Rol niet ingevuld",
        opdracht=service.assignment.name,
        link_name=f"{role or 'Aanvraag zonder rol'} bij {service.assignment.name}",
        panel_url=panel_url,
        org_label=_first_org_label(service.assignment),
        period_text=request_period_text(service) or "Geen periode opgegeven",
        location=service.location,
        hours_per_week=service.hours_per_week,
    )


def opdracht_without_aanvraag_card(assignment: Assignment, panel_url: str) -> AanvraagCard:
    return AanvraagCard(
        title="Nog geen aanvraag",
        opdracht=assignment.name,
        link_name=f"{assignment.name}, nog geen aanvraag",
        panel_url=panel_url,
        org_label=_first_org_label(assignment),
        period_text=date_range_text(assignment.start_date, assignment.end_date) or "Geen periode opgegeven",
    )
