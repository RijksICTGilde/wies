"""Per-colleague occupancy for the business-manager "Bezetting" page.

Aggregates, per colleague, whether they currently have an active placement and a
timeline of their placements across the horizon (2 months back → 4 months ahead)
so a business manager sees at a glance who is on the bench and whose assignment
ends soon.

A colleague is "op de bank" (``bench``: no active placement today), "deels
beschikbaar" (``partial``: placed, but the hours of their active roles add up to
less than their contract) or "volledig ingezet" (``full``). Hours are optional:
without contract hours, or with an active role that has none, the row cannot be
split and counts as full, exactly as before hours existed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Q
from django.db.models.functions import Lower

from wies.core.models import Colleague, Label, Placement, Suborganization
from wies.core.querysets import annotate_placement_dates

# Timeline horizon and "pressing" threshold. Four months ahead, not six: the far
# end of a six-month view was empty for almost every row, and the months that do
# carry bars got squeezed into the left third of the track.
HORIZON_BACK_DAYS = 61
HORIZON_AHEAD_DAYS = 122

# Work wrapping up within three months: the bars colour by it and the summary
# card counts by it, so a click on the card selects exactly the colleagues whose
# rows show an orange bar. These were two constants — 60 days for the card, 93
# for the colour — which had the card select 11 colleagues while the page had
# coloured 17. 93 days rather than 90, so "ends on the same day three months
# out" lands inside the band people expect.
ENDING_SOON_DAYS = 93
ENDING_LEVEL_SOON = "soon"
ENDING_LEVEL_CALM = "calm"  # further out, or no end date at all

# Below this share of the horizon a bar cannot hold its own label legibly.
NARROW_BAR_PCT = 8

# Only colleagues in this role appear on the Bezetting page.
CONSULTANT_GROUP = "Consultant"

# The label category whose labels ride along on a row as chips. Its labels name
# the gilde a colleague belongs to ("ICT", "AI"), which is the
# subdivision this page is read by; the other categories stay in the filter sheet
# only. Created by _seed_all_label_categories in demo data, and a
# deliberate post-release action in production.
GILDE_CATEGORY = "Subgroep"

BUCKET_BENCH = "bench"  # no active placement today
BUCKET_PARTIAL = "partial"  # placed, with contract hours left over
BUCKET_FULL = "full"  # placed, and no hours left (or hours unknown)
# Sort order: bench first, then partials, then fully placed.
_BUCKET_RANK = {BUCKET_BENCH: 0, BUCKET_PARTIAL: 1, BUCKET_FULL: 2}

# Status facets exposed by the summary cards (independent OR-toggles). Not DB
# columns: each is a derived property of an OccupancyRow, so filtering on them
# happens in-memory on the built rows, not in the queryset.
STATUS_BENCH = "bench"
STATUS_PARTIAL = "partial"
STATUS_FULL = "full"
STATUS_ENDS_SOON = "ends_soon"
STATUS_VALUES = (STATUS_BENCH, STATUS_PARTIAL, STATUS_FULL, STATUS_ENDS_SOON)


@dataclass
class TimelineSegment:
    """One placement bar on a colleague's timeline, positioned within the horizon."""

    assignment_name: str
    role: str  # Service.skill name, empty when the service has none
    start: date | None
    end: date | None
    phase: str  # "active" | "planned" | "completed"
    left_pct: float
    width_pct: float
    lane: int = 0  # vertical lane so overlapping (concurrent) placements don't stack
    # Too narrow to hold its own name: the label would render as a stray "I..."
    # next to a wider bar. The name still lives in the title attribute.
    too_narrow: bool = False
    # Whether THIS placement is the one wrapping up. The row-level flag says only
    # that something of this colleague's ends soon; on someone with several
    # placements it named neither which, nor that the others run on.
    ends_soon: bool = False
    # Whether this placement ends within ENDING_SOON_DAYS. Only active
    # placements carry a level: a planned or finished bar says nothing about how
    # soon someone frees up.
    ending_level: str = ENDING_LEVEL_CALM
    # Whole days from today until this placement ends, for the bars that are
    # wrapping up. None wherever ending_level is calm, so the template has
    # nothing to render there.
    days_left: int | None = None
    # Hours per week of the role, None when the role has none recorded.
    hours_per_week: int | None = None


