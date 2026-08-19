"""Per-colleague occupancy for the business-manager "Bezetting" page.

Aggregates, per colleague, whether they currently have an active placement and a
timeline of their placements across the demo horizon (3 months back → 1 year
ahead) so a business manager sees at a glance who is on the bench and whose
assignment ends soon.

The app records no per-week hours, so occupancy is binary: a colleague is either
"op de bank" (``bench`` — no active placement today) or "volledig ingezet"
(``full`` — at least one active placement today). There is no partial state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Q

from wies.core.models import Colleague, Placement
from wies.core.querysets import annotate_placement_dates

# Timeline horizon and "pressing" threshold.
HORIZON_BACK_DAYS = 61
HORIZON_AHEAD_DAYS = 183
ENDS_SOON_DAYS = 60

# Only colleagues in this role appear on the Bezetting page.
CONSULTANT_GROUP = "Consultant"

BUCKET_BENCH = "bench"  # no active placement today
BUCKET_FULL = "full"  # at least one active placement today


@dataclass
class TimelineSegment:
    """One placement bar on a colleague's timeline, positioned within the horizon."""

    assignment_name: str
    start: date | None
    end: date | None
    phase: str  # "active" | "planned" | "completed"
    left_pct: float
    width_pct: float
    lane: int = 0  # vertical lane so overlapping (concurrent) placements don't stack


@dataclass
class OccupancyRow:
    colleague: Colleague
    bucket: str  # bench | full
    ends_soon: bool
    earliest_active_end: date | None
    segments: list[TimelineSegment] = field(default_factory=list)
    lane_count: int = 1  # number of vertical lanes needed (row height scales with this)


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


def colleague_occupancy(
    today: date,
    *,
    merk_ids: list[int] | None = None,
    labels_by_category: dict[int, list[int]] | None = None,
) -> list[OccupancyRow]:
    """Build the occupancy rows, sorted most-pressing first.

    Sort key (ascending): (bench before full, earliest_active_end). Bench
    colleagues come first, then fully-placed colleagues by soonest-ending
    assignment.

    ``merk_ids`` optionally restricts the rows to colleagues in those
    suborganisations (merken); an empty/None value shows everyone.

    ``labels_by_category`` maps a label-category id to the selected label ids in
    that category. Matching is OR within a category and AND between categories,
    matching the "Wie zit waar?" filter semantics.
    """
    horizon_start = today - timedelta(days=HORIZON_BACK_DAYS)
    horizon_end = today + timedelta(days=HORIZON_AHEAD_DAYS)
    far_future = date.max

    # Only consultants: colleagues whose linked user is in the "Consultant" group.
    # Colleagues without a user (e.g. imported without an account) are excluded.
    colleagues = Colleague.objects.filter(user__groups__name=CONSULTANT_GROUP).order_by("name")
    if merk_ids:
        colleagues = colleagues.filter(suborganization_id__in=merk_ids)
    for label_ids in (labels_by_category or {}).values():
        # AND between categories: chain a filter per category (OR within).
        colleagues = colleagues.filter(labels__id__in=label_ids)
    if labels_by_category:
        colleagues = colleagues.distinct()

    # All placements overlapping the horizon, in one query. Overlap = starts on or
    # before the horizon end AND (no end, or ends on or after the horizon start).
    horizon_placements = (
        annotate_placement_dates(Placement.objects.all())
        .filter(Q(actual_start_date__isnull=True) | Q(actual_start_date__lte=horizon_end))
        .filter(Q(actual_end_date__isnull=True) | Q(actual_end_date__gte=horizon_start))
        .select_related("service__assignment")
    )
    placements_by_colleague: dict[int, list[Placement]] = {}
    for placement in horizon_placements:
        placements_by_colleague.setdefault(placement.colleague_id, []).append(placement)

    rows: list[OccupancyRow] = []
    for colleague in colleagues:
        placements = placements_by_colleague.get(colleague.id, [])

        active_count = 0
        active_ends: list[date] = []
        segments: list[TimelineSegment] = []
        for placement in placements:
            start = placement.actual_start_date
            end = placement.actual_end_date
            phase = _phase(start, end, today)
            if phase == "active":
                active_count += 1
                if end is not None:
                    active_ends.append(end)
            left, width = _position(start, end, horizon_start, horizon_end)
            segments.append(
                TimelineSegment(
                    assignment_name=placement.service.assignment.name,
                    start=start,
                    end=end,
                    phase=phase,
                    left_pct=left,
                    width_pct=width,
                )
            )
        segments.sort(key=lambda s: s.start or horizon_start)
        lane_count = _assign_lanes(segments, horizon_start, horizon_end)

        bucket = BUCKET_BENCH if active_count == 0 else BUCKET_FULL
        earliest_active_end = min(active_ends) if active_ends else None
        ends_soon = earliest_active_end is not None and earliest_active_end <= today + timedelta(days=ENDS_SOON_DAYS)

        rows.append(
            OccupancyRow(
                colleague=colleague,
                bucket=bucket,
                ends_soon=ends_soon,
                earliest_active_end=earliest_active_end,
                segments=segments,
                lane_count=lane_count,
            )
        )

    rows.sort(key=lambda r: (0 if r.bucket == BUCKET_BENCH else 1, r.earliest_active_end or far_future))
    return rows
