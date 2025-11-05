import datetime

from ..querysets import annotate_placement_dates, filter_by_date_overlap


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
