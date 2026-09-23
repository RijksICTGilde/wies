"""Importer: an ``OtysImportBatch`` -> Wies models.

Source-agnostic on purpose: it never sees a spreadsheet, only the intermediate
``OtysImportBatch``. When the OTYS API replaces the Excel upload, the same
function runs unchanged against a batch built from the API.

Everything is keyed on ``source="otys_iir"`` plus a stable ``source_id`` (the
vacancy reference for assignments/services, the placement number for
placements), so re-uploading an updated export upserts in place rather than
duplicating. This mirrors ``services/sync.py``'s ``update_or_create`` pattern.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DataError, IntegrityError, transaction

from wies.core.errors import SuborganizationNotFoundError
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)
from wies.core.services.events import create_event
from wies.core.services.otys_import.ministries import resolve_ministry_system_id
from wies.core.services.otys_import.records import OtysImportBatch, OtysVacancy
from wies.core.services.suborganizations import get_suborganization_by_name
from wies.core.services.users import validate_email_domain

logger = logging.getLogger(__name__)

SOURCE = "otys_iir"
# OTYS-synced colleagues all belong to this brand, as in ``services/sync.py``.
OTYS_SUBORGANIZATION = "I-Interim Rijk"


class OtysImportError(Exception):
    """A record could not be imported. Raised with a Dutch, user-facing message.

    The importer fails fast on the first problem: raising this inside the atomic
    block rolls the whole import back, so a half-imported batch is never saved.
    """


# No ``source_url`` is set on imported records for now. The manual export only
# carries human references (e.g. ``RIG03965``), not the internal OTYS uid its deep
# links need, and we don't yet have a correct URL scheme. Leaving source_url empty
# makes the "Externe bron" render as plain text ("OTYS IIR") instead of a broken
# link. The API adapter will supply real uid links later.


def _get_or_create_colleague(email: str, name: str, suborg, counters: dict) -> Colleague | None:
    """Upserts an OTYS colleague by email, validating the address first."""
    email = (email or "").strip()
    if not email:
        return None
    validate_email(email)
    colleague = Colleague.objects.filter(email__iexact=email, source=SOURCE).order_by("id").first()
    if colleague is None:
        validate_email_domain(email, user_facing=True)
        colleague = Colleague.objects.create(
            name=name,
            email=email,
            source=SOURCE,
            suborganization=suborg,
        )
        counters["colleagues_created"] += 1
    else:
        # Keep the display name fresh on re-import; the email is the identity.
        if name and colleague.name != name:
            colleague.name = name
            colleague.save(update_fields=["name"])
        counters["colleagues_updated"] += 1
    return colleague


def _resolve_skill(vacancy: OtysVacancy, counters: dict) -> Skill | None:
    """Resolves the vacancy's function (e.g. "CIO") to a ``Skill``.

    ``Skill.name`` is unique and capped at 30 chars; a role longer than that
    fails the import rather than being silently truncated.
    """
    role = vacancy.role.strip()
    if not role:
        return None
    max_length = Skill._meta.get_field("name").max_length  # noqa: SLF001 — read the model's own limit
    if len(role) > max_length:
        raise OtysImportError(f"Rol '{role}' voor opdracht {vacancy.reference} is te lang (max {max_length} tekens).")
    skill, created = Skill.objects.get_or_create(name=role)
    if created:
        counters["skills_created"] += 1
    return skill


def _link_ministry(assignment: Assignment, vacancy: OtysVacancy, counters: dict) -> None:
    """Links the assignment's primary opdrachtgever from the ministry code.

    Fails the import (raises ``OtysImportError``) when the ministry can't be
    resolved, rather than silently leaving the opdracht without an opdrachtgever.
    """
    if not vacancy.ministry_code:
        raise OtysImportError(f"Opdracht {vacancy.reference} heeft geen ministerie ingevuld.")
    system_id = resolve_ministry_system_id(vacancy.ministry_code)
    if system_id is None:
        raise OtysImportError(
            f"Onbekend ministerie '{vacancy.ministry_code}' voor opdracht {vacancy.reference}. "
            "Vul de ministerie-map aan of corrigeer de export."
        )
    # Match on the stable numeric id inside the synced source_url, which carries
    # a name-derived slug and trailing slash we can't reproduce by hand.
    organization = (
        OrganizationUnit.objects.filter(source_url__contains=f"/{system_id}/")
        .exclude(source_url="")
        .order_by("id")
        .first()
    )
    if organization is None:
        raise OtysImportError(
            f"Geen organisatie gevonden voor ministerie '{vacancy.ministry_code}' "
            f"(id {system_id}). Is de organisatiesync uitgevoerd?"
        )
    _, created = AssignmentOrganizationUnit.objects.get_or_create(
        assignment=assignment,
        organization=organization,
        defaults={"role": "PRIMARY"},
    )
    if created:
        counters["organizations_linked"] += 1


def _placement_period(placement, vacancy) -> dict:
    """Chooses SERVICE (inherit) or PLACEMENT (own dates) for the placement.

    The service inherits the assignment period (the vacancy dates), so a
    placement whose own dates match those (or are absent) inherits too. Only when
    they genuinely differ does the placement carry its own specific period.
    """
    start, end = placement.start_date, placement.end_date
    inherits = (start is None or start == vacancy.start_date) and (end is None or end == vacancy.end_date)
    if inherits:
        return {"period_source": "SERVICE", "specific_start_date": None, "specific_end_date": None}
    return {"period_source": "PLACEMENT", "specific_start_date": start, "specific_end_date": end}


def _upsert_placement(placement, service_by_reference: dict, suborg, counters: dict) -> None:
    """Upserts one placement, failing the import when it can't be linked."""
    linked = service_by_reference.get(placement.vacancy_reference)
    if linked is None:
        raise OtysImportError(
            f"Plaatsing {placement.placement_number} verwijst naar vacature "
            f"{placement.vacancy_reference}, die niet in het bestand staat."
        )
    service, vacancy = linked

    colleague = _get_or_create_colleague(placement.candidate.email, placement.candidate.name, suborg, counters)
    if colleague is None:
        raise OtysImportError(f"Plaatsing {placement.placement_number} heeft geen kandidaat-email.")

    _, created = Placement.objects.update_or_create(
        source_id=placement.placement_number,
        source=SOURCE,
        defaults={
            "colleague": colleague,
            "service": service,
            **_placement_period(placement, vacancy),
        },
    )
    counters["placements_created" if created else "placements_updated"] += 1


