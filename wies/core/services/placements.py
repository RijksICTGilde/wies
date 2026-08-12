import csv
import datetime
import logging
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DataError, IntegrityError, transaction
from django.db.models import Q

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
from wies.core.services.suborganizations import get_suborganization_by_name
from wies.core.services.users import validate_email_domain

logger = logging.getLogger(__name__)


def parse_date_dmy(date_str: str) -> datetime.date:
    """Parses a DD-MM-YYYY date string into a ``datetime.date``."""
    day, month, year = date_str.split("-")
    return datetime.date(int(year), int(month), int(day))


def filter_placements_by_period(queryset, period_from, period_to):
    """Filters the queryset down to placements overlapping ``period_from``..``period_to``."""
    return queryset.filter(
        Q(actual_start_date__lte=period_to)
        & Q(actual_end_date__gte=period_from)
        & Q(actual_start_date__isnull=False)
        & Q(actual_end_date__isnull=False)
    )


def filter_placements_by_min_end_date(queryset, min_end_date):
    return queryset.filter(Q(actual_end_date__gte=min_end_date) | Q(actual_end_date__isnull=True))


def filter_visible_placements(queryset, today, viewer):
    """Filters the overview list by placement visibility.

    Active placements are public, ended ones hidden from everyone, and not-yet-
    started ones kept only for the placed colleague and the assignment's BM-owner.
    Requires ``annotate_placement_dates`` to have been applied first.
    """
    queryset = filter_placements_by_min_end_date(queryset, today)
    started = Q(actual_start_date__isnull=True) | Q(actual_start_date__lte=today)
    if viewer is None:
        return queryset.filter(started)
    return queryset.filter(started | Q(colleague_id=viewer.id) | Q(service__assignment__owner_id=viewer.id))


def create_assignments_from_csv(creator, csv_content: str, request=None):
    """Creates colleagues, assignments, services and placements from CSV.

    Required columns: assignment_name, assignment_description, assignment_owner,
    assignment_owner_email, assignment_start_date, assignment_end_date,
    service_skill, placement_colleague_name, placement_colleague_email.

    Optional: client_1_url (PRIMARY client) and client_2_url / client_3_url
    (INVOLVED clients), all organisaties.overheid.nl URLs; owner_brand and
    colleague_brand set the suborganization on newly created colleagues.
    """
    try:
        dialect = csv.Sniffer().sniff(csv_content[:1024], delimiters=",;")
    except csv.Error:
        return {
            "success": False,
            "errors": ["Kon het CSV-formaat niet bepalen. Controleer of het een geldig CSV-bestand is."],
        }
    csv_reader = csv.DictReader(StringIO(csv_content), delimiter=dialect.delimiter)

    required_columns = {
        "assignment_name",
        "assignment_description",
        "assignment_owner",
        "assignment_owner_email",
        "assignment_start_date",
        "assignment_end_date",
        "service_skill",
        "placement_colleague_name",
        "placement_colleague_email",
    }

    if not csv_reader.fieldnames:
        return {"success": False, "errors": ["CSV file is leeg of heeft geen headers."]}

    missing_columns = required_columns - set(csv_reader.fieldnames)
    if missing_columns:
        return {"success": False, "errors": [f"CSV mist kolommen: {', '.join(missing_columns)}."]}

    try:
        with transaction.atomic():
            # Caches brand → Suborganization lookups across rows.
            suborg_mapping = {}

            def resolve_suborganization(brand_name):
                brand_name = (brand_name or "").strip()
                if not brand_name:
                    return None
                if brand_name not in suborg_mapping:
                    suborg_mapping[brand_name] = get_suborganization_by_name(brand_name)
                return suborg_mapping[brand_name]

            colleagues_created = 0
            assignments_created = 0
            services_created = 0
            placements_created = 0
            skills_created = 0
            organizations_linked = 0
            for _, row in enumerate(csv_reader, start=2):  # Row 1 is the header.
                owner_suborg = resolve_suborganization(row.get("owner_brand"))
                colleague_suborg = resolve_suborganization(row.get("colleague_brand"))

                assignment_owner_email = row["assignment_owner_email"]
                if assignment_owner_email != "":
                    validate_email(assignment_owner_email)
                    owner = Colleague.objects.filter(email__iexact=assignment_owner_email).order_by("id").first()
                    if owner is None:
                        validate_email_domain(assignment_owner_email, user_facing=True)
                        owner = Colleague.objects.create(
                            name=row["assignment_owner"],
                            email=assignment_owner_email,
                            source="wies",
                            suborganization=owner_suborg,
                        )
                        colleagues_created += 1
                else:
                    owner = None

                client_urls = [
                    (row.get("client_1_url", "").strip(), "PRIMARY"),
                    (row.get("client_2_url", "").strip(), "INVOLVED"),
                    (row.get("client_3_url", "").strip(), "INVOLVED"),
                ]

                start_date_str = row["assignment_start_date"] or ""
                end_date_str = row["assignment_end_date"] or ""
                start_date = parse_date_dmy(start_date_str) if start_date_str else None
                end_date = parse_date_dmy(end_date_str) if end_date_str else None

                assignment, created = Assignment.objects.get_or_create(
                    source="wies",
                    name=row["assignment_name"],
                    defaults={
                        "start_date": start_date,
                        "end_date": end_date,
                        "extra_info": row["assignment_description"],
                        "owner": owner,
                    },
                )

                if created:
                    assignments_created += 1
                    create_event(
                        object_type="Assignment",
                        action="create",
                        source="user",
                        object_id=assignment.id,
                        user=creator,
                        request=request,
                        context={
                            "assignment_name": assignment.name,
                        },
                    )

                for url, role in client_urls:
                    if not url:
                        continue
                    organization = OrganizationUnit.objects.filter(source_url=url).first()
                    if organization and not assignment.organizations.filter(id=organization.id).exists():
                        AssignmentOrganizationUnit.objects.create(
                            assignment=assignment, organization=organization, role=role
                        )
                        organizations_linked += 1

                skill = row["service_skill"]
                if skill != "":
                    skill, created = Skill.objects.update_or_create(
                        name=skill,
                    )

                    if created:
                        skills_created += 1
                else:
                    skill = None

                colleague_email = (row["placement_colleague_email"] or "").strip()
                if colleague_email:
                    validate_email(colleague_email)
                    colleague = Colleague.objects.filter(email__iexact=colleague_email).order_by("id").first()
                    if colleague is None:
                        validate_email_domain(colleague_email, user_facing=True)
                        colleague = Colleague.objects.create(
                            name=row["placement_colleague_name"],
                            email=colleague_email,
                            source="wies",
                            suborganization=colleague_suborg,
                        )
                        colleagues_created += 1

                    existing_placement = Placement.objects.filter(
                        colleague=colleague,
                        service__assignment=assignment,
                        service__skill=skill,
                        service__source="wies",
                        source="wies",
                    ).first()
                    if existing_placement is not None:
                        service = existing_placement.service
                    else:
                        service = Service.objects.create(
                            assignment=assignment,
                            skill=skill,
                            source="wies",
                        )
                        services_created += 1

                    _, created = Placement.objects.get_or_create(
                        colleague=colleague,
                        service=service,
                        source="wies",
                    )
                    if created:
                        placements_created += 1
                else:
                    service = Service.objects.filter(
                        assignment=assignment,
                        skill=skill,
                        source="wies",
                        placements__isnull=True,
                    ).first()
                    if service is None:
                        Service.objects.create(
                            assignment=assignment,
                            skill=skill,
                            source="wies",
                        )
                        services_created += 1

    except ValueError as e:
        return {"success": False, "errors": [str(e)]}
    except ValidationError as e:
        return {"success": False, "errors": [str(e)]}
    except (DataError, IntegrityError, csv.Error) as e:
        logger.warning("Opdracht-CSV import failed with a data error", exc_info=e)
        return {
            "success": False,
            "errors": ["Er ging iets mis bij het verwerken van het bestand. Controleer de waarden in het CSV-bestand."],
        }
    else:
        return {
            "success": True,
            "colleagues_created": colleagues_created,
            "assignments_created": assignments_created,
            "services_created": services_created,
            "skills_created": skills_created,
            "organizations_linked": organizations_linked,
            "placements_created": placements_created,
            "errors": [],
        }


