from datetime import date, timedelta
from django.db.models import Q

from ..models import Assignment, Colleague, Placement


class StatisticsService:
    """Service class for application statistics and data calculations"""
    
    @staticmethod
    def get_dashboard_statistics():
        """Calculate and return dashboard statistics"""
        # Calculate global statistics
        consultants_working = Placement.objects.filter(
            service__assignment__status='LOPEND',
            colleague__isnull=False
        ).values('colleague').distinct().count()
        
        total_clients_count = Assignment.objects.values('organization').distinct().exclude(
            organization=''
        ).exclude(organization__isnull=True).count()
        
        # Calculate total budget from all services
        total_budget = 0
        for assignment in Assignment.objects.all():
            assignment_budget = assignment.get_total_services_cost()
            if assignment_budget:
                total_budget += assignment_budget
        
        formatted_budget = f"{int(total_budget):,}".replace(',', '.') if total_budget else "0"
        
        return {
            'consultants_working': consultants_working,
            'total_clients_count': total_clients_count,
            'total_budget': total_budget,
            'formatted_budget': formatted_budget,
        }
    
    @staticmethod
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
    
    @staticmethod
    def get_consultants_on_bench(limit=10):
        """Get consultants who are not currently on active assignments"""
        active_colleague_ids = Placement.objects.filter(
            service__assignment__status='LOPEND'
        ).values_list('colleague_id', flat=True).distinct()
        
        return Colleague.objects.exclude(
            id__in=active_colleague_ids
        ).exclude(id__isnull=True)[:limit]
    
    @staticmethod
    def get_new_leads(limit=10):
        """Get new leads (LEAD status assignments)"""
        return Assignment.objects.filter(
            status='LEAD'
        ).exclude(organization='').exclude(organization__isnull=True).order_by('-id')[:limit]
    
    @classmethod
    def get_dashboard_data(cls, active_tab='ending_soon'):
        """Get all dashboard data in one call"""
        statistics = cls.get_dashboard_statistics()
        
        return {
            **statistics,
            'assignments_ending_soon': cls.get_assignments_ending_soon(),
            'consultants_bench': cls.get_consultants_on_bench(),
            'new_leads': cls.get_new_leads(),
            'active_tab': active_tab,
        }
    
    @staticmethod
    def get_assignment_statistics(assignment):
        """Calculate and return statistics for a specific assignment"""
        # Calculate weeks until end
        weeks_remaining = None
        if assignment.end_date:
            today = date.today()
            if assignment.end_date > today:
                delta = assignment.end_date - today
                weeks_remaining = round(delta.days / 7)
            else:
                weeks_remaining = 0
        
        # Calculate total budget/costs for this assignment
        total_budget = assignment.get_total_services_cost() or 0
        formatted_budget = f"{int(total_budget):,}".replace(',', '.') if total_budget else "0"
        
        # Calculate budget percentage (assuming 100% for now, could be based on planned vs actual)
        budget_percentage = 85  # Placeholder percentage
        
        # Calculate project progress (placeholder - you could improve this)
        project_score = 8.5  # This could be calculated based on deadlines, budget, etc.
        
        return {
            'weeks_remaining': weeks_remaining,
            'total_budget': total_budget,
            'formatted_budget': formatted_budget,
            'budget_percentage': budget_percentage,
            'project_score': project_score,
        } 