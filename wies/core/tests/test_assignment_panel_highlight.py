"""The opdracht panel marks one colleague's rows via ``?collega=`` (the hook
side_panel.js scrolls to) and the side panel every list page opens is one
sheet at one width."""

import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
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
        # The integer pk must not reach the URL (it is enumerable). The
        # lookahead stops "collega=7" from matching a uuid that starts with 7.
        assert not re.search(rf"collega={self.anke.id}(?![0-9a-f-])", row)
        assert "Begeleidt de overgang." not in row

    def test_the_cv_entry_holds_the_placement_and_opens_for_uitgeklapt(self):
        Service.objects.filter(placements__colleague=self.anke).update(
            description="Begeleidt de overgang. " * 12 + "\n\nEn stemt af met de directie.", hours_per_week=24
        )
        headers = {"HX-Request": "true", "HX-Target": "side-panel-content"}
        panel = reverse("home") + f"?collega={self.anke.public_id}"

        # A second opdracht, so the list does not fall under the single-entry
        # rule below and this one starts collapsed.
        other = Assignment.objects.create(name="Archief", source="wies")
        other_service = Service.objects.create(
            assignment=other, description="Eerder werk.", skill=self.skill, source="wies"
        )
        today = timezone.now().date()
        Placement.objects.create(
            colleague=self.anke,
            service=other_service,
            period_source=Placement.PLACEMENT,
            specific_start_date=today - timedelta(days=20),
            specific_end_date=today + timedelta(days=80),
            source="wies",
        )

        closed = self.client.get(panel, headers=headers).content.decode()
        opened = self.client.get(panel + f"&uitgeklapt={self.assignment.public_id}", headers=headers).content.decode()

        assert "Begeleidt de overgang." in closed
        assert 'text="Taken"' in closed
        assert '<p class="wies-cv__preview">Begeleidt de overgang. Begeleidt' in closed
        assert '<div class="wies-cv__more" hidden>' in closed
        assert '<p class="wies-cv__preview" hidden>' in opened
        # Open, the description is rendered from Markdown. The template's
        # indentation is the formatter's to change, so match on the sequence.
        role_block = opened.split('<div class="wies-role-description">')[1]
        assert 'text="Taken"' in opened
        assert '<span class="wies-role-description__text">Begeleidt de overgang.' in role_block
        assert "En stemt af met de directie." in opened
        placement = Placement.objects.get(colleague=self.anke, service__assignment=self.assignment)
        # The placement's own dates, not the opdracht's period. The line shows
        # month and year; the exact day stays in the title.
        meta_line = closed.split('text="Periode"')[1].split("</nldd-list-item>")[0]
        # The line itself shows month and year ...
        assert placement.start_date.strftime("%Y") in meta_line
        # ... and the exact day stays in the title.
        assert f"{placement.start_date.day} " in meta_line
        # The viewer is a team mate, not a planner: no hours for them.
        assert "uur per week" not in closed
        self.client.force_login(self.anke_user)
        own = self.client.get(panel, headers=headers).content.decode()
        # On the entry's own line, not behind the fold.
        assert "24 uur per week" in own.split("wies-cv__more")[0]
        # A description that fits the preview line has nothing behind the fold.
        Service.objects.filter(placements__colleague=self.bram).update(description="Kort.")
        bram = self.client.get(reverse("home") + f"?collega={self.bram.public_id}", headers=headers).content.decode()
        assert '<p class="wies-cv__preview">Kort.</p>' in bram
        assert "wies-cv__toggle" not in bram
        assert "wies-cv__more" not in bram
        self.client.force_login(self.viewer)
        assert 'start-icon="chevron-down"' in closed
        assert " expanded" not in closed.split("wies-cv__toggle")[1].split(">")[0]
        assert '<div class="wies-cv__more">' in opened
        assert 'start-icon="chevron-up"' in opened
        assert " expanded" in opened.split("wies-cv__toggle")[1].split(">")[0]
        # The Opdracht row is the link, with a chevron saying so; the toggle
        # sits in the Taken row, so the two never compete for the same click.
        row = closed.split('<nldd-list-item class="wies-cv__link"')[1].split("</nldd-list-item>")[0]
        assert f'href="/?opdracht={self.assignment.public_id}&amp;collega={self.anke.public_id}"' in row
        assert 'text="Zaaksysteem"' in row
        assert 'icon="chevron-right"' in row
        assert "data-action" not in row
        entry = closed.split('<li class="wies-cv__item">')[1]
        assert entry.count("nldd-list-item class=") == 1

    def test_an_open_entry_marks_its_preview_hidden(self):
        """Open, the preview must not stand above the block that repeats it.

        This checks the markup; the stylesheet has to cooperate too, because a
        `display` there beats the hidden attribute — hence the
        `:not([hidden])` on .wies-cv__preview, which the CSS test below pins.
        """
        other = Skill.objects.create(name="Arch")
        service = Service.objects.create(
            assignment=self.assignment, description="Tekst van de tweede rol. " * 8, skill=other, source="wies"
        )
        today = timezone.now().date()
        Placement.objects.create(
            colleague=self.anke,
            service=service,
            period_source=Placement.PLACEMENT,
            specific_start_date=today - timedelta(days=10),
            specific_end_date=today + timedelta(days=100),
            source="wies",
        )
        Service.objects.filter(placements__colleague=self.anke, skill=self.skill).update(
            description="Tekst van de eerste rol. " * 8
        )
        headers = {"HX-Request": "true", "HX-Target": "side-panel-content"}
        panel = reverse("home") + f"?collega={self.anke.public_id}"

        opened = self.client.get(panel + f"&uitgeklapt={self.assignment.public_id}", headers=headers).content.decode()

        # Scoped to this opdracht's own entry: the panel lists others too.
        entry = next(
            item for item in opened.split('<li class="wies-cv__item">')[1:] if "Tekst van de eerste rol." in item
        )
        # The preview carries hidden, so it does not stand above the block that
        # repeats it; each role's text is visible exactly once.
        preview = re.search(r'<p class="wies-cv__preview"([^>]*)>', entry)
        assert preview is not None
        assert "hidden" in preview.group(1)
        # Each role's text appears in its own block; the one the preview
        # repeats appears twice, but that copy carries hidden.
        assert '<p class="wies-cv__role-label">Arch</p>' in entry
        assert '<p class="wies-cv__role-label">Dev</p>' in entry
        # The preview runs both texts together; the blocks below carry them
        # once each, under their own role heading.
        preview_text = re.search(r'<p class="wies-cv__preview" hidden>([^<]*)</p>', entry).group(1)
        assert "Tekst van de eerste rol." in preview_text
        assert "Tekst van de tweede rol." in preview_text
        assert entry.count('<div class="wies-cv__role-block">') == 2

    def test_only_your_own_panel_offers_the_pencil_on_your_role(self):
        """You may edit your own role text, so the entry carries the pencil to
        the same sheet the team row opens; someone else's panel does not."""
        Service.objects.filter(placements__colleague=self.anke).update(description="Mijn taken.")
        headers = {"HX-Request": "true", "HX-Target": "side-panel-content"}
        anke_panel = reverse("home") + f"?collega={self.anke.public_id}"

        # A team mate looking at Anke's panel.
        other = self.client.get(anke_panel, headers=headers).content.decode()
        assert 'icon="edit"' not in other.split('<ul class="wies-cv">')[1]

        # Anke looking at her own.
        self.client.force_login(self.anke_user)
        own = self.client.get(anke_panel, headers=headers).content.decode()
        entry = own.split('<ul class="wies-cv">')[1]
        assert 'icon="edit"' in entry
        # A plain consultant edits the text, not the role.
        assert 'text="Mijn taken wijzigen"' in entry
        service = Service.objects.get(placements__colleague=self.anke)
        assert f"teamlid={service.public_id}" in entry

    def test_a_hidden_placement_states_that_above_the_whole_entry(self):
        """The rule hides the entry, not just its period, so the note is a band
        at the top of the block rather than a chip beside one value."""
        placement = Placement.objects.get(colleague=self.anke)
        placement.specific_start_date = timezone.now().date() - timedelta(days=400)
        placement.specific_end_date = timezone.now().date() - timedelta(days=300)
        placement.save()
        headers = {"HX-Request": "true", "HX-Target": "side-panel-content"}

        # Only a privileged viewer sees an ended placement at all.
        self.client.force_login(make_bdm_user(email="band@rijksoverheid.nl"))
        body = self.client.get(reverse("home") + f"?collega={self.anke.public_id}", headers=headers).content.decode()

        entry = body.split('<li class="wies-cv__item">')[1]
        band = entry.split('<nldd-list-item class="wies-cv__privacy">')[1]
        assert "Alleen zichtbaar voor" in band
        # Above the opdracht's own row, so it covers everything under it.
        assert entry.index("wies-cv__privacy") < entry.index("wies-cv__link")
        # "Afgelopen" still belongs to the dates, not to the band.
        assert 'text="Afgelopen"' in entry.split('text="Periode"')[1]

    def test_a_lone_opdracht_opens_its_description_without_asking(self):
        """One entry fills the panel on its own, and a collapsed description
        there reads as if the list itself were cut off."""
        Service.objects.filter(placements__colleague=self.anke).update(
            description="Begeleidt de overgang. " * 12 + "\n\nEn stemt af met de directie."
        )
        headers = {"HX-Request": "true", "HX-Target": "side-panel-content"}
        body = self.client.get(reverse("home") + f"?collega={self.anke.public_id}", headers=headers).content.decode()

        assert body.count('<li class="wies-cv__item">') == 1
        assert '<div class="wies-cv__more">' in body
        assert '<p class="wies-cv__preview" hidden>' in body
        assert "Toon minder" in body


class CvPreviewStylesheetTest(SimpleTestCase):
    """A `display` in the stylesheet beats the `hidden` attribute, so the rule
    that clamps the preview has to exclude hidden ones. Without it an open
    entry showed its first role's text twice, and no template test catches
    that: the markup is right, the stylesheet overrides it."""

    def test_the_preview_rule_does_not_override_hidden(self):
        css = (settings.BASE_DIR / "wies" / "core" / "static" / "css" / "app.css").read_text()
        rule = next(line for line in css.splitlines() if line.startswith(".wies-cv__preview"))

        assert rule.startswith(".wies-cv__preview:not([hidden])"), rule


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
