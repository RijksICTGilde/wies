"""BM-kanban-bord: de opdrachten van een BM in kolommen op hun status.

Elke kolom is een ``Assignment.status`` (Lead → Open → Ingevuld → Gesloten). Eén
kaart per opdracht, met de rollen als tags. Slepen tussen kolommen zet de status
van de opdracht.
"""

from __future__ import annotations

from django.db.models import Prefetch
from django.utils import timezone

from wies.core.models import ASSIGNMENT_STATUS, Assignment, Service

# Kolommen in pijplijn-volgorde; de sleutel is de Assignment.status-waarde.
COLUMNS = [(key, label) for key, label in ASSIGNMENT_STATUS.items()]

# Een einddatum binnen dit venster is "loopt bijna af" — de BM moet dan aan een
# verlenging of afronding denken. Zes weken geeft genoeg voorbereidingstijd.
ENDING_SOON_WEEKS = 6

# PoC-gildes binnen RIG. Er is (nog) geen gilde-veld op Assignment, dus we leiden
# het deterministisch af uit het opdracht-id: even → IT, oneven → Digi. Later te
# vervangen door een echt veld/label.
GILDES = {"it": "IT Gilde", "digi": "Digi Gilde"}


def _gilde_for(assignment_id: int) -> str:
    """Dummy: even id → IT Gilde, oneven → Digi Gilde."""
    return "it" if assignment_id % 2 == 0 else "digi"


def build_bm_board(colleague, *, gilde=None, ending_within_months=None):
    """Return {status: [card, ...]} voor de opdrachten van deze BM.

    ``colleague`` is de Business Manager (``Assignment.owner``). Zonder collega
    zijn alle kolommen leeg. Optionele filters:
    - ``gilde``: "it" of "digi" — alleen opdrachten van dat (dummy-)gilde.
    - ``ending_within_months``: 1/2/3 — alleen opdrachten met een einddatum
      binnen zoveel maanden vanaf vandaag (verlopen datums vallen erbuiten).
    """
    board: dict[str, list[dict]] = {key: [] for key, _ in COLUMNS}
    if colleague is None:
        return board

    from datetime import timedelta  # noqa: PLC0415

    from wies.core.models import AssignmentNote  # noqa: PLC0415 — PoC, avoids import cycle

    assignments = (
        Assignment.objects.filter(owner=colleague)
        .prefetch_related(
            # Placements erbij zodat we per dienst weten of hij bezet is (bezetting
            # + open plekken) zonder N+1.
            Prefetch(
                "services",
                queryset=Service.objects.select_related("skill").prefetch_related("placements"),
                to_attr="loaded_services",
            ),
            Prefetch(
                "notes",
                queryset=AssignmentNote.objects.filter(show_on_board=True),
                to_attr="board_notes",
            ),
            # Opdrachtgever-label op de kaart, net als de aanvragen-kaart.
            "organizations",
        )
        .order_by("name")
    )

    today = timezone.now().date()
    # ~30 dagen per maand is voor een grof "binnen N maanden"-filter prima.
    ending_cutoff = today + timedelta(days=30 * ending_within_months) if ending_within_months else None

    for assignment in assignments:
        if gilde and _gilde_for(assignment.id) != gilde:
            continue
        if ending_cutoff is not None and not (assignment.end_date and today <= assignment.end_date <= ending_cutoff):
            continue
        org = next(iter(assignment.organizations.all()), None)
        total = len(assignment.loaded_services)
        # Een dienst is "bezet" zodra er minstens één plaatsing op staat; de rest
        # zijn open plekken die de BM nog moet vullen.
        filled = sum(1 for s in assignment.loaded_services if s.placements.all())
        card = {
            "id": assignment.id,
            "name": assignment.name,
            "gilde": GILDES[_gilde_for(assignment.id)],
            # Eén dienst = één in te vullen plek ≈ 1 fte (er is geen uren-veld op
            # Service). We tonen bezetting (ingevuld/totaal) i.p.v. losse rollen.
            "fte": total,
            "filled": filled,
            "open_count": total - filled,
            "org_label": (org.label or org.name) if org else "",
            "start_date": assignment.start_date,
            "end_date": assignment.end_date,
            "weeks_until_end": _weeks_until(assignment.end_date, today),
            "notes": [n.text for n in assignment.board_notes],
        }
        # Onbekende/oude status valt terug op Open, zodat de kaart altijd ergens staat.
        board.get(assignment.status, board["OPEN"]).append(card)

    return board


def _weeks_until(end_date, today) -> int | None:
    """Hele weken tot ``end_date`` (afgerond naar beneden), of None zonder datum.

    Negatief als de datum al voorbij is; de kaart toont dat niet als
    'loopt-bijna-af' maar het getal blijft bruikbaar.
    """
    if end_date is None:
        return None
    return (end_date - today).days // 7


def move_assignment_to_status(assignment, status_key: str) -> bool:
    """Zet de status van de opdracht. False bij een onbekende status."""
    if status_key not in ASSIGNMENT_STATUS:
        return False
    if assignment.status != status_key:
        assignment.status = status_key
        assignment.save(update_fields=["status"])
    return True
