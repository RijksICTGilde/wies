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


def annotate_colleague_max_end_date(queryset):
    """
    Annotate Colleague queryset with max end_date of current placements.

    This calculates the maximum end_date across all placements that are currently active
    (start_date <= today AND end_date >= today), handling the full hierarchy where dates
    can come from Assignment -> Service -> Placement levels.

    Returns:
        QuerySet with 'max_current_end_date' annotation (nullable)

    Note:
        Colleagues without current placements will have NULL max_current_end_date.
        Use F('max_current_end_date').asc(nulls_first=True) for sorting.
    """
    today = date.today()

    # Calculate actual_start_date inline (same logic as annotate_placement_dates)
    actual_start_date_expr = Case(
        When(
            placements__period_source='SERVICE',
            then=Case(
                When(placements__service__period_source='ASSIGNMENT',
                     then=F('placements__service__assignment__start_date')),
                default=F('placements__service__specific_start_date')
            )
        ),
        default=F('placements__specific_start_date')
    )

    # Calculate actual_end_date inline (same logic as annotate_placement_dates)
    actual_end_date_expr = Case(
        When(
            placements__period_source='SERVICE',
            then=Case(
                When(placements__service__period_source='ASSIGNMENT',
                     then=F('placements__service__assignment__end_date')),
                default=F('placements__service__specific_end_date')
            )
        ),
        default=F('placements__specific_end_date')
    )

    # Build filter conditions for currently active placements
    # A placement is current if: start_date <= today AND end_date >= today
    # We need to check all three possible date sources

    current_placement_filter = (
        # Placement has its own dates and they're current
        (
            Q(placements__period_source='PLACEMENT') &
            Q(placements__specific_start_date__lte=today) &
            Q(placements__specific_end_date__gte=today) &
            Q(placements__specific_start_date__isnull=False) &
            Q(placements__specific_end_date__isnull=False)
        ) |
        # Or placement uses service dates
        (
            Q(placements__period_source='SERVICE') &
            (
                # Service has its own dates
                (
                    Q(placements__service__period_source='SERVICE') &
                    Q(placements__service__specific_start_date__lte=today) &
                    Q(placements__service__specific_end_date__gte=today) &
                    Q(placements__service__specific_start_date__isnull=False) &
                    Q(placements__service__specific_end_date__isnull=False)
                ) |
                # Or service uses assignment dates
                (
                    Q(placements__service__period_source='ASSIGNMENT') &
                    Q(placements__service__assignment__start_date__lte=today) &
                    Q(placements__service__assignment__end_date__gte=today) &
                    Q(placements__service__assignment__start_date__isnull=False) &
                    Q(placements__service__assignment__end_date__isnull=False)
                )
            )
        )
    )

    # Annotate with max end_date, filtering for current placements only
    return queryset.annotate(
        max_current_end_date=Max(
            actual_end_date_expr,
            filter=current_placement_filter
        )
    )
