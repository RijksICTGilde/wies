from datetime import date, timedelta

from django.db.models import Q
from ..models import Assignment, Colleague, Placement, Service


def get_consultants_working():
    active_colleague_ids = set()
    for colleague in Colleague.objects.all():
        if colleague.end_date:
            active_colleague_ids.add(colleague.id)
    return Colleague.objects.filter(
        id__in=active_colleague_ids
    ).count()


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
    """Get assignments ending within 3 months - optimized database query"""
    
    today = date.today()
    three_months = today + timedelta(days=90)
    
    # Use database filtering instead of Python filtering
    return Assignment.objects.filter(
        Q(end_date__gte=today) & Q(end_date__lte=three_months),
        status__in=['INGEVULD', 'VACATURE']
    ).exclude(
        Q(organization='') | Q(organization__isnull=True)
    ).order_by('end_date')[:limit]


def get_consultants_on_bench(limit=10):
    """Get consultants who are not currently on active assignments"""    
    active_colleague_ids = set()
    for colleague in Colleague.objects.all():
        if colleague.end_date:
            active_colleague_ids.add(colleague.id)

    return Colleague.objects.exclude(
        id__in=active_colleague_ids
    ).exclude(id__isnull=True)[:limit]


def get_new_leads(limit=10):
    """Get new leads (LEAD status assignments)"""
    return Assignment.objects.filter(
        status='LEAD'
    ).exclude(organization='').exclude(organization__isnull=True).order_by('-id')[:limit]


def get_total_services():
    """Get total number of services across all assignments"""
    return Service.objects.filter(
        assignment__status__in=['INGEVULD', 'VACATURE', 'LEAD']
    ).count()


def get_services_filled():
    """Get number of services that have colleagues assigned"""
    return Placement.objects.filter(
        service__assignment__status__in=['INGEVULD', 'VACATURE']
    ).values('service').distinct().count()


def get_average_utilization():
    """Calculate average utilization rate of consultants"""
    total_colleagues = Colleague.objects.count()
    if total_colleagues == 0:
        return 0
    
    working_consultants = get_consultants_working()
    return round((working_consultants / total_colleagues) * 100)


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


def get_available_since(colleague):
    """Calculate how long a colleague has been available (on the bench)"""
    
    if colleague.end_date:
        raise ValueError("Active colleague, not on bench")

    # Find their most recent placement that has ended

    available_since = None
    last_placement = None
    for placement in colleague.placements.all():
        if (placement.service.assignment.status != 'INGEVULD'
            or not placement.start_date
            or not placement.end_date):
            continue  # skip invalid placements

        if placement.service.assignment.phase == 'completed' and (available_since is None or placement.end_date):
            available_since = placement.end_date
            last_placement = placement
    
    if not last_placement:
        # If no historical placement found, return a default period
        return "altijd"
    
    days = (date.today() - last_placement.end_date).days

    if days < 14:
        return f"{days} dagen"
    elif days < 84:  # Less than 12 weeks
        weeks = round(days / 7)
        return f"{weeks} weken"
    else:
        months = round(days / 30)
        return f"{months} maanden"
