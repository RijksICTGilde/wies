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

    def test_the_description_is_on_every_row_with_a_toggle_past_two_lines(self):
        long_text = "Begeleidt de overgang naar het nieuwe platform. " * 5
        Service.objects.filter(placements__colleague=self.anke).update(description=long_text.strip())
        Service.objects.filter(placements__colleague=self.bram).update(description="Kort.")

        body = self._panel()

        assert "Toon meer" in _row_of(body, "Anke Jacobs")
        assert "Kort." in _row_of(body, "Bram Smit")
        assert "Toon meer" not in _row_of(body, "Bram Smit")


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