@dataclass
class OccupancyRow:
    colleague: Colleague
    bucket: str  # bench | partial | full
    ends_soon: bool
    earliest_active_end: date | None
    segments: list[TimelineSegment] = field(default_factory=list)
    lane_count: int = 1  # number of vertical lanes needed (row height scales with this)
    # The colleague's labels in the gilde category, as (name, nldd colour) pairs.
    # Only that category: the row has room for a chip or two, and the full
    # expertise list would fill it, while the gilde is the subdivision this page
    # is read by.
    gilde_labels: list[tuple[str, str]] = field(default_factory=list)
    # What this colleague does: the role they hold today, or — on the bench — the
    # one from their most recent finished placement, since that is the best
    # available answer to "what does this person do". Empty when unknown.
    role: str = ""
    # Whether `role` comes from a finished placement rather than a current one,
    # so the caller can say so instead of implying it is current.
    role_is_past: bool = False
    # When this colleague's last placement ended, for bench rows. None means no
    # placement on record at all, which reads differently from "free since <date>"
    # and is left to the caller to phrase.
    bench_since: date | None = None
    # Whole days between bench_since and today; None when bench_since is.
    bench_days: int | None = None
    # The free stretch drawn on the track: (left%, width%) from bench_since (or
    # the horizon start, whichever is later) up to today. None when there is no
    # date to draw from.
    bench_bar: tuple[float, float] | None = None
    # Whether the stretch started before the horizon: the bar is clipped at the
    # left edge, so it needs to say it runs on beyond what is shown.
    bench_bar_clipped: bool = False
    # Contract hours per week on today's date; None when no period covers today.
    contract_hours: int | None = None
    # Hours per week of the active roles added up; None when any of them has no
    # hours, since a partial sum would understate how placed someone is.
    active_hours: int | None = None
    # Contract minus active hours, or the whole contract on the bench. None
    # whenever either side is unknown.
    unfilled_hours: int | None = None


def contract_hours_on(periods, day: date) -> int | None:
    """Hours per week of the period covering ``day``, from an already loaded list."""
    for period in periods:
        if period.start_date <= day and (period.end_date is None or day <= period.end_date):
            return period.hours_per_week
    return None


def row_has_status(row: OccupancyRow, status: str) -> bool:
    """Whether an occupancy row matches a status facet from the summary cards."""
    if status == STATUS_BENCH:
        return row.bucket == BUCKET_BENCH
    if status == STATUS_PARTIAL:
        return row.bucket == BUCKET_PARTIAL
    if status == STATUS_FULL:
        return row.bucket == BUCKET_FULL
    if status == STATUS_ENDS_SOON:
        return row.ends_soon
    return False


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


def _ending_level(end: date | None, phase: str, today: date) -> str:
    """Whether an active placement ends soon enough to flag.

    Only active work gets flagged: a planned placement has not started and a
    finished one is already over, so neither says anything about how soon this
    colleague frees up. No end date is calm — open-ended is not urgent.
    """
    if phase != "active" or end is None:
        return ENDING_LEVEL_CALM
    if (end - today).days <= ENDING_SOON_DAYS:
        return ENDING_LEVEL_SOON
    return ENDING_LEVEL_CALM