def import_batch(batch: OtysImportBatch, creator, request=None) -> dict:
    """Imports a batch of OTYS records, upserting on the source keys.

    Fails fast: the whole batch runs in one transaction and the first problem
    (unresolvable ministry, dangling placement, missing/invalid email) rolls
    everything back and returns ``success=False`` with the reason. Nothing is
    saved partially.
    """
    counters = {
        "colleagues_created": 0,
        "colleagues_updated": 0,
        "assignments_created": 0,
        "assignments_updated": 0,
        "services_created": 0,
        "services_updated": 0,
        "skills_created": 0,
        "placements_created": 0,
        "placements_updated": 0,
        "organizations_linked": 0,
    }

    try:
        with transaction.atomic():
            otys_suborg = get_suborganization_by_name(OTYS_SUBORGANIZATION)

            # Upsert vacancies -> Assignment + Service, keyed on the reference.
            # The vacancy travels alongside its service so a placement can compare
            # its own period against the (inherited) service period.
            service_by_reference: dict[str, tuple[Service, OtysVacancy]] = {}
            for vacancy in batch.vacancies:
                owner = _get_or_create_colleague(vacancy.owner_email, vacancy.owner_name, otys_suborg, counters)

                assignment, created = Assignment.objects.update_or_create(
                    source_id=vacancy.reference,
                    source=SOURCE,
                    defaults={
                        "name": vacancy.name or vacancy.reference,
                        "start_date": vacancy.start_date,
                        "end_date": vacancy.end_date,
                        "extra_info": vacancy.description[:5000],
                        "owner": owner,
                    },
                )
                counters["assignments_created" if created else "assignments_updated"] += 1
                if created:
                    create_event(
                        object_type="Assignment",
                        action="create",
                        source="user",
                        object_id=assignment.id,
                        user=creator,
                        request=request,
                        context={"assignment_name": assignment.name},
                    )

                _link_ministry(assignment, vacancy, counters)

                skill = _resolve_skill(vacancy, counters)
                service, service_created = Service.objects.update_or_create(
                    source_id=vacancy.reference,
                    source=SOURCE,
                    defaults={
                        "assignment": assignment,
                        "description": (vacancy.name or vacancy.reference)[:500],
                        "skill": skill,
                        "period_source": "ASSIGNMENT",
                    },
                )
                counters["services_created" if service_created else "services_updated"] += 1
                service_by_reference[vacancy.reference] = (service, vacancy)

            # Upsert placements -> Placement, keyed on the placement number.
            for placement in batch.placements:
                _upsert_placement(placement, service_by_reference, otys_suborg, counters)

    except OtysImportError as exc:
        return {"success": False, "errors": [str(exc)]}
    except SuborganizationNotFoundError:
        message = f"De vereiste merk '{OTYS_SUBORGANIZATION}' bestaat niet. Maak dit merk aan voordat je importeert."
        return {"success": False, "errors": [message]}
    except ValidationError as exc:
        # ``validate_email`` wraps its message in a list; join to a plain sentence.
        return {"success": False, "errors": ["; ".join(exc.messages)]}
    except (DataError, IntegrityError) as exc:
        logger.warning("OTYS import failed with a data error", exc_info=exc)
        return {
            "success": False,
            "errors": ["Er ging iets mis bij het verwerken van het bestand. Controleer de waarden."],
        }
    else:
        return {"success": True, "errors": [], **counters}
