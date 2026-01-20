import logging
import os
import time

from django.db import transaction

from wies.core.models import DEFAULT_LABELS, Assignment, Colleague, Label, LabelCategory, Placement, Service

from .otys import OTYSAPI

logger = logging.getLogger(__name__)


def sync_all_otys_iir_records():
    """
    Sync candidates and vacancies from OTYS IIR to WIES.
    - Candidates are synced as Colleagues
    - Vacancies are synced as Assignments + Services

    Vacancy title format: "Assignment Name - Service Description"
    """

    otys_api_key = os.environ["OTYS_API_KEY"]
    otys_url = os.environ["OTYS_URL"]

    with OTYSAPI(otys_api_key) as otys_api:
        # Get candidates and vacancies
        logger.info("Fetching candidates from OTYS...")
        otys_candidates = otys_api.get_candidate_list()["listOutput"]

        logger.info("Fetching vacancies from OTYS...")
        otys_vacancies = otys_api.get_vacancy_list()["listOutput"]

        # Fetch procedures for each vacancy (candidate-vacancy matches)
        logger.info("Fetching procedures for vacancies...")
        vacancy_procedures = {}
        for otys_vacancy in otys_vacancies:
            vacancy_uid = otys_vacancy["uid"]
            try:
                procedures = otys_api.get_procedures_for_specific_vacancy(vacancy_uid)["listOutput"]
                vacancy_procedures[vacancy_uid] = procedures
                time.sleep(0.1)  # not hammer server
                logger.debug("Found %d procedures for vacancy %s", len(procedures), vacancy_uid)
            except (OSError, ValueError):
                logger.warning("Failed to fetch procedures for vacancy %s", vacancy_uid, exc_info=True)
                vacancy_procedures[vacancy_uid] = []

    with transaction.atomic():
        # Get or create the 'I-Interim Rijk' label for OTYS-synced colleagues
        merken_category, _ = LabelCategory.objects.get_or_create(
            name="Merk", defaults={"color": DEFAULT_LABELS["Merk"]["color"]}
        )
        i_interim_rijk_label, _ = Label.objects.get_or_create(name="I-Interim Rijk", category=merken_category)

        placements_synced = 0

        # Sync candidates (colleagues)
        logger.info("Syncing %d candidates...", len(otys_candidates))
        for otys_candidate in otys_candidates:
            uid = otys_candidate["uid"]
            firstname = otys_candidate.get("Person", {}).get("firstName", "")
            lastname = otys_candidate.get("Person", {}).get("lastName", "")
            infix = otys_candidate.get("Person", {}).get("infix", "")
            email = otys_candidate.get("Person", {}).get("emailPrimary", "")

            name = f"{firstname}"  # wrong whitespace if done like f'{firstname} {infix} {lastname}
            if infix:
                name = name + f" {infix}"
            if lastname:
                name = name + f" {lastname}"

            if not name:
                logger.warning("Skipping candidate %s - missing name", uid)
                continue

            # Prepare colleague data
            colleague_data = {
                "name": name,
                "source_url": f"{otys_url}/us/modular.html#/candidates/{uid}",
                "email": email or "",
            }

            # Update or create colleague based on source and source_id
            colleague, created = Colleague.objects.update_or_create(
                source_id=str(uid), source="otys_iir", defaults=colleague_data
            )

            # Assign 'I-Interim Rijk' label to all OTYS-synced colleagues
            if not colleague.labels.filter(id=i_interim_rijk_label.id).exists():
                colleague.labels.add(i_interim_rijk_label)

            action = "Created" if created else "Updated"
            logger.debug("%s colleague: %s (uid: %s)", action, name, uid)

        # Sync vacancies (assignments + services)
        logger.info("Syncing %d vacancies...", len(otys_vacancies))
        for otys_vacancy in otys_vacancies:
            vacancy_uid = otys_vacancy["uid"]
            vacancy_title = otys_vacancy.get("title", "")

            # Split title into assignment name and service description
            if " - " in vacancy_title:
                assignment_name, service_description = vacancy_title.split(" - ", 1)
            else:
                # If no separator, use entire title as assignment name
                assignment_name = vacancy_title
                service_description = vacancy_title

            # Create or update Assignment
            assignment_data = {
                "name": assignment_name.strip(),
                "status": "INGEVULD",
                "source_url": f"{otys_url}/us/modular.html#/vacancies/{vacancy_uid}",
            }

            assignment, assignment_created = Assignment.objects.update_or_create(
                source_id=str(vacancy_uid), source="otys_iir", defaults=assignment_data
            )

            assignment_action = "Created" if assignment_created else "Updated"
            logger.debug("%s assignment: %s (uid: %s)", assignment_action, assignment_name, vacancy_uid)

            # Create or update Service for this vacancy
            service_data = {
                "assignment": assignment,
                "description": service_description.strip(),
                "period_source": "ASSIGNMENT",  # Use assignment dates
                "source_url": f"{otys_url}/us/modular.html#/vacancies/{vacancy_uid}",
            }

            service, service_created = Service.objects.update_or_create(
                source_id=str(vacancy_uid), source="otys_iir", defaults=service_data
            )

            service_action = "Created" if service_created else "Updated"
            logger.debug("%s service: %s for assignment %s", service_action, service_description, assignment_name)

            # Create placements from procedures for this vacancy
            procedures = vacancy_procedures.get(vacancy_uid, [])
            logger.debug("Processing %d procedures for vacancy %s", len(procedures), vacancy_uid)

            for procedure in procedures:
                candidate_uid = procedure.get("candidateUid")
                procedure_uid = procedure.get("uid")

                if not candidate_uid or not procedure_uid:
                    logger.warning("Skipping procedure %s - missing candidate or procedure UID", procedure_uid)
                    continue

                # Find the colleague by source_id
                try:
                    colleague = Colleague.objects.get(source_id=str(candidate_uid), source="otys_iir")
                except Colleague.DoesNotExist:
                    logger.warning(
                        "Colleague with source_id %s not found for procedure %s", candidate_uid, procedure_uid
                    )
                    continue

                # Check the status to determine if this is an active placement
                procedure_status = procedure.get("ProcedureStatus1", {}).get("status", "")

                # Create or update Placement
                placement_data = {
                    "colleague": colleague,
                    "service": service,
                    "period_source": "SERVICE",
                    "hours_source": "SERVICE",
                    "source_url": f"{otys_url}/us/modular.html#/procedures/{procedure_uid}",
                }

                _placement, placement_created = Placement.objects.update_or_create(
                    source_id=str(procedure_uid), source="otys_iir", defaults=placement_data
                )

                placement_action = "Created" if placement_created else "Updated"
                logger.debug(
                    "%s placement for %s on service %s (status: %s)",
                    placement_action,
                    colleague.name,
                    service.description,
                    procedure_status,
                )
                placements_synced += 1

    logger.info("Sync completed successfully")
    return {
        "candidates_synced": len(otys_candidates),
        "vacancies_synced": len(otys_vacancies),
        "placements_synced": placements_synced,
    }
