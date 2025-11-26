import datetime
import csv
from io import StringIO

from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from wies.core.querysets import annotate_placement_dates, filter_by_date_overlap
from wies.core.models import Assignment, Colleague, Service, Placement, Ministry, Skill, Brand


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
    if '_' not in period:
        return queryset

    try:
        period_from_str, period_to_str = period.split('_', 1)
        period_from = datetime.datetime.strptime(period_from_str, '%Y-%m-%d').date()
        period_to = datetime.datetime.strptime(period_to_str, '%Y-%m-%d').date()

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
        'assignment_name',
        'assignment_description',
        'assignment_owner',
        'assignment_owner_email',
        'assignment_organization',
        'assignment_ministry',
        'assignment_start_date',
        'assignment_end_date',
        'service_skill',
        'placement_colleague_name',
        'placement_colleague_email',
    }

    if not csv_reader.fieldnames:
        return {
            'success': False,
            'errors': ['CSV file is leeg of heeft geen headers.']
        }
    
    missing_columns = required_columns - set(csv_reader.fieldnames)
    if missing_columns:
        return {
            'success': False,
            'errors': [f'CSV mist kolommen: {", ".join(missing_columns)}.']
        }

    try:
        with transaction.atomic():
            # Get or create the 'Rijks ICT Gilde' brand for newly created colleagues
            rijks_ict_gilde_brand, _ = Brand.objects.get_or_create(name='Rijks ICT Gilde')

            colleagues_created = 0
            assignments_created = 0
            services_created = 0
            placements_created = 0
            skills_created = 0
            for _, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)

                assignment_owner_email = row['assignment_owner_email']
                if assignment_owner_email != "":
                    validate_email(assignment_owner_email)
                    if Colleague.objects.filter(email=assignment_owner_email).exists():
                        owner = Colleague.objects.get(email=assignment_owner_email)
                    else:
                        owner = Colleague.objects.create(
                            name=row['assignment_owner'],
                            email=assignment_owner_email,
                            source='wies',
                            brand=rijks_ict_gilde_brand,
                        )
                        colleagues_created += 1
                else:
                    owner = None

                ministry_name = row['assignment_ministry']
                if ministry_name != '':
                    ministry = Ministry.objects.get(abbreviation=ministry_name)
                else:
                    ministry = None

                # parse dates into proper types
                start_date = row['assignment_start_date']
                end_date = row['assignment_end_date']
                if start_date: 
                    start_date = datetime.datetime.strptime(start_date, '%d-%m-%Y').date()
                else:
                    start_date = None
                if end_date:
                    end_date = datetime.datetime.strptime(end_date, '%d-%m-%Y').date()
                else:
                    end_date = None

                # owner update or create
                assignment, created = Assignment.objects.get_or_create(
                    source='wies',
                    name = row['assignment_name'],
                    defaults={
                        'start_date': start_date,
                        'end_date': end_date,
                        'extra_info': row['assignment_description'],
                        'owner': owner,
                        'organization': row['assignment_organization'],
                        'ministry': ministry,
                        'status': 'INGEVULD',
                    }
                )

                if created:
                    assignments_created += 1

                skill = row['service_skill']
                if skill != '':
                    skill, created = Skill.objects.update_or_create(
                        name=skill,
                    )

                    if created:
                        skills_created += 1
                else:
                    skill = None

                service = Service.objects.create(
                    assignment=assignment,
                    skill=skill,
                    source='wies',
                )
                services_created += 1


                colleague_email = row['placement_colleague_email']
                validate_email(colleague_email)
                if Colleague.objects.filter(email=colleague_email).exists():
                    colleague = Colleague.objects.get(email=colleague_email)
                else:
                    colleague = Colleague.objects.create(
                        name=row['placement_colleague_name'],
                        email=colleague_email,
                        source='wies',
                        brand=rijks_ict_gilde_brand,
                    )
                    colleagues_created += 1
                
                Placement.objects.create(
                    colleague=colleague,
                    service=service,
                    source='wies',
                )
                placements_created += 1

        return {
            'success': True,
            'colleagues_created': colleagues_created,
            'assignments_created': assignments_created,
            'services_created': services_created,
            'skills_created': skills_created,
            'placements_created': placements_created,
            'errors': [],
        }

    except Ministry.DoesNotExist:
        return {
            'success': False,
            'errors': ['Onbekend ministerie']
        }
    except ValueError as e:
        return {
            'success': False,
            'errors': [str(e)]
        }
    except ValidationError as e:
        return {
            'success': False,
            'errors': [str(e)]
        }
    except Exception as e:
        return {
            'success': False,
            'errors': ['Er is iets onverwachts misgegaan']
        }

