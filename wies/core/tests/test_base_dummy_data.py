"""The committed fixture must produce a usable demo environment on its own.

`just setup` runs a chain of commands, but several environments only get as far
as `loaddata` — a PR preview seeded through /staff/, for one. What the fixture
alone yields is therefore what those environments show.
"""

from django.contrib.auth import get_user_model
from django.core import management
from django.test import TestCase

from wies.core.models import Assignment, Colleague, Placement
from wies.core.roles import setup_roles

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

    def test_loading_twice_does_not_fail_on_duplicate_emails(self):
        """A unique index guards email case-insensitively, and /staff/ can load
        the fixture onto an environment that already has it."""
        management.call_command("loaddata", "base_dummy_data.json", verbosity=0)
        assert Colleague.objects.filter(user__isnull=True).count() == 0
