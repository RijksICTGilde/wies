"""The base dummy data must produce a usable demo environment on its own.

`just setup` runs a chain of commands, but several environments only get as far
as the base data generator — a PR preview seeded through /staff/, for one. What
that generator alone yields is therefore what those environments show.

These tests measure against today. The generator dates its data relative to
today (`load_dummy_data --profile base`), so — unlike the old fixed-date fixture
— it does not age out; these tests instead pin that the generated spread stays
in the shape a consultancy demo needs.
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from wies.core.models import Assignment, Colleague, LabelCategory, Placement
from wies.core.services.occupancy import GILDE_CATEGORY, colleague_occupancy

User = get_user_model()


class BaseDummyDataFixtureTest(TestCase):
    """What `load_dummy_data --profile base` leaves behind."""

    def setUp(self):
        call_command("load_dummy_data", "--profile", "base", verbosity=0)

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

    def test_the_timeline_shows_both_urgency_bands(self):
        """A demo that only ever renders one colour proves nothing about the other."""
        rows = colleague_occupancy(timezone.now().date())
        levels = {segment.ending_level for row in rows for segment in row.segments}
        assert {"soon", "calm"} <= levels, levels

    def test_some_but_not_most_bench_colleagues_have_work_lined_up(self):
        """A planned bar on a bench row is the reason those rows keep a timeline
        at all, so the demo data has to contain the case — but only a minority.

        An earlier spread booked ahead for two thirds of the bench, which reads
        as a team with nothing left to plan rather than one with people to place.
        """
        bench = [row for row in colleague_occupancy(timezone.now().date()) if row.bucket == "bench"]
        with_plans = [row for row in bench if any(s.phase == "planned" for s in row.segments)]
        assert len(with_plans) >= 2, f"only {len(with_plans)} bench rows with planned work"
        assert len(with_plans) < len(bench) / 2, f"{len(with_plans)} of {len(bench)} bench rows already booked"

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

    def test_loading_twice_regenerates_cleanly(self):
        """/staff/ can reseed onto an environment that already has data. The
        generator clears its own data first and reuses users by email, so a
        second run regenerates rather than colliding or piling up."""
        call_command("load_dummy_data", "--profile", "base", verbosity=0)
        assert Colleague.objects.count() == 50
        assert Colleague.objects.filter(user__isnull=True).count() == 0
