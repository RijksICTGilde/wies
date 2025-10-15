"""
Search tool functions for LLM-powered natural language search.

These functions are called by the LLM service when Claude requests
specific data through tool use.
"""

from django.db.models import Q, Count
from wies.projects.models import Assignment, Colleague, Ministry


def search_assignments(query=None, organization=None, ministry=None, status=None, offset=0):
    """
    Search for assignments by various criteria with pagination support.

    Args:
        query: Text search across name, organization, and extra_info
        organization: Filter by organization name
        ministry: Filter by ministry name or abbreviation
        status: Filter by status (LEAD, VACATURE, INGEVULD, AFGEWEZEN)
        offset: Starting position for pagination (default: 0)

    Returns:
        Dictionary with pagination metadata and results:
        - results: List of assignment dictionaries
        - total_count: Total number of matching assignments
        - returned_count: Number of results in this response
        - offset: Starting position of this page
        - limit: Maximum results per page (50)
    """
    LIMIT = 50
    qs = Assignment.objects.select_related('ministry').prefetch_related('services__skill')

    # Apply filters
    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(organization__icontains=query) |
            Q(extra_info__icontains=query)
        )

    if organization:
        qs = qs.filter(organization__icontains=organization)

    if ministry:
        qs = qs.filter(
            Q(ministry__name__icontains=ministry) |
            Q(ministry__abbreviation__icontains=ministry)
        )

    if status:
        qs = qs.filter(status=status)

    # Get total count before pagination
    total_count = qs.count()

    # Apply pagination
    paginated_qs = qs[offset:offset + LIMIT]

    # Format results
    results = []
    for assignment in paginated_qs:
        skills = [service.skill.name for service in assignment.services.all() if service.skill]
        results.append({
            'id': assignment.pk,
            'url': f'/assignments/{assignment.pk}/',
            'name': assignment.name,
            'organization': assignment.organization,
            'ministry': assignment.ministry.name if assignment.ministry else None,
            'status': assignment.get_status_display(),
            'start_date': assignment.start_date.strftime('%Y-%m-%d') if assignment.start_date else None,
            'end_date': assignment.end_date.strftime('%Y-%m-%d') if assignment.end_date else None,
            'skills': skills,
        })

    return {
        'results': results,
        'total_count': total_count,
        'returned_count': len(results),
        'offset': offset,
        'limit': LIMIT
    }


def search_colleagues(query=None, skill=None, brand=None, offset=0):
    """
    Search for colleagues by various criteria with pagination support.

    Args:
        query: Text search across name and email
        skill: Filter by skill name
        brand: Filter by brand name
        offset: Starting position for pagination (default: 0)

    Returns:
        Dictionary with pagination metadata and results:
        - results: List of colleague dictionaries
        - total_count: Total number of matching colleagues
        - returned_count: Number of results in this response
        - offset: Starting position of this page
        - limit: Maximum results per page (50)
    """
    LIMIT = 50
    qs = Colleague.objects.select_related('brand').prefetch_related('skills', 'expertises')

    # Apply filters
    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(skills__name__icontains=query) |
            Q(expertises__name__icontains=query)
        ).distinct()

    if skill:
        qs = qs.filter(skills__name__icontains=skill)

    if brand:
        qs = qs.filter(brand__name__icontains=brand)

    # Get total count before pagination
    total_count = qs.count()

    # Apply pagination
    paginated_qs = qs[offset:offset + LIMIT]

    # Format results
    results = []
    for colleague in paginated_qs:
        results.append({
            'id': colleague.pk,
            'url': f'/colleagues/{colleague.pk}/',
            'name': colleague.name,
            'email': colleague.email,
            'brand': colleague.brand.name if colleague.brand else None,
            'skills': [skill.name for skill in colleague.skills.all()],
            'expertises': [exp.name for exp in colleague.expertises.all()],
        })

    return {
        'results': results,
        'total_count': total_count,
        'returned_count': len(results),
        'offset': offset,
        'limit': LIMIT
    }


