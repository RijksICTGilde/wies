import csv
import datetime
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q

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


def parse_date_dmy(date_str: str) -> datetime.date:
    """Parse date string in DD-MM-YYYY format to datetime.date."""
    day, month, year = date_str.split("-")
    return datetime.date(int(year), int(month), int(day))


def filter_placements_by_period(queryset, period_from, period_to):
    """
    Filter placement queryset by period range for overlapping periods.

    Args:
        queryset: Placement queryset to filter
        period_from: date object
        period_from: date object
    Returns:
        Filtered queryset containing only placements that overlap with the given period
    """

    return queryset.filter(
        Q(actual_start_date__lte=period_to)
        & Q(actual_end_date__gte=period_from)
        & Q(actual_start_date__isnull=False)
        & Q(actual_end_date__isnull=False)
    )


def filter_placements_by_min_end_date(queryset, min_end_date):
    return queryset.filter(Q(actual_end_date__gte=min_end_date) | Q(actual_end_date__isnull=True))


def create_assignments_from_csv(csv_content: str):
    """
    Create colleagues, assignments, services and placements from csv.

    The CSV should contain the following required columns:
    - assignment_name, assignment_description, assignment_owner, assignment_owner_email
    - assignment_organization, assignment_ministry, assignment_start_date, assignment_end_date
    - service_skill, placement_colleague_name, placement_colleague_email

    Optional columns:
    - owner_brand: If provided, assigns the brand label to newly created assignment owners.
                   If empty or not provided, no brand label is assigned.
    - colleague_brand: If provided, assigns the brand label to newly created placement colleagues.
                       If empty or not provided, no brand label is assigned.
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
        return {"success": False, "errors": ["CSV file is leeg of heeft geen headers."]}

    missing_columns = required_columns - set(csv_reader.fieldnames)
    if missing_columns:
        return {"success": False, "errors": [f"CSV mist kolommen: {', '.join(missing_columns)}."]}

    try:
        with transaction.atomic():
            # Get or create the 'Merk' (Brand) label category
            merken_category, _ = LabelCategory.objects.get_or_create(
                name="Merk", defaults={"color": DEFAULT_LABELS["Merk"]["color"]}
            )

            # Cache for brand labels to avoid repeated database queries
            label_mapping = {}

            colleagues_created = 0
            assignments_created = 0
            services_created = 0
            placements_created = 0
            skills_created = 0
            ministries_created = 0
            for _, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
                # Get owner brand label if specified in CSV
                owner_brand_name = row.get("owner_brand", "").strip()
                owner_brand_label = None
                if owner_brand_name:
                    if owner_brand_name in label_mapping:
                        owner_brand_label = label_mapping[owner_brand_name]
                    else:
                        owner_brand_label, _ = Label.objects.get_or_create(
                            name=owner_brand_name, category=merken_category
                        )
                        label_mapping[owner_brand_name] = owner_brand_label

                # Get colleague brand label if specified in CSV
                colleague_brand_name = row.get("colleague_brand", "").strip()
                colleague_brand_label = None
                if colleague_brand_name:
                    if colleague_brand_name in label_mapping:
                        colleague_brand_label = label_mapping[colleague_brand_name]
                    else:
                        colleague_brand_label, _ = Label.objects.get_or_create(
                            name=colleague_brand_name, category=merken_category
                        )
                        label_mapping[colleague_brand_name] = colleague_brand_label

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
                        if owner_brand_label:
                            owner.labels.add(owner_brand_label)
                        colleagues_created += 1
                else:
                    owner = None

                ministry_name = row["assignment_ministry"]
                if ministry_name != "":
                    ministry, created = Ministry.objects.get_or_create(
                        name=ministry_name, defaults={"abbreviation": ministry_name}
                    )
                    if created:
                        ministries_created += 1
                else:
                    ministry = None

                # parse dates into proper types
                start_date_str = row["assignment_start_date"]
                end_date_str = row["assignment_end_date"]
                start_date = parse_date_dmy(start_date_str) if start_date_str else None
                end_date = parse_date_dmy(end_date_str) if end_date_str else None

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
                    if colleague_brand_label:
                        colleague.labels.add(colleague_brand_label)
                    colleagues_created += 1

                _, created = Placement.objects.get_or_create(
                    colleague=colleague,
                    service=service,
                    source="wies",
                )
                if created:
                    placements_created += 1

    except ValueError as e:
        return {"success": False, "errors": [str(e)]}
    except ValidationError as e:
        return {"success": False, "errors": [str(e)]}
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
