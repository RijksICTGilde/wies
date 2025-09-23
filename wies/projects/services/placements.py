import datetime


def filter_placements_by_period(queryset, period):
    """
    Filter placement queryset by period range for overlapping periods

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

        # We need to filter placements where their period overlaps with the filter period
        # A placement overlaps if: placement_start <= filter_end AND placement_end >= filter_start

        placement_ids = []
        for placement in queryset:
            placement_start = placement.start_date
            placement_end = placement.end_date

            if placement_start and placement_end:
                # Check for overlap
                overlaps = True

                if placement_start > period_to:
                    overlaps = False
                if placement_end < period_from:
                    overlaps = False

                if overlaps:
                    placement_ids.append(placement.id)

        return queryset.filter(id__in=placement_ids)
    except ValueError:
        # Invalid date format, ignore filter
        return queryset