from datetime import date

from ..models import Assignment, Colleague, Placement
from ..querysets import annotate_placement_dates


def get_consultants_working():
    """
    Get count of consultants with active placements.

    Optimized to use database-level queries instead of iterating through all colleagues.
    """
    today = date.today()

    # Get colleagues who have at least one current placement
    # Using subquery with annotated dates for efficiency
    active_placements = annotate_placement_dates(
        Placement.objects.select_related('service__assignment')
    ).filter(
        actual_start_date__isnull=False,
        actual_end_date__isnull=False,
        actual_start_date__lte=today,
        actual_end_date__gte=today
    )

    return Colleague.objects.filter(
        placements__in=active_placements
    ).distinct().count()


def get_total_clients_count():
    return Assignment.objects.values('organization').distinct().exclude(
        organization=''
    ).exclude(organization__isnull=True).count()


def get_weeks_remaining(assignment):
    # Calculate weeks until end
    weeks_remaining = None
    if assignment.end_date:
        today = date.today()
        if assignment.end_date > today:
            delta = assignment.end_date - today
            weeks_remaining = round(delta.days / 7)
        else:
            weeks_remaining = 0
    return weeks_remaining
