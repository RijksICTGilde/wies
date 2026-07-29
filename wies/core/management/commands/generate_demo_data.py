"""Generate a small, *representative* demo dataset for the hours features.

Exploratory BM-feature (branch ``explore-bm-views``). Unlike ``load_full_data``
this command is **offline**: it reuses the organizations, skills and org-types
already in the database (loaded from the base fixture) and only regenerates
colleagues, contract periods, assignments, services and placements — shaped into
recognizable occupancy scenarios so the demo visualizations have something to
show.

Per-colleague scenarios (see ``SCENARIO_WEIGHTS``):
- ``full``  — fully loaded on one active assignment (all contract hours).
- ``split`` — contract hours divided over 2+ concurrent active assignments.
- ``bench`` — no active assignment today (only a past placement, or none).
- ``edge``  — active but hours ≠ contract (under → vrije uren, over → overbelast).

Contract periods: everyone has exactly one *open* (``end_date=None``) current
period; ~28% also have an earlier closed period. An open end date always means
the current contract.

Run against a DB that already has orgs/skills (e.g. after ``loaddata
base_dummy_data``), then dump the result back into the fixture.
"""

import random
from datetime import UTC, datetime, timedelta

from django.core.management.base import BaseCommand

from wies.core.management.commands.load_full_data import (
    CONTRACT_HOURS_WEIGHTS,
    SCENARIO_WEIGHTS,
    SECOND_CONTRACT_PERIOD_PROBABILITY,
    SERVICE_DESCRIPTIONS,
    SOURCE_WEIGHTS,
    classify_orgs_from_db,
    generate_assignment_name,
    generate_name,
    sanitize_email,
    split_hours,
    weighted_choice,
)
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    ContractPeriod,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)

# Size of the demo dataset (~100 colleagues).
NUM_COLLEAGUES = 100
RIJKSOVERHEID_RATIO = 0.90

# Interesting horizon for the demo: ~3 months back to ~1 year ahead. Dates are
# kept inside this window so the visualizations aren't diluted by ancient or
# far-future work.
HORIZON_BACK_DAYS = 90
HORIZON_AHEAD_DAYS = 365


def _active_today_dates(rng, today):
    """Active *today*, within the demo horizon: started ≤3mo ago, ends ≤1yr ahead."""
    start = today - timedelta(days=rng.randint(1, HORIZON_BACK_DAYS))
    end = today + timedelta(days=rng.randint(30, HORIZON_AHEAD_DAYS))
    return start, end


def _planned_dates(rng, today):
    """Starts in the (near) future, inside the horizon → phase 'planned'."""
    start = today + timedelta(days=rng.randint(15, 180))
    end = start + timedelta(days=rng.randint(90, HORIZON_AHEAD_DAYS))
    return start, end


def _completed_dates(rng, today):
    """Recently ended (within the last ~3 months), not years ago → 'completed'."""
    end = today - timedelta(days=rng.randint(5, HORIZON_BACK_DAYS))
    start = end - timedelta(days=rng.randint(90, 365))
    return start, end


# How many assignments to build per phase pool. Generous so every colleague can
# draw distinct active assignments (split needs 2-3 each).
NUM_ACTIVE_ASSIGNMENTS = 130
NUM_PLANNED_ASSIGNMENTS = 15
NUM_COMPLETED_ASSIGNMENTS = 40

MIN_SPLIT_SERVICES = 2  # a "split" colleague needs at least this many active services
TRIPLE_SPLIT_PROBABILITY = 0.25  # otherwise a split is across 2 assignments
BENCH_HAS_PAST_PLACEMENT_PROBABILITY = 0.6  # some bench colleagues show a finished placement
EDGE_UNDER_PROBABILITY = 0.5  # else over-allocated
EDGE_UNDER_HOURS = [4, 8, 12]
EDGE_OVER_HOURS = [4, 8]
MIN_PLACEMENT_HOURS = 4
MAX_PLACEMENT_HOURS = 40


