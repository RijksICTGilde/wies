"""The opdracht panel marks one colleague's rows via ``?collega=`` (the hook
side_panel.js scrolls to) and the side panel every list page opens is one
sheet at one width."""

import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.tests.role_helpers import make_bdm_user

User = get_user_model()

HX = {"HX-Request": "true", "HX-Target": "side-panel-content"}
HIGHLIGHT = "wies-team-row--highlighted"


def _row_of(body: str, name: str) -> str:
    """The list item that names ``name``, from its opening tag."""
    items = re.findall(r"<nldd-list-item[^>]*>.*?</nldd-list-item>", body, re.DOTALL)
    return next(item for item in items if name in item)


class AssignmentPanelHighlightTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.viewer = User.objects.create_user(email="v@rijksoverheid.nl")
        Colleague.objects.create(user=self.viewer, name="Viewer", email="v@rijksoverheid.nl", source="wies")
        self.anke_user = User.objects.create_user(email="anke@rijksoverheid.nl")
        self.anke = Colleague.objects.create(
            user=self.anke_user, name="Anke Jacobs", email="anke@rijksoverheid.nl", source="wies"
        )
        self.bram = Colleague.objects.create(name="Bram Smit", email="bram@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="Zaaksysteem", source="wies")
        self.skill = Skill.objects.create(name="Dev")
        self._place(self.anke, start=-10, end=100)
        self._place(self.bram, start=-10, end=100)
        self.client.force_login(self.viewer)

    def _place(self, colleague, *, start, end):
        today = timezone.now().date()
        service = Service.objects.create(assignment=self.assignment, description="", skill=self.skill, source="wies")
        return Placement.objects.create(
            colleague=colleague,
            service=service,
            period_source=Placement.PLACEMENT,
            specific_start_date=today + timedelta(days=start),
            specific_end_date=today + timedelta(days=end),
            source="wies",
        )

    def _panel(self, **params):
        query = "&".join(f"{k}={v}" for k, v in {"opdracht": self.assignment.public_id, **params}.items())
        return self.client.get(reverse("home") + "?" + query, headers=HX).content.decode()

    def test_the_colleagues_rows_are_marked_and_the_others_not(self):
        body = self._panel(collega=self.anke.public_id)

        assert HIGHLIGHT in _row_of(body, "Anke Jacobs")
        assert HIGHLIGHT not in _row_of(body, "Bram Smit")

    def test_two_rows_of_the_same_colleague_are_both_marked(self):
        self._place(self.anke, start=-5, end=50)

        body = self._panel(collega=self.anke.public_id)

        assert body.count(HIGHLIGHT) == 2

    def test_unknown_or_unplaced_colleague_marks_nothing(self):
        assert HIGHLIGHT not in self._panel(collega="not-a-uuid")
        outsider = Colleague.objects.create(name="Niet Geplaatst", email="n@rijksoverheid.nl", source="wies")
        assert HIGHLIGHT not in self._panel(collega=outsider.public_id)

    def test_a_hidden_row_is_not_marked_for_an_outsider_but_is_for_a_bdm(self):
        ended = Colleague.objects.create(name="Eva Eind", email="eva@rijksoverheid.nl", source="wies")
        self._place(ended, start=-100, end=-10)

        body = self._panel(collega=ended.public_id)
        assert "Eva Eind" not in body
        assert HIGHLIGHT not in body

        self.client.force_login(make_bdm_user(email="bdm@rijksoverheid.nl", name="Bdm"))
        body = self._panel(collega=ended.public_id)
        assert HIGHLIGHT in _row_of(body, "Eva Eind")

    def test_a_viewer_without_actions_gets_the_row_as_a_link_without_description(self):
        Service.objects.filter(placements__colleague=self.anke).update(description="Begeleidt de overgang.")

        row = _row_of(self._panel(), "Anke Jacobs")

        assert f'href="?collega={self.anke.public_id}&amp;uitgeklapt={self.assignment.public_id}"' in row.split(">")[0]
        assert 'icon="chevron-right"' in row
        assert "<nldd-link" not in row
        assert "Acties voor" not in row
        assert f"collega={self.anke.id}" not in row
        assert "Begeleidt de overgang." not in row

    def test_the_opdracht_card_holds_the_placement_and_opens_for_uitgeklapt(self):
        Service.objects.filter(placements__colleague=self.anke).update(
            description="Begeleidt de overgang.\n\nEn stemt af met de directie.", hours_per_week=24
        )
        headers = {"HX-Request": "true", "HX-Target": "side-panel-content"}
        panel = reverse("home") + f"?collega={self.anke.public_id}"

        closed = self.client.get(panel, headers=headers).content.decode()
        opened = self.client.get(panel + f"&uitgeklapt={self.assignment.public_id}", headers=headers).content.decode()

        assert "Begeleidt de overgang." in closed
        assert (
            '<span class="wies-card__preview-text"><span class="wies-text-secondary">Taken:</span> '
            "Begeleidt de overgang.</span></p>" in closed
        )
        assert '<div class="wies-card__more" hidden>' in closed
        assert '<p class="wies-card__preview" hidden>' in opened
        assert (
            '<span class="wies-role-description__text"><span class="wies-text-secondary">Taken:</span> '
            "Begeleidt de overgang.\n\nEn stemt af met de directie.</span></p>" in opened
        )
        placement = Placement.objects.get(colleague=self.anke)
        # The placement's own dates on the card, not the opdracht's period.
        assert f"{placement.start_date.day} " in closed.split("wies-card__meta")[1].split("</div>")[0]
        # The viewer is a team mate, not a planner: no hours for them.
        assert "uur per week" not in closed
        self.client.force_login(self.anke_user)
        own = self.client.get(panel, headers=headers).content.decode()
        # On the card's own line, not behind the fold.
        assert "24 uur per week" in own.split("wies-card__more")[0]
        # A description that fits the preview line has nothing behind the fold.
        Service.objects.filter(placements__colleague=self.bram).update(description="Kort.")
        bram = self.client.get(reverse("home") + f"?collega={self.bram.public_id}", headers=headers).content.decode()
        assert "Taken:</span> Kort.</span></p>" in bram
        assert "wies-card__toggle" not in bram
        assert "wies-card__more" not in bram
        self.client.force_login(self.viewer)
        assert 'icon="chevron-down"' in closed
        assert " expanded" not in closed.split("wies-card__toggle")[1].split(">")[0]
        assert '<div class="wies-card__more">' in opened
        assert 'icon="chevron-up"' in opened
        assert " expanded" in opened.split("wies-card__toggle")[1].split(">")[0]
        assert (
            f'<nldd-link class="wies-card__link" href="/?opdracht={self.assignment.public_id}&amp;collega={self.anke.public_id}" text="Zaaksysteem"'
            in closed
        )


class SidePanelSheetTest(TestCase):
    """One sheet include for every page that opens the panel, so the width
    cannot drift between them."""

    def test_every_list_page_renders_one_sheet_at_the_same_width(self):
        client = Client()
        client.force_login(make_bdm_user(email="bdm@rijksoverheid.nl", name="Bdm"))
        for name in ("home", "assignment-list", "bezetting", "user-profile"):
            body = client.get(reverse(name)).content.decode()
            sheets = re.findall(r'<nldd-sheet id="side-panel"[^>]*>', body)
            assert len(sheets) == 1, name
            assert 'width="800px"' in sheets[0], name
