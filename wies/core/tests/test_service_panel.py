"""The aanvraag panel: the read view of one open role on an opdracht.

A team row for a placement opens that colleague's panel; an aanvraag has no
colleague, so ``?aanvraag=`` opens this one instead of leaving the row a dead
end.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.tests.role_helpers import make_bdm_user

User = get_user_model()

HX = {"HX-Request": "true", "HX-Target": "side-panel-content"}


class ServicePanelTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.viewer = User.objects.create_user(email="v@rijksoverheid.nl")
        Colleague.objects.create(user=self.viewer, name="Viewer", email="v@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="Zaaksysteem", source="wies")
        self.skill = Skill.objects.create(name="Dev")
        self.service = Service.objects.create(
            assignment=self.assignment,
            description="Bouwt de koppeling.",
            skill=self.skill,
            hours_per_week=24,
            source="wies",
        )
        self.client.force_login(self.viewer)

    def _panel(self):
        url = reverse("home") + f"?opdracht={self.assignment.public_id}&aanvraag={self.service.public_id}"
        return self.client.get(url, headers=HX).content.decode()

    def test_the_panel_names_the_role_and_its_opdracht(self):
        body = self._panel()

        assert "Aanvraag" in body
        assert "Dev" in body
        # The opdracht is a row of its own, the way back up.
        assert f'href="/?opdracht={self.assignment.public_id}"' in body
        assert "Zaaksysteem" in body
        assert 'icon="chevron-right"' in body

    def test_the_panel_shows_the_hours_and_the_description(self):
        body = self._panel()

        assert "24 uur" in body
        assert "Uren per week" in body
        assert "Bouwt de koppeling." in body

    def test_an_aanvraag_without_hours_leaves_the_row_out(self):
        self.service.hours_per_week = None
        self.service.save()

        body = self._panel()

        assert "Uren per week" not in body

    def test_a_viewer_without_edit_rights_gets_no_edit_action(self):
        body = self._panel()

        assert "Aanvraag wijzigen" not in body

    def test_a_team_editor_can_reach_the_edit_sheet_from_the_panel(self):
        bdm = make_bdm_user(email="bdm@rijksoverheid.nl")
        self.assignment.owner = bdm.colleague
        self.assignment.save()
        self.client.force_login(bdm)

        body = self._panel()

        assert "Aanvraag wijzigen" in body
        assert f"teamlid={self.service.public_id}" in body

    def test_an_unknown_aanvraag_is_a_404_for_the_panel_request(self):
        """As for every other panel object: the HTMX request 404s rather than
        rendering a panel with no data."""
        url = reverse("home") + f"?opdracht={self.assignment.public_id}&aanvraag=00000000-0000-0000-0000-000000000000"

        assert self.client.get(url, headers=HX).status_code == 404

    def test_the_team_row_of_an_aanvraag_links_to_the_panel(self):
        """Without the rights to edit the team the row is one link, like a
        person row is; with them the menu carries "Aanvraag bekijken"."""
        body = self.client.get(reverse("home") + f"?opdracht={self.assignment.public_id}", headers=HX).content.decode()

        assert f"aanvraag={self.service.public_id}" in body

    def test_a_team_editor_reaches_the_aanvraag_from_its_title(self):
        """A row with a menu cannot be the link, so the title is a quiet one --
        as the name is on a person's row. Without it a team editor had no way
        in but the menu."""
        bdm = make_bdm_user(email="bdm2@rijksoverheid.nl")
        self.assignment.owner = bdm.colleague
        self.assignment.save()
        self.client.force_login(bdm)

        body = self.client.get(reverse("home") + f"?opdracht={self.assignment.public_id}", headers=HX).content.decode()

        link = next(t for t in body.split("<a ") if "Aanvraag: Dev" in t)
        assert "wies-quiet-link" in link
        assert f"aanvraag={self.service.public_id}" in link
        # The menu is still its own click target next to it.
        assert "Acties voor" in body


class ServicePanelOnlyVacanciesTest(TestCase):
    """``?aanvraag=`` is the read view of a *vacancy*, so it resolves through
    the viewer's own team rows (#693).

    A filled row belongs to the placed colleague: its hours follow
    ``can_view_role_hours`` and an ended one is hidden altogether. This panel
    applies neither rule, so resolving a filled or hidden row here would hand
    out exactly what the team list withholds -- to anyone holding a service
    public_id, which every shared ``teamlid=`` link carries.
    """

    def setUp(self):
        self.client = Client()
        self.assignment = Assignment.objects.create(name="Zaaksysteem", source="wies")
        self.skill = Skill.objects.create(name="Dev")

        # A plain consultant on the team: no rights beyond seeing the opdracht.
        self.viewer = User.objects.create_user(email="v@rijksoverheid.nl")
        viewer_colleague = Colleague.objects.create(
            user=self.viewer, name="Viewer", email="v@rijksoverheid.nl", source="wies"
        )
        self._place(viewer_colleague, hours=10, start=-5, end=50)

        placed = Colleague.objects.create(name="Anke Jacobs", email="anke@rijksoverheid.nl", source="wies")
        self.filled = self._place(placed, hours=16, start=-5, end=50)

        ended = Colleague.objects.create(name="Eva Eind", email="eva@rijksoverheid.nl", source="wies")
        self.hidden = self._place(ended, hours=24, start=-100, end=-10)

        self.vacancy = Service.objects.create(
            assignment=self.assignment, description="Open taken.", skill=self.skill, hours_per_week=36, source="wies"
        )
        self.client.force_login(self.viewer)

    def _place(self, colleague, *, hours, start, end):
        today = timezone.now().date()
        service = Service.objects.create(
            assignment=self.assignment,
            description=f"Taken van {colleague.name}.",
            skill=self.skill,
            hours_per_week=hours,
            source="wies",
        )
        Placement.objects.create(
            colleague=colleague,
            service=service,
            period_source=Placement.PLACEMENT,
            specific_start_date=today + timedelta(days=start),
            specific_end_date=today + timedelta(days=end),
            source="wies",
        )
        return service

    def _get(self, service):
        url = reverse("home") + f"?opdracht={self.assignment.public_id}&aanvraag={service.public_id}"
        return self.client.get(url, headers=HX)

    def test_a_filled_role_is_not_an_aanvraag(self):
        assert self._get(self.filled).status_code == 404

    def test_a_hidden_placement_is_not_reachable_as_an_aanvraag(self):
        assert self._get(self.hidden).status_code == 404

    def test_the_hours_the_team_row_withholds_do_not_leak(self):
        """The team row hides this colleague's hours from a team mate; the
        panel must not be the way around that."""
        row_body = self.client.get(
            reverse("home") + f"?opdracht={self.assignment.public_id}", headers=HX
        ).content.decode()
        assert "Anke Jacobs" in row_body
        assert "16 uur" not in row_body

        assert "16 uur" not in self._get(self.filled).content.decode()

    def test_a_real_aanvraag_still_opens_with_its_hours(self):
        body = self._get(self.vacancy).content.decode()

        assert "36 uur" in body
        assert "Open taken." in body

    def test_a_full_page_load_renders_without_the_panel(self):
        """No HX-Request: a filled row gives the list page, not a 404 -- the
        same as an unknown id, so nothing distinguishes the two."""
        url = reverse("home") + f"?opdracht={self.assignment.public_id}&aanvraag={self.filled.public_id}"
        response = self.client.get(url)

        assert response.status_code == 200
        assert "Taken van Anke Jacobs." not in response.content.decode()
