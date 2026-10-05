"""The aanvraag panel: the read view of one open role on an opdracht.

A team row for a placement opens that colleague's panel; an aanvraag has no
colleague, so ``?aanvraag=`` opens this one instead of leaving the row a dead
end.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Service, Skill
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

        assert "24 uur per week" in body
        assert "Bouwt de koppeling." in body

    def test_an_aanvraag_without_hours_leaves_the_row_out(self):
        self.service.hours_per_week = None
        self.service.save()

        body = self._panel()

        assert "uur per week" not in body

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
        person row is; with them the menu carries "Bekijk aanvraag"."""
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
