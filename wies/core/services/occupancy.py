"""Per-colleague occupancy for the business-manager "Bezetting" page.

Exploratory BM-feature (branch ``explore-bm-views``). Aggregates, per colleague:
their current contract hours, the hours currently filled by active placements,
and the resulting unfilled ("bench") hours — plus a timeline of placements across
the demo horizon (3 months back → 1 year ahead) so a BM sees at a glance who
needs work and whose assignment ends soon.

No permission modelling (demo): every viewer sees every colleague.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Count, Q

from wies.core.models import Colleague, ContractPeriod, Placement, Service
from wies.core.querysets import annotate_placement_dates, annotate_service_dates

# Timeline horizon and "pressing" thresholds.
HORIZON_BACK_DAYS = 90
HORIZON_AHEAD_DAYS = 365
ENDS_SOON_DAYS = 60

BUCKET_BENCH = "bench"
BUCKET_PARTIAL = "partial"
BUCKET_FULL = "full"
BUCKET_UNKNOWN = "unknown"  # has an active placement but no hours recorded
# Sort order (lower = more pressing): bench first, then partials, then fully
# filled, and finally "hours unknown" (assigned, so not a bench-filling priority).
_BUCKET_RANK = {BUCKET_BENCH: 0, BUCKET_PARTIAL: 1, BUCKET_FULL: 2, BUCKET_UNKNOWN: 3}


@dataclass
class TimelineSegment:
    """One placement bar on a colleague's timeline, positioned within the horizon."""

    assignment_name: str
    start: date
    end: date | None
    hours: int
    phase: str  # "active" | "planned" | "completed"
    left_pct: float
    width_pct: float
    lane: int = 0  # vertical lane so overlapping (concurrent) placements don't stack


@dataclass
class OccupancyRow:
    colleague: Colleague
    contract_hours: int
    active_hours: int
    active_count: int
    unfilled_hours: int
    bucket: str  # bench | partial | full | unknown
    ends_soon: bool
    earliest_active_end: date | None
    segments: list[TimelineSegment] = field(default_factory=list)
    lane_count: int = 1  # number of vertical lanes needed (row height scales with this)

    @property
    def filled_pct(self) -> float:
        """Filled share of the contract, for the compact hours bar (0-100)."""
        if not self.contract_hours:
            return 0.0
        return min(100.0, round(self.active_hours / self.contract_hours * 100))


def _current_contract_hours(colleague: Colleague, today: date) -> int:
    """Hours of the contract period covering today (open end = current). 0 if none."""
    period = next(
        (
            p
            for p in colleague.contract_periods.all()  # prefetched, ordered -start_date
            if p.start_date <= today and (p.end_date is None or p.end_date >= today)
        ),
        None,
    )
    return period.hours_per_week if period else 0


def _phase(start: date | None, end: date | None, today: date) -> str:
    if start is not None and start > today:
        return "planned"
    if end is not None and end < today:
        return "completed"
    return "active"


def _position(start: date | None, end: date | None, horizon_start: date, horizon_end: date) -> tuple[float, float]:
    """Clamp a placement to the horizon and return (left%, width%).

    Open-ended placements (no end) run to the horizon end.
    """
    span = (horizon_end - horizon_start).days or 1
    seg_start = max(start or horizon_start, horizon_start)
    seg_end = min(end or horizon_end, horizon_end)
    left = (seg_start - horizon_start).days / span * 100
    width = max((seg_end - seg_start).days, 1) / span * 100
    return round(left, 2), round(width, 2)


def _assign_lanes(segments: list[TimelineSegment], horizon_start: date, horizon_end: date) -> int:
    """Greedily pack segments into vertical lanes so concurrent bars don't overlap.

    Segments are sorted by start; each goes into the first lane whose last bar
    ended before this one starts. Returns the number of lanes used.
    """
    lane_ends: list[date] = []  # effective end date of the last segment in each lane
    for seg in sorted(segments, key=lambda s: s.start or horizon_start):
        seg_start = seg.start or horizon_start
        seg_end = seg.end or horizon_end
        placed = False
        for lane, last_end in enumerate(lane_ends):
            if seg_start > last_end:
                seg.lane = lane
                lane_ends[lane] = seg_end
                placed = True
                break
        if not placed:
            seg.lane = len(lane_ends)
            lane_ends.append(seg_end)
    return max(len(lane_ends), 1)