def _weighted_hours(rng):
    return int(weighted_choice(rng, {str(k): v for k, v in CONTRACT_HOURS_WEIGHTS.items()}))


class Command(BaseCommand):
    help = "Generate a representative, offline demo dataset for the hours features (reuses existing orgs/skills)."

    def handle(self, *args, **options):  # noqa: C901 — a linear data-builder, clearer as one function
        rng = random.Random(42)  # noqa: S311 — deterministic dummy data, not security-sensitive
        today = datetime.now(tz=UTC).date()

        orgs = list(OrganizationUnit.objects.values_list("id", flat=True))
        skills = list(Skill.objects.all())
        if not orgs or not skills:
            self.stderr.write("No organizations/skills in the DB. Run `manage.py loaddata base_dummy_data` first.")
            return
        rijks_pks, other_pks = classify_orgs_from_db()

        # ── 0. Clean only the regenerated models (keep orgs/skills/orgtypes) ──
        self.stdout.write("Cleaning colleagues, contract periods, assignments, services, placements...")
        Placement.objects.all().delete()
        Service.objects.all().delete()
        AssignmentOrganizationUnit.objects.all().delete()
        Assignment.objects.all().delete()
        ContractPeriod.objects.all().delete()
        Colleague.objects.all().delete()

        # ── 1. Colleagues ────────────────────────────────────────────────
        used_emails: set[str] = set()
        colleagues = []
        for i in range(1, NUM_COLLEAGUES + 1):
            name = generate_name(rng)
            base = sanitize_email(name)
            email = f"{base}@rijksoverheid.nl"
            if email in used_emails:
                email = f"{base}.{i}@rijksoverheid.nl"
            used_emails.add(email)
            num_skills = rng.randint(1, 3)
            colleague = Colleague.objects.create(
                name=name, email=email, source=weighted_choice(rng, SOURCE_WEIGHTS), source_id=""
            )
            colleague.skills.set(rng.sample(skills, num_skills))
            colleagues.append(colleague)
        self.stdout.write(f"Colleagues: {len(colleagues)}")

        # ── 2. Contract periods (open end = current contract) ─────────────
        contract_periods = []
        current_hours_by_colleague: dict[int, int] = {}
        for colleague in colleagues:
            current_hours = _weighted_hours(rng)
            current_hours_by_colleague[colleague.id] = current_hours
            current_start = today - timedelta(days=rng.randint(30, 1095))
            if rng.random() < SECOND_CONTRACT_PERIOD_PROBABILITY:
                prev_end = current_start - timedelta(days=1)
                prev_start = prev_end - timedelta(days=rng.randint(180, 730))
                prev_hours = _weighted_hours(rng)
                contract_periods.append(
                    ContractPeriod(
                        colleague=colleague, hours_per_week=prev_hours, start_date=prev_start, end_date=prev_end
                    )
                )
            contract_periods.append(
                ContractPeriod(
                    colleague=colleague, hours_per_week=current_hours, start_date=current_start, end_date=None
                )
            )
        ContractPeriod.objects.bulk_create(contract_periods)
        self.stdout.write(f"Contract periods: {len(contract_periods)}")

        # ── 3. Assignments partitioned by phase ───────────────────────────
        def make_assignment(dates):
            start, end = dates
            a = Assignment.objects.create(
                name=generate_assignment_name(rng),
                start_date=start,
                end_date=end,
                extra_info="",
                owner=rng.choice(colleagues),
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )
            if rng.random() < RIJKSOVERHEID_RATIO and rijks_pks:
                org_pk = rng.choice(rijks_pks)
            else:
                org_pk = rng.choice(other_pks or rijks_pks or orgs)
            AssignmentOrganizationUnit.objects.create(assignment=a, organization_id=org_pk, role="PRIMARY")
            return a

        active_assignments = [make_assignment(_active_today_dates(rng, today)) for _ in range(NUM_ACTIVE_ASSIGNMENTS)]
        planned_assignments = [make_assignment(_planned_dates(rng, today)) for _ in range(NUM_PLANNED_ASSIGNMENTS)]
        completed_assignments = [
            make_assignment(_completed_dates(rng, today)) for _ in range(NUM_COMPLETED_ASSIGNMENTS)
        ]
        self.stdout.write(
            f"Assignments: active={len(active_assignments)}, planned={len(planned_assignments)}, "
            f"completed={len(completed_assignments)}"
        )

        # One service per assignment (a placement attaches to a service). Track
        # available active services so split colleagues get *distinct* ones.
        def make_service(assignment):
            skill = rng.choice(skills)
            return Service.objects.create(
                assignment=assignment,
                description=rng.choice(SERVICE_DESCRIPTIONS.get(skill.name, [""])),
                skill=skill,
                period_source="ASSIGNMENT",
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
            )

        active_services = [make_service(a) for a in active_assignments]
        completed_services = [make_service(a) for a in completed_assignments]
        # planned assignments keep an open service (vacancy) — no placement.
        for a in planned_assignments:
            make_service(a)

        rng.shuffle(active_services)
        rng.shuffle(completed_services)
        active_pool = list(active_services)
        completed_pool = list(completed_services)

        def take(pool, n):
            """Pop up to n services from a pool (distinct assignments)."""
            taken = pool[:n]
            del pool[:n]
            return taken

        # ── 4. Placements per colleague scenario ──────────────────────────
        placement_count = 0
        scenario_counts = {"full": 0, "split": 0, "bench": 0, "edge": 0}

        def create_placement(colleague, service, hours):
            nonlocal placement_count
            Placement.objects.create(
                colleague=colleague,
                service=service,
                period_source="SERVICE",
                specific_start_date=None,
                specific_end_date=None,
                source=weighted_choice(rng, SOURCE_WEIGHTS),
                source_id="",
                assignment_hours_per_week=hours,
            )
            placement_count += 1

        for colleague in colleagues:
            scenario = weighted_choice(rng, SCENARIO_WEIGHTS)
            contract = current_hours_by_colleague[colleague.id]

            if scenario == "split" and len(active_pool) >= MIN_SPLIT_SERVICES:
                n = 3 if rng.random() < TRIPLE_SPLIT_PROBABILITY else 2
                services = take(active_pool, min(n, len(active_pool)))
                for svc, hrs in zip(services, split_hours(rng, contract, len(services)), strict=True):
                    create_placement(colleague, svc, hrs)
                scenario_counts["split"] += 1
            elif scenario == "bench":
                # No active work. Some show a finished placement, the rest nothing.
                if rng.random() < BENCH_HAS_PAST_PLACEMENT_PROBABILITY and completed_pool:
                    svc = take(completed_pool, 1)[0]
                    create_placement(colleague, svc, _weighted_hours(rng))
                scenario_counts["bench"] += 1
            elif scenario == "edge" and active_pool:
                svc = take(active_pool, 1)[0]
                if rng.random() < EDGE_UNDER_PROBABILITY:
                    hours = max(MIN_PLACEMENT_HOURS, contract - rng.choice(EDGE_UNDER_HOURS))  # under → vrije uren
                else:
                    hours = min(MAX_PLACEMENT_HOURS, contract + rng.choice(EDGE_OVER_HOURS))  # over → overbelast
                create_placement(colleague, svc, hours)
                scenario_counts["edge"] += 1
            elif active_pool:  # "full" (and fallback when another pool ran dry)
                svc = take(active_pool, 1)[0]
                create_placement(colleague, svc, contract)
                scenario_counts["full"] += 1
            else:
                scenario_counts["bench"] += 1

        self.stdout.write(f"Placements: {placement_count}")
        self.stdout.write(f"Scenarios: {scenario_counts}")
        self.stdout.write(self.style.SUCCESS("Done!"))
