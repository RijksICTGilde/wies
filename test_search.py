#!/usr/bin/env python
import os
import sys
import django

# Add the wies project directory to the Python path
sys.path.append('/Users/rubenrouwhof/wies')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django.setup()

from django.db.models import Q, Count
from wies.projects.models import Assignment, Colleague, Ministry, Service, Placement

def test_global_search(search_query):
    """Test the global search functionality"""
    print(f"Testing search for: '{search_query}'")
    print("-" * 50)
    
    # Check database counts
    print(f"Database totals:")
    print(f"  Assignments: {Assignment.objects.count()}")
    print(f"  Colleagues: {Colleague.objects.count()}")
    print(f"  Ministries: {Ministry.objects.count()}")
    print(f"  Services: {Service.objects.count()}")
    print(f"  Placements: {Placement.objects.count()}")
    print()
    
    if not search_query.strip():
        print("No search query provided")
        return
    
    # Search Assignments
    assignments = Assignment.objects.filter(
        Q(name__icontains=search_query) |
        Q(organization__icontains=search_query) |
        Q(extra_info__icontains=search_query)
    ).select_related('ministry')
    print(f"Assignment results: {assignments.count()}")
    for i, assignment in enumerate(assignments[:5]):
        print(f"  {i+1}. {assignment.name} @ {assignment.organization}")
    
    # Search Colleagues
    colleagues = Colleague.objects.filter(
        Q(name__icontains=search_query) |
        Q(email__icontains=search_query) |
        Q(skills__name__icontains=search_query) |
        Q(expertises__name__icontains=search_query)
    ).distinct().select_related('brand').prefetch_related('skills', 'expertises')
    print(f"Colleague results: {colleagues.count()}")
    for i, colleague in enumerate(colleagues[:5]):
        print(f"  {i+1}. {colleague.name}")
    
    # Search Ministries
    ministries = Ministry.objects.filter(
        Q(name__icontains=search_query) |
        Q(abbreviation__icontains=search_query)
    ).annotate(assignment_count=Count('assignment'))
    print(f"Ministry results: {ministries.count()}")
    for i, ministry in enumerate(ministries[:5]):
        print(f"  {i+1}. {ministry.name} ({ministry.abbreviation})")
    
    # Search Services
    services = Service.objects.filter(
        Q(skill__name__icontains=search_query) |
        Q(assignment__name__icontains=search_query) |
        Q(assignment__organization__icontains=search_query)
    ).select_related('skill', 'assignment', 'assignment__ministry')
    print(f"Service results: {services.count()}")
    for i, service in enumerate(services[:5]):
        skill_name = service.skill.name if service.skill else "No skill"
        print(f"  {i+1}. {skill_name} for {service.assignment.name}")
    
    # Search Placements
    placements = Placement.objects.filter(
        Q(colleague__name__icontains=search_query) |
        Q(service__assignment__name__icontains=search_query) |
        Q(service__skill__name__icontains=search_query)
    ).select_related('colleague', 'colleague__brand', 'service', 'service__skill', 'service__assignment__ministry')
    print(f"Placement results: {placements.count()}")
    for i, placement in enumerate(placements[:5]):
        print(f"  {i+1}. {placement.colleague.name} -> {placement.service.assignment.name}")
    
    total_count = assignments.count() + colleagues.count() + ministries.count() + services.count() + placements.count()
    print(f"\nTotal results: {total_count}")

if __name__ == '__main__':
    # Test with a few different search terms
    test_queries = ["AI", "logius", "data", "digitaal", "consultant"]
    
    for query in test_queries:
        test_global_search(query)
        print("\n" + "="*60 + "\n")