def placement_edit_specs(placement, user, only=None):
    """Returns the placement panel's editable specs, each with its own object.

    Three fields across two models (Service.skill, Service.description,
    Placement.period). Only specs the user may UPDATE come back, so the form never
    shows a field that would be refused on save.

    ``only`` (a spec name) narrows it to one field, as with the assignment. "Rol"
    covers two specs, since the role and its description share a row.
    """
    from wies.core.editables.placement import PlacementEditables  # noqa: PLC0415 — avoids import cycle
    from wies.core.editables.service import ServiceEditables  # noqa: PLC0415
    from wies.core.permission_engine import Verb, has_permission  # noqa: PLC0415

    service = placement.service
    candidates = [
        (ServiceEditables, ServiceEditables.skill, service),
        (ServiceEditables, ServiceEditables.description, service),
        (PlacementEditables, PlacementEditables.period, placement),
    ]
    if only is not None:
        # The role row shows the role with its description below it, so both
        # belong in the same form.
        wanted = {"skill", "description"} if only == "skill" else {only}
        candidates = [(s, spec, obj) for (s, spec, obj) in candidates if spec.name in wanted]
    return [(s, spec, obj) for (s, spec, obj) in candidates if has_permission(Verb.UPDATE, obj, user, spec)]


def save_placement_edit(request, placement, specs, cleaned_data):
    """Saves all specs in one transaction, with the same audit events as inline edit."""
    from contextlib import nullcontext  # noqa: PLC0415 (import not at top level) — only used here

    from wies.core.editables.placement import PlacementEditables  # noqa: PLC0415 — avoids import cycle
    from wies.core.services.inline_edit_save import save_edit_specs  # noqa: PLC0415 — avoids import cycle

    # A placement change has no audit type of its own; audit_mirror mirrors it as a
    # "Team" event on the assignment timeline, like the inline-edit flow (#393).
    mirror = PlacementEditables.audit_mirror
    with transaction.atomic(), mirror(placement, request.user, request) if mirror else nullcontext():
        save_edit_specs(request, specs, cleaned_data)