def _days_left(end: date | None, phase: str, today: date) -> int | None:
    """Whole days until an active placement ends, or None when that says nothing.

    Same rule as ``_ending_level``: only running work counts down, so a planned
    or finished bar has no number, and neither does open-ended work.
    """
    if phase != "active" or end is None:
        return None
    return (end - today).days


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

    Sort key (ascending): (bench, partial, full), then the most hours left,
    then earliest_active_end. Bench colleagues come first, then partially placed
    ones with the most free hours first, then fully-placed colleagues by
    soonest-ending assignment.

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
    # The labels and merk ride along: the row shows them as chips, and without
    # the prefetch that is a query per colleague.
    colleagues = (
        Colleague.objects.filter(user__groups__name=CONSULTANT_GROUP)
        .select_related("suborganization")
        .prefetch_related("labels__category", "contract_periods")
        .order_by("name")
    )
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
        .select_related("service__assignment", "service__skill")
    )
    placements_by_colleague: dict[int, list[Placement]] = {}
    for placement in horizon_placements:
        placements_by_colleague.setdefault(placement.colleague_id, []).append(placement)

    # How long each colleague has been free, which the horizon cannot answer: the
    # placement that ended is usually older than the window the timeline draws.
    # One aggregate over every finished placement, not a per-row query.
    # Walked oldest-first so the last write per colleague is their most recent
    # finished placement: one pass gives both the date and the role, where an
    # aggregate could only give the date. select_related keeps it one query.
    last_end_by_colleague: dict[int, date] = {}
    last_role_by_colleague: dict[int, str] = {}
    finished = (
        annotate_placement_dates(Placement.objects.all())
        .filter(actual_end_date__lt=today)
        .select_related("service__skill")
        .order_by("actual_end_date")
    )
    for placement in finished:
        last_end_by_colleague[placement.colleague_id] = placement.actual_end_date
        last_role_by_colleague[placement.colleague_id] = placement.service.skill.name if placement.service.skill else ""

    # One cutoff for the whole build: the row flag and the per-segment flag must
    # agree on what "soon" means.
    soon_cutoff = today + timedelta(days=ENDING_SOON_DAYS)

    rows: list[OccupancyRow] = []
    for colleague in colleagues:
        placements = placements_by_colleague.get(colleague.id, [])

        active_count = 0
        active_ends: list[date] = []
        active_hours: int | None = 0
        segments: list[TimelineSegment] = []
        for placement in placements:
            start = placement.actual_start_date
            end = placement.actual_end_date
            phase = _phase(start, end, today)
            hours = placement.service.hours_per_week
            if phase == "active":
                active_count += 1
                if end is not None:
                    active_ends.append(end)
                # One role without hours makes the sum unknowable.
                active_hours = None if active_hours is None or hours is None else active_hours + hours
            left, width = _position(start, end, horizon_start, horizon_end)
            segments.append(
                TimelineSegment(
                    assignment_name=placement.service.assignment.name,
                    role=placement.service.skill.name if placement.service.skill else "",
                    start=start,
                    end=end,
                    phase=phase,
                    left_pct=left,
                    width_pct=width,
                    ends_soon=(phase == "active" and end is not None and end <= soon_cutoff),
                    ending_level=_ending_level(end, phase, today),
                    days_left=_days_left(end, phase, today),
                    hours_per_week=hours,
                    # 8% of the horizon is roughly four weeks; below that the
                    # label is all ellipsis and no word.
                    too_narrow=width < NARROW_BAR_PCT,
                )
            )
        segments.sort(key=lambda s: s.start or horizon_start)
        lane_count = _assign_lanes(segments, horizon_start, horizon_end)

        contract_hours = contract_hours_on(colleague.contract_periods.all(), today)
        if active_count == 0:
            bucket = BUCKET_BENCH
            unfilled_hours = contract_hours
        elif contract_hours is not None and active_hours is not None and active_hours < contract_hours:
            bucket = BUCKET_PARTIAL
            unfilled_hours = contract_hours - active_hours
        else:
            bucket = BUCKET_FULL
            unfilled_hours = 0 if contract_hours is not None and active_hours is not None else None
        earliest_active_end = min(active_ends) if active_ends else None
        ends_soon = earliest_active_end is not None and earliest_active_end <= soon_cutoff

        # Only meaningful while someone is free; on a placed colleague the date of
        # their previous placement says nothing about today.
        bench_since = last_end_by_colleague.get(colleague.id) if bucket == BUCKET_BENCH else None
        bench_days = (today - bench_since).days if bench_since else None
        # The stretch as a bar on the same axis as the placements, so how long
        # someone has been free is read off the track rather than as a third
        # column of text. Clipped at the horizon: most people on the bench have
        # been free longer than the axis reaches back, and a bar that simply ran
        # to the left edge would look identical for all of them.
        bench_bar = _position(bench_since, today, horizon_start, horizon_end) if bench_since else None
        bench_bar_clipped = bool(bench_since and bench_since < horizon_start)

        # The role they hold now. Someone on two placements can hold two roles;
        # the first active one names what they do without turning the row into a
        # list. On the bench there is no current role, so their last one stands in
        # — flagged, so the template can say it is past rather than imply it holds.
        active_roles = [seg.role for seg in segments if seg.phase == "active" and seg.role]
        role = active_roles[0] if active_roles else ""
        role_is_past = False
        if not role and bucket == BUCKET_BENCH:
            role = last_role_by_colleague.get(colleague.id, "")
            role_is_past = bool(role)

        rows.append(
            OccupancyRow(
                colleague=colleague,
                gilde_labels=[
                    (label.name, label.category.nldd_color)
                    for label in colleague.labels.all()
                    if label.category.name == GILDE_CATEGORY
                ],
                bucket=bucket,
                ends_soon=ends_soon,
                earliest_active_end=earliest_active_end,
                role=role,
                role_is_past=role_is_past,
                bench_since=bench_since,
                bench_days=bench_days,
                bench_bar=bench_bar,
                bench_bar_clipped=bench_bar_clipped,
                segments=segments,
                lane_count=lane_count,
                contract_hours=contract_hours,
                active_hours=active_hours if active_count else None,
                unfilled_hours=unfilled_hours,
            )
        )

    rows.sort(key=lambda r: (_BUCKET_RANK[r.bucket], -(r.unfilled_hours or 0), r.earliest_active_end or far_future))
    return rows


