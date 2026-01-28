"""
Query optimization utilities for hierarchical date handling.

This module provides efficient database-level annotations for start_date and end_date
that cascade from Assignment -> Service -> Placement hierarchy.
"""

from django.db.models import Case, Count, F, Prefetch, When
from django.db.models.functions import Lower

from wies.core.models import Label


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
                period_source="SERVICE",
                then=Case(
                    # And service uses ASSIGNMENT dates
                    When(service__period_source="ASSIGNMENT", then=F("service__assignment__start_date")),
                    # Or service has its own dates
                    default=F("service__specific_start_date"),
                ),
            ),
            # When placement has its own dates
            default=F("specific_start_date"),
        ),
        actual_end_date=Case(
            # When placement uses SERVICE dates
            When(
                period_source="SERVICE",
                then=Case(
                    # And service uses ASSIGNMENT dates
                    When(service__period_source="ASSIGNMENT", then=F("service__assignment__end_date")),
                    # Or service has its own dates
                    default=F("service__specific_end_date"),
                ),
            ),
            # When placement has its own dates
            default=F("specific_end_date"),
        ),
    )


def annotate_usage_counts(queryset):
    """
    Annotate LabelCategory queryset with usage counts on labels
    """

    labels_with_usage = Label.objects.order_by(Lower("name")).annotate(
        usage_count=Count("users", distinct=True) + Count("colleagues", distinct=True)
    )

    return queryset.prefetch_related(Prefetch("labels", queryset=labels_with_usage))
