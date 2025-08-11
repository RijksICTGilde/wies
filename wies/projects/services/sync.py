from django.db import transaction
from wies.exact.models import ExactEmployee
from wies.projects.models import Colleague, Brand


def sync_colleagues_from_exact():
    """
    Sync all ExactEmployee records to Colleague records.
    Creates new Colleague records or updates existing ones based on source_id.
    """
    exact_employees = ExactEmployee.objects.all()
    
    with transaction.atomic():
        for exact_employee in exact_employees:
            # Get or create brand based on organisatieonderdeel
            brand, created = Brand.objects.get_or_create(
                name=exact_employee.organisatieonderdeel
            )
            
            # Prepare colleague data
            colleague_data = {
                'name': exact_employee.naam_medewerker,
                'brand': brand,
                'source': 'exact',
                'source_url': f'http://127.0.0.1:8000/exact/employees/{exact_employee.id}/'
            }
            
            # Update or create colleague based on source_id
            colleague, created = Colleague.objects.update_or_create(
                source_id=str(exact_employee.id),
                source='exact',
                defaults=colleague_data
            )