def occupancy_summary(rows) -> dict:
    """Population counts for the summary cards, over the full (pre-status-filter) rows.

    They stay a stable dashboard regardless of which status cards are toggled, so
    the caller computes them before the status filter narrows the rows.
    """
    return {
        "bench_count": sum(1 for r in rows if r.bucket == BUCKET_BENCH),
        "partial_count": sum(1 for r in rows if r.bucket == BUCKET_PARTIAL),
        "full_count": sum(1 for r in rows if r.bucket == BUCKET_FULL),
        "ends_soon_count": sum(1 for r in rows if r.ends_soon),
    }


def split_bench_and_timeline(rows) -> tuple[list, list]:
    """Split occupancy rows into (bench_rows, timeline_rows).

    Bench colleagues get their own section above the placed ones, longest-free
    first — the order a business manager reads this in. Sorted here rather than in
    the template: Jinja's sort filter cannot order a list where some bench_days are
    None (never placed), and comparing None to an int raises. Those go last —
    "never placed" is not a long wait, it is a different thing.
    """
    bench_rows = sorted(
        (r for r in rows if r.bucket == BUCKET_BENCH),
        key=lambda r: (r.bench_days is None, -(r.bench_days or 0)),
    )
    timeline_rows = [r for r in rows if r.bucket != BUCKET_BENCH]
    return bench_rows, timeline_rows


def today_marker_pct() -> float:
    """Horizontal position of the 'today' marker within the timeline horizon."""
    return round(HORIZON_BACK_DAYS / (HORIZON_BACK_DAYS + HORIZON_AHEAD_DAYS) * 100, 2)


def month_ticks(today: date) -> list[dict]:
    """First-of-month gridline labels across the horizon, as {label, month, left%}."""
    horizon_start = today - timedelta(days=HORIZON_BACK_DAYS)
    horizon_end = today + timedelta(days=HORIZON_AHEAD_DAYS)
    span = (horizon_end - horizon_start).days or 1
    ticks = []
    year, month = horizon_start.year, horizon_start.month
    # Advance to the first month boundary on or after the horizon start.
    if horizon_start.day != 1:
        month += 1
        if month > 12:  # noqa: PLR2004 (12 = months per year)
            month = 1
            year += 1
    cursor = date(year, month, 1)
    while cursor <= horizon_end:
        left = (cursor - horizon_start).days / span * 100
        ticks.append({"label": cursor.strftime("%b"), "month": cursor.month, "left": round(left, 2)})
        month += 1
        if month > 12:  # noqa: PLR2004 (12 = months per year)
            month = 1
            year += 1
        cursor = date(year, month, 1)
    return ticks


