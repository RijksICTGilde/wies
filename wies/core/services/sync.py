import os

from django.db import transaction
from wies.core.models import Colleague, Brand

from .otys import OTYSAPI


def sync_colleagues_from_otys_iir():
    # TODO: removal from OTYS is not handled, they stay in wies. is that desired?

    OTYS_API_KEY = os.environ['OTYS_API_KEY']
    OTYS_URL = os.environ['OTYS_URL']

    with OTYSAPI(OTYS_API_KEY) as otys_api:
        otys_colleagues = otys_api.get_candidate_list()['listOutput']  # TODO: apply filter to not transfer all information

    with transaction.atomic():

        brand=Brand.objects.get(name='I-Interim Rijk')  # TODO: now hardcoded on IIR

        for otys_colleague in otys_colleagues:
        
            uid = otys_colleague['uid']
            firstname = otys_colleague['Person']['firstName']
            lastname = otys_colleague['Person']['lastName']
            email = otys_colleague['Person']['emailPrimary']
            name=f'{firstname} {lastname}'

            # Prepare colleague data
            colleague_data = {
                'name': name,
                'brand': brand,
                'source_url': f'{OTYS_URL}/us/modular.html#/candidates/{uid}',
                'email': email,
            }
        
            # Update or create colleague based on source and source_id
            colleague, created = Colleague.objects.update_or_create(
                source_id=str(uid),
                source='otys_iir',
                defaults=colleague_data
            )
