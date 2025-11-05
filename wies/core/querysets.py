"""
Query optimization utilities for hierarchical date handling.

This module provides efficient database-level annotations for start_date and end_date
that cascade from Assignment -> Service -> Placement hierarchy.
"""

from datetime import date
from django.db.models import Case, When, F, Q, Max


def annotate_placement_dates(queryset):
    """
    Annotate Placement queryset with actual start_date and end_date.

    Handles the full hierarchy where dates can come from:
    - Assignment level (when service.period_source='ASSIGNMENT')
    - Service level (when placement.period_source='SERVICE')
    - Placement level (when placement.period_source='PLACEMENT')

    Returns:
        QuerySet with 'actual_start_date' and 'actual_end_date' annotations
    """
    return queryset.annotate(
        actual_start_date=Case(
            # When placement uses SERVICE dates
            When(
                period_source='SERVICE',
                then=Case(
                    # And service uses ASSIGNMENT dates
                    When(service__period_source='ASSIGNMENT', then=F('service__assignment__start_date')),
                    # Or service has its own dates
                    default=F('service__specific_start_date')
                )
            ),
            # When placement has its own dates
            default=F('specific_start_date')
        ),
        actual_end_date=Case(
            # When placement uses SERVICE dates
            When(
                period_source='SERVICE',
                then=Case(
                    # And service uses ASSIGNMENT dates
                    When(service__period_source='ASSIGNMENT', then=F('service__assignment__end_date')),
                    # Or service has its own dates
                    default=F('service__specific_end_date')
                )
            ),
            # When placement has its own dates
            default=F('specific_end_date')
        )
    )


def filter_by_date_overlap(queryset, start_date, end_date, start_field='actual_start_date', end_field='actual_end_date'):
    """
    Filter queryset for records that overlap with the given date range.

    A record overlaps if: record_start <= range_end AND record_end >= range_start

    Args:
        queryset: QuerySet to filter (must have start/end date annotations)
        start_date: Range start date
        end_date: Range end date
        start_field: Name of the start date field/annotation
        end_field: Name of the end date field/annotation

    Returns:
        Filtered QuerySet
    """
    return queryset.filter(
        Q(**{f'{start_field}__lte': end_date}) &
        Q(**{f'{end_field}__gte': start_date}) &
        Q(**{f'{start_field}__isnull': False}) &
        Q(**{f'{end_field}__isnull': False})
    )
