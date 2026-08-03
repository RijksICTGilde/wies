"""BM-kanban-bord: de opdrachten van een BM in kolommen op hun status.

Elke kolom is een ``Assignment.status`` (Lead → Open → Ingevuld → Gesloten). Eén
kaart per opdracht, met de rollen als tags. Slepen tussen kolommen zet de status
van de opdracht.
"""

from __future__ import annotations

from django.db.models import Prefetch

from wies.core.models import ASSIGNMENT_STATUS, Assignment, Service

# Kolommen in pijplijn-volgorde; de sleutel is de Assignment.status-waarde.
COLUMNS = [(key, label) for key, label in ASSIGNMENT_STATUS.items()]


def build_bm_board(colleague):
    """Return {status: [card, ...]} voor de opdrachten van deze BM.

    ``colleague`` is de Business Manager (``Assignment.owner``). Zonder collega
    zijn alle kolommen leeg.
    """
    board: dict[str, list[dict]] = {key: [] for key, _ in COLUMNS}
    if colleague is None:
        return board

    assignments = (
        Assignment.objects.filter(owner=colleague)
        .prefetch_related(
            Prefetch("services", queryset=Service.objects.select_related("skill"), to_attr="loaded_services")
        )
        .order_by("name")
    )

    for assignment in assignments:
        roles = [s.skill.name for s in assignment.loaded_services if s.skill]
        card = {
            "id": assignment.id,
            "name": assignment.name,
            "roles": roles,
            "start_date": assignment.start_date,
            "end_date": assignment.end_date,
        }
        # Onbekende/oude status valt terug op Open, zodat de kaart altijd ergens staat.
        board.get(assignment.status, board["OPEN"]).append(card)

    return board


def move_assignment_to_status(assignment, status_key: str) -> bool:
    """Zet de status van de opdracht. False bij een onbekende status."""
    if status_key not in ASSIGNMENT_STATUS:
        return False
    if assignment.status != status_key:
        assignment.status = status_key
        assignment.save(update_fields=["status"])
    return True
