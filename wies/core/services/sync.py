import os
import logging
import time

from django.db import transaction
from wies.core.models import Colleague, Brand, Assignment, Service, Placement

from .otys import OTYSAPI

logger = logging.getLogger(__name__)


def sync_all_otys_iir_records():
    """
    Sync candidates and vacancies from OTYS IIR to WIES.
    - Candidates are synced as Colleagues
    - Vacancies are synced as Assignments + Services

    Vacancy title format: "Assignment Name - Service Description"
    """
    # TODO: removal from OTYS is not handled, they stay in wies. is that desired?

    OTYS_API_KEY = os.environ['OTYS_API_KEY']
    OTYS_URL = os.environ['OTYS_URL']

    with OTYSAPI(OTYS_API_KEY) as otys_api:
        # Get candidates and vacancies
        logger.info("Fetching candidates from OTYS...")
        otys_candidates = otys_api.get_candidate_list()['listOutput']

        logger.info("Fetching vacancies from OTYS...")
        otys_vacancies = otys_api.get_vacancy_list()['listOutput']

        # Fetch procedures for each vacancy (candidate-vacancy matches)
        logger.info("Fetching procedures for vacancies...")
        vacancy_procedures = {}
        for otys_vacancy in otys_vacancies:
            vacancy_uid = otys_vacancy['uid']
            try:
                procedures = otys_api.get_procedures_for_specific_vacancy(vacancy_uid)['listOutput']
                vacancy_procedures[vacancy_uid] = procedures
                time.sleep(0.1)  # not hammer server
                logger.debug(f"Found {len(procedures)} procedures for vacancy {vacancy_uid}")
            except Exception as e:
                logger.warning(f"Failed to fetch procedures for vacancy {vacancy_uid}: {e}")
                vacancy_procedures[vacancy_uid] = []

    with transaction.atomic():
        brand, created = Brand.objects.get_or_create(name='I-Interim Rijk')

        placements_synced = 0

        # Sync candidates (colleagues)
        logger.info(f"Syncing {len(otys_candidates)} candidates...")
        for otys_candidate in otys_candidates:
            uid = otys_candidate['uid']
            firstname = otys_candidate.get('Person', {}).get('firstName', '')
            lastname = otys_candidate.get('Person', {}).get('lastName', '')
            email = otys_candidate.get('Person', {}).get('emailPrimary', '')
            name = f'{firstname} {lastname}'.strip()  #TODO: tussenvoegsel?

            if not name:
                logger.warning(f"Skipping candidate {uid} - missing name")
                continue

            # Prepare colleague data
            colleague_data = {
                'name': name,
                'brand': brand,
                'source_url': f'{OTYS_URL}/us/modular.html#/candidates/{uid}',
                'email': email or '',
            }

            # Update or create colleague based on source and source_id
            colleague, created = Colleague.objects.update_or_create(
                source_id=str(uid),
                source='otys_iir',
                defaults=colleague_data
            )

            action = "Created" if created else "Updated"
            logger.debug(f"{action} colleague: {name} (uid: {uid})")

        # Sync vacancies (assignments + services)
        logger.info(f"Syncing {len(otys_vacancies)} vacancies...")
        for otys_vacancy in otys_vacancies:
            vacancy_uid = otys_vacancy['uid']
            vacancy_title = otys_vacancy.get('title', '')

            # Split title into assignment name and service description
            if ' - ' in vacancy_title:
                assignment_name, service_description = vacancy_title.split(' - ', 1)
            else:
                # If no separator, use entire title as assignment name
                assignment_name = vacancy_title
                service_description = vacancy_title

            # Create or update Assignment
            assignment_data = {
                'name': assignment_name.strip(),
                'status': 'INGEVULD',
                'source_url': f'{OTYS_URL}/us/modular.html#/vacancies/{vacancy_uid}',
            }

            assignment, assignment_created = Assignment.objects.update_or_create(
                source_id=str(vacancy_uid),
                source='otys_iir',
                defaults=assignment_data
            )

            assignment_action = "Created" if assignment_created else "Updated"
            logger.debug(f"{assignment_action} assignment: {assignment_name} (uid: {vacancy_uid})")

            # Create or update Service for this vacancy
            service_data = {
                'assignment': assignment,
                'description': service_description.strip(),
                'period_source': 'ASSIGNMENT',  # Use assignment dates
                'source_url': f'{OTYS_URL}/us/modular.html#/vacancies/{vacancy_uid}',
            }

            service, service_created = Service.objects.update_or_create(
                source_id=str(vacancy_uid),
                source='otys_iir',
                defaults=service_data
            )

            service_action = "Created" if service_created else "Updated"
            logger.debug(f"{service_action} service: {service_description} for assignment {assignment_name}")

            # Create placements from procedures for this vacancy
            procedures = vacancy_procedures.get(vacancy_uid, [])
            logger.debug(f"Processing {len(procedures)} procedures for vacancy {vacancy_uid}")

            for procedure in procedures:
                candidate_uid = procedure.get('candidateUid')
                procedure_uid = procedure.get('uid')

                if not candidate_uid or not procedure_uid:
                    logger.warning(f"Skipping procedure {procedure_uid} - missing candidate or procedure UID")
                    continue

                # Find the colleague by source_id
                try:
                    colleague = Colleague.objects.get(
                        source_id=str(candidate_uid),
                        source='otys_iir'
                    )
                except Colleague.DoesNotExist:
                    logger.warning(f"Colleague with source_id {candidate_uid} not found for procedure {procedure_uid}")
                    continue

                # Check the status to determine if this is an active placement
                procedure_status = procedure.get('ProcedureStatus1', {}).get('status', '')

                # Create or update Placement
                placement_data = {
                    'colleague': colleague,
                    'service': service,
                    'period_source': 'SERVICE',
                    'hours_source': 'SERVICE',
                    'source_url': f'{OTYS_URL}/us/modular.html#/procedures/{procedure_uid}',
                }

                placement, placement_created = Placement.objects.update_or_create(
                    source_id=str(procedure_uid),
                    source='otys_iir',
                    defaults=placement_data
                )

                placement_action = "Created" if placement_created else "Updated"
                logger.debug(f"{placement_action} placement for {colleague.name} on service {service.description} (status: {procedure_status})")
                placements_synced += 1

    logger.info("Sync completed successfully")
    return {
        'candidates_synced': len(otys_candidates),
        'vacancies_synced': len(otys_vacancies),
        'placements_synced': placements_synced,
    }
