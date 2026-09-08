"""The business manager's assignments, grouped into columns by their status.

Where the "Bezetting" page answers who is free, this board answers where each
assignment stands: every ``ASSIGNMENT_STATUS`` value is a column, in pipeline
order (Lead → Open → Ingevuld → Gesloten), and one card per assignment moves
between them as the work progresses.

The status is a field a business manager sets by dragging a card, not something
derived from the placements: an assignment can sit in "Lead" long before it has
any services, and stay in "Ingevuld" while a role is briefly vacant.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Prefetch
from django.utils import timezone

from wies.core.models import ASSIGNMENT_STATUS, Assignment, Service
from wies.core.services.occupancy import GILDE_CATEGORY

# An end date inside this window is "wrapping up": the business manager has to
# think about an extension or a hand-off. Six weeks is enough lead time to act.
ENDING_SOON_WEEKS = 6

# Offered by the "eindigt binnen" filter, in months.
ENDING_WITHIN_CHOICES = (1, 2, 3)

# A month is 30 days here. The filter is a coarse "roughly within N months", and
# calendar-exact month arithmetic would not make the answer any more useful.
DAYS_PER_MONTH = 30


@dataclass
class BoardCard:
    """One assignment on the board."""

    public_id: str
    name: str
    org_label: str
    start_date: date | None
    end_date: date | None
    # One service is one seat to fill; the app records no hours, so occupancy is
    # a count of seats rather than an fte sum.
    total_seats: int
    filled_seats: int
    # (name, nldd colour) per gilde on this assignment's team, as on Bezetting.
    gilde_labels: list[tuple[str, str]] = field(default_factory=list)
    # Whose pipeline this sits on. The board spans the team, so a card has to
    # say who owns it.
    owner_name: str = ""
    # Whole weeks until the end date, negative once it has passed, None without
    # one. Only used while ends_soon is set.
    weeks_until_end: int | None = None
    ends_soon: bool = False

    @property
    def open_seats(self) -> int:
        return self.total_seats - self.filled_seats


@dataclass
class BoardColumn:
    """One status column, with the cards that currently sit in it."""

    key: str
    label: str
    cards: list[BoardCard] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.cards)


def build_board(
    *,
    ending_within_months: int | None = None,
    org_ids: list[int] | None = None,
    label_ids: list[int] | None = None,
    owner_ids: list[int] | None = None,
) -> list[BoardColumn]:
    """Return the assignments on the board, in pipeline order.

    Every business manager's work by default: the board is read to see where the
    pipeline stands, and that question spans the team. ``owner_ids`` narrows it
    to one or more of them.

    The filters narrow which cards land on the board:
    - ``ending_within_months`` keeps only assignments ending between today and
      that many months out. Assignments that already ended fall outside it — the
      filter reads as "needs attention soon", and a past date does not.
    - ``org_ids`` keeps only assignments for those client organisations.
    - ``label_ids`` keeps only assignments whose team carries one of those
      labels, which is how the gilde chips on the cards filter.
    - ``owner_ids`` keeps only assignments owned by those business managers.
    """
    columns = {key: BoardColumn(key=key, label=label) for key, label in ASSIGNMENT_STATUS.items()}

    today = timezone.now().date()
    cutoff = today + timedelta(days=DAYS_PER_MONTH * ending_within_months) if ending_within_months else None

    for assignment in _assignments_for(org_ids, label_ids, owner_ids):
        if cutoff is not None and not (assignment.end_date and today <= assignment.end_date <= cutoff):
            continue
        card = _card_for(assignment, today)
        # An unknown status would drop the card off the board entirely; park it
        # in Open instead, where it is visible and can be dragged somewhere else.
        column = columns.get(assignment.status) or columns["OPEN"]
        column.cards.append(card)

    return list(columns.values())


def board_assignments():
    """Everything the board can show: every assignment that has an owner."""
    return Assignment.objects.filter(owner__isnull=False)


def owner_counts() -> Counter:
    """Cards per business manager, for the BM filter."""
    return Counter(board_assignments().values_list("owner_id", flat=True))


def organization_counts() -> Counter:
    """Cards per client organisation, for the Opdrachtgever filter."""
    return Counter(oid for oid in board_assignments().values_list("organizations__id", flat=True) if oid)


def gilde_counts(category_id: int) -> Counter:
    """Cards per gilde label, for the Subgroep filter.

    Per assignment, not per person: two AI colleagues on one assignment are one
    card, so the number beside a filter says how many cards it would leave.
    """
    pairs = (
        board_assignments()
        .filter(services__placements__colleague__labels__category_id=category_id)
        .values_list("id", "services__placements__colleague__labels__id")
        .distinct()
    )
    return Counter(label_id for _, label_id in pairs)


def ending_within_counts(months_choices) -> dict[int, int]:
    """Cards ending within each of ``months_choices``, in one pass."""
    today = timezone.now().date()
    cutoffs = {m: today + timedelta(days=DAYS_PER_MONTH * m) for m in months_choices}
    ends = board_assignments().filter(end_date__gte=today).values_list("end_date", flat=True)
    counts = dict.fromkeys(months_choices, 0)
    for end in ends:
        for months, cutoff in cutoffs.items():
            if end <= cutoff:
                counts[months] += 1
    return counts


def _assignments_for(
    org_ids: list[int] | None = None,
    label_ids: list[int] | None = None,
    owner_ids: list[int] | None = None,
):
    """The board's assignments, prefetched for the card fields.

    Only assignments that have an owner: a card names its business manager, and
    one without is not on anybody's pipeline.
    """
    queryset = board_assignments()
    if owner_ids:
        queryset = queryset.filter(owner_id__in=owner_ids)
    if org_ids:
        queryset = queryset.filter(organizations__id__in=org_ids).distinct()
    if label_ids:
        # Through the people placed on it: an assignment carries no labels itself.
        queryset = queryset.filter(services__placements__colleague__labels__id__in=label_ids).distinct()
    return (
        queryset.select_related("owner")  # the card names its business manager
        .prefetch_related(
            # Services with their placements: the card needs filled-vs-total,
            # which would otherwise be a query per card.
            Prefetch(
                "services",
                queryset=Service.objects.prefetch_related("placements__colleague__labels__category"),
                to_attr="loaded_services",
            ),
            "organizations",
        )
        .order_by("name")
    )


def _card_for(assignment: Assignment, today: date) -> BoardCard:
    org = next(iter(assignment.organizations.all()), None)
    services = assignment.loaded_services
    # A seat counts as filled once anyone is placed on it; the remainder is what
    # the business manager still has to fill.
    filled = sum(1 for service in services if service.placements.all())
    weeks = _weeks_until(assignment.end_date, today)
    return BoardCard(
        gilde_labels=_gilde_labels(services),
        public_id=str(assignment.public_id),
        name=assignment.name,
        org_label=(org.label or org.name) if org else "",
        start_date=assignment.start_date,
        end_date=assignment.end_date,
        owner_name=assignment.owner.name if assignment.owner else "",
        total_seats=len(services),
        filled_seats=filled,
        weeks_until_end=weeks,
        ends_soon=weeks is not None and 0 <= weeks <= ENDING_SOON_WEEKS,
    )


def _gilde_labels(services) -> list[tuple[str, str]]:
    """The gildes on this assignment's team, deduplicated, in a stable order.

    An assignment has no labels of its own; the people placed on it do. A team
    is usually one gilde, but a mixed one names both rather than picking a
    winner.
    """
    seen: dict[str, str] = {}
    for service in services:
        for placement in service.placements.all():
            for label in placement.colleague.labels.all():
                if label.category.name == GILDE_CATEGORY:
                    seen.setdefault(label.name, label.category.nldd_color)
    return sorted(seen.items())


def _weeks_until(end_date: date | None, today: date) -> int | None:
    """Whole weeks until ``end_date``, negative once past, None without a date."""
    if end_date is None:
        return None
    return (end_date - today).days // 7


def move_assignment(assignment: Assignment, status: str) -> bool:
    """Move ``assignment`` to ``status``. False when the status is unknown."""
    if status not in ASSIGNMENT_STATUS:
        return False
    if assignment.status != status:
        assignment.status = status
        assignment.save(update_fields=["status"])
    return True