def colleague_occupancy(today: date) -> list[OccupancyRow]:
    """Build the occupancy rows, sorted most-pressing first.

    Sort key (ascending): (bucket_rank, -unfilled_hours, earliest_active_end).
    Bench first, then partials by descending unfilled hours, then fulls by
    soonest-ending assignment.
    """
    horizon_start = today - timedelta(days=HORIZON_BACK_DAYS)
    horizon_end = today + timedelta(days=HORIZON_AHEAD_DAYS)
    far_future = date.max

    colleagues = Colleague.objects.prefetch_related("contract_periods").order_by("name")

    # All placements overlapping the horizon, in one query. Overlap = starts on or
    # before the horizon end AND (no end, or ends on or after the horizon start).
    horizon_placements = (
        annotate_placement_dates(Placement.objects.all())
        .filter(Q(actual_start_date__isnull=True) | Q(actual_start_date__lte=horizon_end))
        .filter(Q(actual_end_date__isnull=True) | Q(actual_end_date__gte=horizon_start))
        .select_related("colleague", "service__assignment")
    )
    placements_by_colleague: dict[int, list[Placement]] = {}
    for placement in horizon_placements:
        placements_by_colleague.setdefault(placement.colleague_id, []).append(placement)

    rows: list[OccupancyRow] = []
    for colleague in colleagues:
        contract_hours = _current_contract_hours(colleague, today)
        placements = placements_by_colleague.get(colleague.id, [])

        active_hours = 0
        active_count = 0
        active_ends: list[date] = []
        segments: list[TimelineSegment] = []
        for placement in placements:
            start = placement.actual_start_date
            end = placement.actual_end_date
            phase = _phase(start, end, today)
            # Hours live on the service now; ``service__assignment`` is already
            # select_related above, so this is no extra query. A service with
            # several placements reports its full hours per placement (demo).
            hours = placement.service.assignment_hours_per_week or 0
            if phase == "active":
                active_count += 1
                active_hours += hours
                if end is not None:
                    active_ends.append(end)
            left, width = _position(start, end, horizon_start, horizon_end)
            segments.append(
                TimelineSegment(
                    assignment_name=placement.service.assignment.name,
                    start=start,
                    end=end,
                    hours=hours,
                    phase=phase,
                    left_pct=left,
                    width_pct=width,
                )
            )
        segments.sort(key=lambda s: s.start or horizon_start)
        lane_count = _assign_lanes(segments, horizon_start, horizon_end)

        unfilled_hours = max(contract_hours - active_hours, 0)
        # Bench = genuinely no active placement. A colleague WITH an active
        # placement but no hours recorded is "assigned, hours unknown" — not bench.
        if active_count == 0:
            bucket = BUCKET_BENCH
        elif active_hours == 0:
            bucket = BUCKET_UNKNOWN
        elif active_hours < contract_hours:
            bucket = BUCKET_PARTIAL
        else:
            bucket = BUCKET_FULL
        earliest_active_end = min(active_ends) if active_ends else None
        ends_soon = earliest_active_end is not None and earliest_active_end <= today + timedelta(days=ENDS_SOON_DAYS)

        rows.append(
            OccupancyRow(
                colleague=colleague,
                contract_hours=contract_hours,
                active_hours=active_hours,
                active_count=active_count,
                unfilled_hours=unfilled_hours,
                bucket=bucket,
                ends_soon=ends_soon,
                earliest_active_end=earliest_active_end,
                segments=segments,
                lane_count=lane_count,
            )
        )

    rows.sort(key=lambda r: (_BUCKET_RANK[r.bucket], -r.unfilled_hours, r.earliest_active_end or far_future))
    return rows


def _covers(start: date | None, end: date | None, d: date) -> bool:
    """True if the [start, end] interval covers date ``d`` (null = open bound)."""
    return (start is None or start <= d) and (end is None or end >= d)


def capacity_forecast(today: date) -> dict:
    """Weekly capacity vs. demand across the horizon, for the Prognose chart.

    For each week in [today - HORIZON_BACK_DAYS, today + HORIZON_AHEAD_DAYS]:
      - capacity  = Σ contract hours of every ContractPeriod covering that week,
      - planned   = Σ hours of every *filled* Service (≥1 placement) covering it,
      - aanvragen = Σ hours of every *open* Service (no placement) covering it.

    Demand (planned + aanvragen) can exceed capacity: an open aanvraag carries
    hours whether or not a consultant is placed. Two queries total (contract
    periods + annotated services); the per-week aggregation runs in Python.
    Returns JSON-ready lists.
    """
    horizon_start = today - timedelta(days=HORIZON_BACK_DAYS)
    horizon_end = today + timedelta(days=HORIZON_AHEAD_DAYS)

    # Weekly sample points: Mondays from the first Monday on/before the horizon
    # start through the horizon end.
    first_monday = horizon_start - timedelta(days=horizon_start.weekday())
    weeks: list[date] = []
    cursor = first_monday
    while cursor <= horizon_end:
        weeks.append(cursor)
        cursor += timedelta(days=7)

    contract_periods = list(ContractPeriod.objects.all())
    services = list(
        annotate_service_dates(Service.objects.all())
        .annotate(placement_count=Count("placements"))
        .values("actual_start_date", "actual_end_date", "assignment_hours_per_week", "placement_count")
    )

    capacity: list[int] = []
    planned: list[int] = []
    aanvragen: list[int] = []
    for week in weeks:
        cap = sum(cp.hours_per_week for cp in contract_periods if _covers(cp.start_date, cp.end_date, week))
        plan = 0
        aanvraag = 0
        for s in services:
            if not _covers(s["actual_start_date"], s["actual_end_date"], week):
                continue
            hours = s["assignment_hours_per_week"] or 0
            if s["placement_count"] > 0:  # a filled service is "ingepland"
                plan += hours
            else:  # an open service (no placement) is an "aanvraag"
                aanvraag += hours
        capacity.append(cap)
        planned.append(plan)
        aanvragen.append(aanvraag)

    # Index of the week the "today" marker sits in (the last week start <= today).
    today_index = max((i for i, w in enumerate(weeks) if w <= today), default=0)

    return {
        "weeks": [w.isoformat() for w in weeks],
        "capacity": capacity,
        "planned": planned,
        "aanvragen": aanvragen,
        # Free capacity after both planned and requested demand (never negative);
        # overcommit is the excess demand above capacity (0 when there is slack).
        "unfilled": [max(c - p - a, 0) for c, p, a in zip(capacity, planned, aanvragen, strict=True)],
        "overcommit": [max(p + a - c, 0) for c, p, a in zip(capacity, planned, aanvragen, strict=True)],
        "today_index": today_index,
        "today": today.isoformat(),
    }
