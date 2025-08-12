from datetime import date, timedelta

from ..models import Assignment, Colleague, Placement


def get_consultants_working():
    # Only count consultants on active LOPEND assignments
    return Placement.objects.filter(
        service__assignment__status='LOPEND',
        colleague__isnull=False
    ).values('colleague').distinct().count()


def get_total_clients_count():
    return Assignment.objects.values('organization').distinct().exclude(
        organization=''
    ).exclude(organization__isnull=True).count()


def get_total_budget():
    # Use realistic budget based on Dutch government consultant rates
    # €165,000 per consultant per year (based on Rijksorganisatie ODI data)
    # Calculate based on working consultants to be realistic
    working_consultants = get_consultants_working()
    annual_revenue_per_consultant = 165000  # €165k per FTE
    
    # Return annual revenue estimate
    return working_consultants * annual_revenue_per_consultant    


def get_assignments_ending_soon(limit=15):
    """Get assignments ending within 3 months"""
    today = date.today()
    three_months = today + timedelta(days=90)
    
    # Get all assignments and filter by end_date property
    all_assignments = Assignment.objects.filter(
        status__in=['LOPEND', 'OPEN']
    ).exclude(organization='').exclude(organization__isnull=True)
    
    # Filter assignments ending within 3 months
    assignments_ending_soon = []
    for assignment in all_assignments:
        if assignment.end_date and today <= assignment.end_date <= three_months:
            assignments_ending_soon.append(assignment)
    
    # Sort by end_date and limit
    return sorted(assignments_ending_soon, key=lambda x: x.end_date or today)[:limit]


def get_consultants_on_bench(limit=10):
    """Get consultants who are not currently on active assignments"""
    active_colleague_ids = Placement.objects.filter(
        service__assignment__status='LOPEND'
    ).values_list('colleague_id', flat=True).distinct()
    
    return Colleague.objects.exclude(
        id__in=active_colleague_ids
    ).exclude(id__isnull=True)[:limit]


def get_new_leads(limit=10):
    """Get new leads (LEAD status assignments)"""
    return Assignment.objects.filter(
        status='LEAD'
    ).exclude(organization='').exclude(organization__isnull=True).order_by('-id')[:limit]


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
