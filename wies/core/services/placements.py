import csv
import datetime
import logging
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from wies.core.models import (
    DEFAULT_LABELS,
    Assignment,
    Colleague,
    Label,
    LabelCategory,
    Ministry,
    Placement,
    Service,
    Skill,
)
from wies.core.querysets import annotate_placement_dates, filter_by_date_overlap

logger = logging.getLogger(__name__)


def filter_placements_by_period(queryset, period):
    """
    Filter placement queryset by period range for overlapping periods.

    This function uses database-level annotations and filtering for optimal performance.

    Args:
        queryset: Placement queryset to filter
        period: Period string in format "YYYY-MM-DD_YYYY-MM-DD"

    Returns:
        Filtered queryset containing only placements that overlap with the given period
    """
    if not period:
        return queryset

    # Parse period in format "YYYY-MM-DD_YYYY-MM-DD"
    if "_" not in period:
        return queryset

    try:
        period_from_str, period_to_str = period.split("_", 1)
        period_from = datetime.date.fromisoformat(period_from_str)
        period_to = datetime.date.fromisoformat(period_to_str)

        # Annotate with actual dates at database level
        queryset = annotate_placement_dates(queryset)

        # Filter for overlapping periods at database level
        return filter_by_date_overlap(queryset, period_from, period_to)

    except ValueError:
        # Invalid date format, ignore filter
        return queryset


def create_placements_from_csv(csv_content: str):
    """
    Create colleagues, assignments, services and placements from csv
    """

    csv_reader = csv.DictReader(StringIO(csv_content))

    required_columns = {
        "assignment_name",
        "assignment_description",
        "assignment_owner",
        "assignment_owner_email",
        "assignment_organization",
        "assignment_ministry",
        "assignment_start_date",
        "assignment_end_date",
        "service_skill",
        "placement_colleague_name",
        "placement_colleague_email",
    }

    if not csv_reader.fieldnames:
        return {
            "success": False,
            "errors": ["CSV file is leeg of heeft geen headers."],
        }

    missing_columns = required_columns - set(csv_reader.fieldnames)
    if missing_columns:
        return {
            "success": False,
            "errors": [f"CSV mist kolommen: {', '.join(missing_columns)}."],
        }

    try:
        with transaction.atomic():
            # Get or create the 'Rijks ICT Gilde' label for newly created colleagues
            merken_category, _ = LabelCategory.objects.get_or_create(
                name="Merk",
                defaults={"color": DEFAULT_LABELS["Merk"]["color"]},
            )
            rijks_ict_gilde_label, _ = Label.objects.get_or_create(
                name="Rijks ICT Gilde",
                category=merken_category,
            )

            colleagues_created = 0
            assignments_created = 0
            services_created = 0
            placements_created = 0
            skills_created = 0
            ministries_created = 0
            for _, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
                assignment_owner_email = row["assignment_owner_email"]
                if assignment_owner_email != "":
                    validate_email(assignment_owner_email)
                    if Colleague.objects.filter(email=assignment_owner_email).exists():
                        owner = Colleague.objects.get(email=assignment_owner_email)
                    else:
                        owner = Colleague.objects.create(
                            name=row["assignment_owner"],
                            email=assignment_owner_email,
                            source="wies",
                        )
                        owner.labels.add(rijks_ict_gilde_label)
                        colleagues_created += 1
                else:
                    owner = None

                ministry_name = row["assignment_ministry"]
                if ministry_name != "":
                    ministry, created = Ministry.objects.get_or_create(
                        name=ministry_name,
                        defaults={"abbreviation": ministry_name},
                    )
                    if created:
                        ministries_created += 1
                else:
                    ministry = None

                # parse dates into proper types (timezone irrelevant - converting to date immediately)
                start_date = row["assignment_start_date"]
                end_date = row["assignment_end_date"]
                start_date = datetime.datetime.strptime(start_date, "%d-%m-%Y").date() if start_date else None  # noqa: DTZ007
                end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y").date() if end_date else None  # noqa: DTZ007

                # owner update or create
                assignment, created = Assignment.objects.get_or_create(
                    source="wies",
                    name=row["assignment_name"],
                    defaults={
                        "start_date": start_date,
                        "end_date": end_date,
                        "extra_info": row["assignment_description"],
                        "owner": owner,
                        "organization": row["assignment_organization"],
                        "ministry": ministry,
                        "status": "INGEVULD",
                    },
                )

                if created:
                    assignments_created += 1

                skill = row["service_skill"]
                if skill != "":
                    skill, created = Skill.objects.update_or_create(
                        name=skill,
                    )

                    if created:
                        skills_created += 1
                else:
                    skill = None

                service, created = Service.objects.get_or_create(
                    assignment=assignment,
                    skill=skill,
                    source="wies",
                )
                if created:
                    services_created += 1

                colleague_email = row["placement_colleague_email"]
                validate_email(colleague_email)
                if Colleague.objects.filter(email=colleague_email).exists():
                    colleague = Colleague.objects.get(email=colleague_email)
                else:
                    colleague = Colleague.objects.create(
                        name=row["placement_colleague_name"],
                        email=colleague_email,
                        source="wies",
                    )
                    colleague.labels.add(rijks_ict_gilde_label)
                    colleagues_created += 1

                _, created = Placement.objects.get_or_create(
                    colleague=colleague,
                    service=service,
                    source="wies",
                )
                if created:
                    placements_created += 1

    except ValueError as e:
        return {
            "success": False,
            "errors": [str(e)],
        }
    except ValidationError as e:
        return {
            "success": False,
            "errors": [str(e)],
        }
    except Exception:
        logger.exception("Unexpected error during placement CSV import")
        return {
            "success": False,
            "errors": ["Er is iets onverwachts misgegaan"],
        }
    else:
        return {
            "success": True,
            "colleagues_created": colleagues_created,
            "assignments_created": assignments_created,
            "services_created": services_created,
            "skills_created": skills_created,
            "ministries_created": ministries_created,
            "placements_created": placements_created,
            "errors": [],
        }