def labels_by_category(label_ids: list[int]) -> dict[int, list[int]]:
    """Group label ids by their category id."""
    by_category: dict[int, list[int]] = {}
    for label in Label.objects.filter(id__in=label_ids).values("id", "category_id"):
        by_category.setdefault(label["category_id"], []).append(label["id"])
    return by_category


def consultant_colleagues():
    """Base colleague queryset for the Bezetting page: only consultants, matching
    the occupancy timeline (colleagues whose linked user is in that group)."""
    return Colleague.objects.filter(user__groups__name=CONSULTANT_GROUP)


def apply_colleague_filters(qs, merk, labels_by_cat, *, exclude_filter=None):
    """Apply the merk + label filters to a consultant-colleague queryset.

    ``exclude_filter`` leaves one facet out so a facet's own counts don't collapse
    to its current selection: "merk" for the merk group, or a label ``category_id``
    (int) for that category's group. Labels are OR within a category, AND between.
    """
    for cat_id, cat_label_ids in labels_by_cat.items():
        if exclude_filter != cat_id:
            qs = qs.filter(labels__id__in=cat_label_ids)
    if exclude_filter != "merk" and merk.ids:
        qs = qs.filter(suborganization_id__in=merk.ids)
    return qs.distinct()


def bezetting_filter_groups(merk, labels, labels_by_cat) -> list[dict]:
    """Build the select-multi filter groups for the Bezetting sheet.

    One group per label category (only labels used by a consultant; empty
    categories dropped) plus one merk group. Each option carries a cross-filtered
    count — the number of consultants that would remain if only this value were
    added to the other active filters — like the "Gebruikers" filter sheet.
    """
    base_qs = consultant_colleagues()
    selected_label_ids = set(labels.public_ids)
    selected_merk_ids = set(merk.public_ids)

    groups = []

    # Label categories: one group each, only labels actually used by a consultant.
    used_labels = (
        Label.objects.filter(colleagues__user__groups__name=CONSULTANT_GROUP)
        .distinct()
        .select_related("category")
        .order_by("category__name", Lower("name"))
    )
    labels_by_cat_display: dict[int, list] = {}
    category_names: dict[int, str] = {}
    for label in used_labels:
        labels_by_cat_display.setdefault(label.category_id, []).append(label)
        category_names[label.category_id] = label.category.name

    for cat_id, cat_labels in labels_by_cat_display.items():
        cat_qs = apply_colleague_filters(base_qs, merk, labels_by_cat, exclude_filter=cat_id)
        counts = Counter(lid for lid in cat_qs.values_list("labels__id", flat=True) if lid is not None)
        options = [{"value": "", "label": ""}]
        selected_values = []
        for label in cat_labels:
            value = str(label.public_id)
            option = {"value": value, "label": label.name, "count": counts.get(label.id, 0)}
            if value in selected_label_ids:
                option["selected"] = True
                selected_values.append(value)
            options.append(option)
        groups.append(
            {
                "type": "select-multi",
                "name": "labels",
                "label": category_names[cat_id],
                "options": options,
                "selected_values": selected_values,
            }
        )

    # Merk: only suborganisations that have at least one consultant.
    merk_qs = apply_colleague_filters(base_qs, merk, labels_by_cat, exclude_filter="merk")
    merk_counts = Counter(mid for mid in merk_qs.values_list("suborganization_id", flat=True) if mid is not None)
    merk_options = [{"value": "", "label": ""}]
    merk_selected = []
    used_suborgs = Suborganization.objects.filter(colleagues__user__groups__name=CONSULTANT_GROUP).distinct()
    for suborganization in used_suborgs:
        value = str(suborganization.public_id)
        option = {"value": value, "label": suborganization.name, "count": merk_counts.get(suborganization.id, 0)}
        if value in selected_merk_ids:
            option["selected"] = True
            merk_selected.append(value)
        merk_options.append(option)
    groups.append(
        {
            "type": "select-multi",
            "name": "merk",
            "label": "Merk",
            "options": merk_options,
            "selected_values": merk_selected,
        }
    )

    return groups
