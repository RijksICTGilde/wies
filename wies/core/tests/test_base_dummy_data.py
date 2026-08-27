"""The committed fixture must produce a usable demo environment on its own.

`just setup` runs a chain of commands, but several environments only get as far
as `loaddata` — a PR preview seeded through /staff/, for one. What the fixture
alone yields is therefore what those environments show.

These tests measure against today, and the fixture holds fixed dates, so they
are what will notice when it ages: the dates were last spread around September
2026, and once most assignments have ended these fail rather than the demo
quietly turning into a page of empty rows. Re-spread the dates when they do.
"""

from django.contrib.auth import get_user_model
from django.core import management
from django.test import TestCase
from django.utils import timezone

from wies.core.models import Assignment, Colleague, LabelCategory, Placement
from wies.core.roles import setup_roles
from wies.core.services.occupancy import GILDE_CATEGORY, colleague_occupancy

User = get_user_model()


class BaseDummyDataFixtureTest(TestCase):
    """What a bare `loaddata base_dummy_data` leaves behind."""

    def setUp(self):
        # The fixture references role groups by natural key, so they must exist.
        setup_roles()
        management.call_command("loaddata", "base_dummy_data.json", verbosity=0)

    def test_every_colleague_has_a_user(self):
        """Bezetting lists colleagues by their user's role group, so a colleague
        without a user is invisible there however many placements they have."""
        assert Colleague.objects.count() > 0
        assert Colleague.objects.filter(user__isnull=True).count() == 0

    def test_most_colleagues_are_consultants(self):
        """The Bezetting page shows Consultants only. A handful would render a
        page that looks broken rather than a demo of the timeline."""
        consultants = Colleague.objects.filter(user__groups__name="Consultant").count()
        assert consultants >= 20, f"only {consultants} consultants in the fixture"

    def test_the_other_roles_are_represented(self):
        """Roles drive permissions, so the demo data has to exercise more than one."""
        for role in ("Business Development Manager", "Beheerder"):
            assert Colleague.objects.filter(user__groups__name=role).exists(), f"no {role}"

    def test_consultants_have_placements_to_draw(self):
        """Without placements every timeline row is empty and the page proves nothing."""
        placed = Placement.objects.filter(colleague__user__groups__name="Consultant").count()
        assert placed >= 20, f"only {placed} placements on consultants"
        assert Assignment.objects.count() >= 10

    def test_most_consultants_are_placed(self):
        """The fixture's dates were written once and had aged: by the time this
        test was added, 19 of 32 assignments had ended and 62% of consultants sat
        on the bench — the opposite of what a consultancy looks like, and a demo
        that showed empty rows instead of a timeline."""
        rows = colleague_occupancy(timezone.now().date())
        placed = sum(1 for row in rows if row.bucket != "bench")
        share = placed / len(rows)
        assert 0.5 <= share <= 0.85, f"{placed}/{len(rows)} placed ({share:.0%})"

    def test_the_timeline_shows_every_urgency_band(self):
        """A demo that only ever renders one colour proves nothing about the rest."""
        rows = colleague_occupancy(timezone.now().date())
        levels = {segment.ending_level for row in rows for segment in row.segments}
        assert {"critical", "warning", "attention", "calm"} <= levels, levels

    def test_some_bench_colleagues_have_work_lined_up(self):
        """A planned bar on a bench row is the reason those rows keep a timeline
        at all, so the demo data has to contain the case."""
        rows = colleague_occupancy(timezone.now().date())
        with_plans = [
            row
            for row in rows
            if row.bucket == "bench" and any(s.phase == "planned" for s in row.segments)
        ]
        assert len(with_plans) >= 2, f"only {len(with_plans)} bench rows with planned work"

    def test_every_colleague_carries_a_gilde_label(self):
        """The Bezetting rows chip that category, and the filter sheet offers it."""
        assert LabelCategory.objects.filter(name=GILDE_CATEGORY).exists()
        rows = colleague_occupancy(timezone.now().date())
        assert all(row.gilde_labels for row in rows), "a consultant without a gilde label"

    def test_the_other_label_categories_are_populated_too(self):
        """Expertise and Thema drive the filter sheet; empty ones filter nothing."""
        for name in ("Expertise", "Thema"):
            category = LabelCategory.objects.filter(name=name).first()
            assert category is not None, f"no {name} category"
            assert category.labels.exists(), f"{name} has no labels"

    def test_loading_twice_does_not_fail_on_duplicate_emails(self):
        """A unique index guards email case-insensitively, and /staff/ can load
        the fixture onto an environment that already has it."""
        management.call_command("loaddata", "base_dummy_data.json", verbosity=0)
        assert Colleague.objects.filter(user__isnull=True).count() == 0