def search_ministries(query=None, offset=0):
    """
    Search for ministries by name or abbreviation with pagination support.

    Args:
        query: Text search across name and abbreviation
        offset: Starting position for pagination (default: 0)

    Returns:
        Dictionary with pagination metadata and results:
        - results: List of ministry dictionaries
        - total_count: Total number of matching ministries
        - returned_count: Number of results in this response
        - offset: Starting position of this page
        - limit: Maximum results per page (50)
    """
    LIMIT = 50
    qs = Ministry.objects.annotate(assignment_count=Count('assignment'))

    # Apply filters
    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(abbreviation__icontains=query)
        )

    # Get total count before pagination
    total_count = qs.count()

    # Apply pagination
    paginated_qs = qs[offset:offset + LIMIT]

    # Format results
    results = []
    for ministry in paginated_qs:
        results.append({
            'id': ministry.pk,
            'url': f'/ministries/{ministry.pk}/',
            'name': ministry.name,
            'abbreviation': ministry.abbreviation,
            'assignment_count': ministry.assignment_count,
        })

    return {
        'results': results,
        'total_count': total_count,
        'returned_count': len(results),
        'offset': offset,
        'limit': LIMIT
    }


def get_assignment_details(assignment_id):
    """
    Get detailed information about a specific assignment.

    Args:
        assignment_id: Primary key of the assignment

    Returns:
        Dictionary with full assignment details including services and placements
    """
    try:
        assignment = Assignment.objects.select_related('ministry').prefetch_related(
            'services__skill',
            'services__placements__colleague'
        ).get(pk=assignment_id)
    except Assignment.DoesNotExist:
        return {'error': 'Assignment not found'}

    # Format services and placements
    services = []
    for service in assignment.services.all():
        placements = []
        for placement in service.placements.all():
            placements.append({
                'colleague_url': f'/colleagues/{placement.colleague.pk}/',
                'colleague_name': placement.colleague.name,
                'start_date': placement.start_date.strftime('%Y-%m-%d') if placement.start_date else None,
                'end_date': placement.end_date.strftime('%Y-%m-%d') if placement.end_date else None,
                'hours_per_week': placement.hours_per_week,
            })

        services.append({
            'url': f'/services/{service.pk}/',
            'description': service.description,
            'skill': service.skill.name if service.skill else None,
            'start_date': service.start_date.strftime('%Y-%m-%d') if service.start_date else None,
            'end_date': service.end_date.strftime('%Y-%m-%d') if service.end_date else None,
            'hours_per_week': service.hours_per_week,
            'placements': placements,
        })

    return {
        'url': f'/assignments/{assignment.pk}/',
        'name': assignment.name,
        'organization': assignment.organization,
        'ministry': assignment.ministry.name if assignment.ministry else None,
        'status': assignment.get_status_display(),
        'start_date': assignment.start_date.strftime('%Y-%m-%d') if assignment.start_date else None,
        'end_date': assignment.end_date.strftime('%Y-%m-%d') if assignment.end_date else None,
        'extra_info': assignment.extra_info,
        'services': services,
    }


def get_colleague_details(colleague_id):
    """
    Get detailed information about a specific colleague.

    Args:
        colleague_id: Primary key of the colleague

    Returns:
        Dictionary with full colleague details including current placements
    """
    try:
        colleague = Colleague.objects.select_related('brand').prefetch_related(
            'skills',
            'expertises',
            'placements__service__assignment'
        ).get(pk=colleague_id)
    except Colleague.DoesNotExist:
        return {'error': 'Colleague not found'}

    # Get current placements (INGEVULD status only)
    placements = []
    for placement in colleague.placements.filter(service__assignment__status='INGEVULD'):
        placements.append({
            'assignment_url': f'/assignments/{placement.service.assignment.pk}/',
            'assignment_name': placement.service.assignment.name,
            'organization': placement.service.assignment.organization,
            'start_date': placement.start_date.strftime('%Y-%m-%d') if placement.start_date else None,
            'end_date': placement.end_date.strftime('%Y-%m-%d') if placement.end_date else None,
            'hours_per_week': placement.hours_per_week,
        })

    return {
        'url': f'/colleagues/{colleague.pk}/',
        'name': colleague.name,
        'email': colleague.email,
        'brand': colleague.brand.name if colleague.brand else None,
        'skills': [skill.name for skill in colleague.skills.all()],
        'expertises': [exp.name for exp in colleague.expertises.all()],
        'current_placements': placements,
    }
