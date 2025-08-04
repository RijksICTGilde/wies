from django import template
from ..models import Assignment, Ministry

register = template.Library()

@register.simple_tag
def get_clients():
    """Get all clients (organizations and ministries) for multiselect"""
    clients = []
    
    # Get unique organizations
    organizations = Assignment.objects.exclude(
        organization__isnull=True
    ).exclude(organization='').values_list('organization', flat=True).distinct()
    
    for org in organizations:
        clients.append({
            'id': org,
            'text': org,
            'type': 'organization'
        })
    
    # Get ministries
    ministries = Ministry.objects.all()
    for ministry in ministries:
        ministry_text = f"{ministry.name} ({ministry.abbreviation})" if ministry.abbreviation else ministry.name
        clients.append({
            'id': ministry_text,
            'text': ministry_text,
            'type': 'ministry'
        })
    
    # Sort alphabetically
    clients.sort(key=lambda x: x['text'])
    return clients