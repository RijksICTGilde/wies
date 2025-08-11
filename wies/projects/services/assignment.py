from datetime import date

from ..models import Assignment


class AssignmentService:
    """Service class for assignment-specific calculations and data"""
    
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
    
    @staticmethod
    def get_assignment_context_data(assignment):
        """Get all context data for an assignment detail view"""
        statistics = AssignmentService.get_assignment_statistics(assignment)
        
        return {
            **statistics,
            'assignment': assignment,
        } 