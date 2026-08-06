"""PoC opmerkingen bij een opdracht: rijen met een "…"-menu (zoals het team),
per-opmerking bewerken in een child-sheet, en de zichtbare notities op het bord
(met live OOB-swap)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, AssignmentNote, Colleague

User = get_user_model()

#: HX-headers voor een paneel-swap: de lijstview levert alleen de paneel-partial
#: als het doel side-panel-content is (anders de kaartenlijst).
PANEL_HX = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "side-panel-content"}


class AssignmentNotesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl")
        self.client.force_login(self.owner_user)
        self.owner = Colleague.objects.get(user=self.owner_user)
        self.assignment = Assignment.objects.create(
            name="Test Opdracht",
            source="wies",
            owner=self.owner,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

    def _panel_url(self, **params):
        query = "".join(f"&{k}={v}" for k, v in params.items())
        return reverse("assignment-list") + f"?opdracht={self.assignment.id}{query}"

    def test_panel_lists_notes_with_menu(self):
        """Het paneel toont opmerkingen als rijen met een toevoeg-knop; een
        show_on_board-notitie krijgt de 'Op het bord'-tag."""
        AssignmentNote.objects.create(
            assignment=self.assignment, author=self.owner, text="Bestaande opmerking", show_on_board=True
        )
        body = self.client.get(self._panel_url(), **PANEL_HX).content.decode()
        assert "Opmerkingen" in body
        assert "Bestaande opmerking" in body
        assert "Op het bord" in body  # show_on_board-tag
        assert "notitie=nieuw" in body  # toevoeg-knop
        assert "Bewerken" in body  # rijmenu

    def test_add_note_child_sheet_and_save(self):
        """?notitie=nieuw opent het lege formulier; opslaan maakt de notitie aan
        en her-rendert het opdrachtpaneel + de bord-kaart (OOB)."""
        sheet = self.client.get(self._panel_url(notitie="nieuw"), **PANEL_HX).content.decode()
        assert "Opmerking toevoegen" in sheet
        assert 'name="text"' in sheet
        assert "Klein tonen op de bord-kaart" in sheet

        r = self.client.post(
            reverse("assignment-note-save", args=[self.assignment.id, 0]),
            {"text": "Nieuwe opmerking", "show_on_board": "1", "terug_url": self._panel_url()},
            headers={"hx-request": "true"},
        )
        assert r.status_code == 200
        note = self.assignment.notes.get(text="Nieuwe opmerking")
        assert note.show_on_board
        assert note.author == self.owner
        # De response her-rendert het opdrachtpaneel met de verse notitie (de
        # child-sheet sluit) plus de bord-kaart als OOB-swap. De paneel-acties
        # wijzen terug naar de ouder-URL, niet naar het save-endpoint.
        body = r.content.decode()
        assert "Nieuwe opmerking" in body
        assert 'hx-swap-oob="true"' in body
        assert "opslaan" not in body

    def test_edit_note_child_sheet_and_save(self):
        """?notitie=<id> opent het formulier met de bestaande waarden; opslaan
        werkt tekst én show_on_board bij."""
        note = AssignmentNote.objects.create(
            assignment=self.assignment, author=self.owner, text="Oud", show_on_board=False
        )
        sheet = self.client.get(self._panel_url(notitie=note.id), **PANEL_HX).content.decode()
        assert "Opmerking bewerken" in sheet
        # De tekst zit in het value-attribuut (de textarea leest .value, niet de body).
        assert 'value="Oud"' in sheet
        # Switch i.p.v. checkbox voor 'tonen op het bord'.
        assert "nldd-switch" in sheet

        r = self.client.post(
            reverse("assignment-note-save", args=[self.assignment.id, note.id]),
            {"text": "Nieuw", "show_on_board": "1"},
            headers={"hx-request": "true"},
        )
        assert r.status_code == 200
        note.refresh_from_db()
        assert note.text == "Nieuw"
        assert note.show_on_board

    def test_save_empty_text_reshows_form_with_error(self):
        r = self.client.post(
            reverse("assignment-note-save", args=[self.assignment.id, 0]),
            {"text": "   "},
            headers={"hx-request": "true"},
        )
        assert r.status_code == 200
        assert self.assignment.notes.count() == 0
        assert "Vul een opmerking in" in r.content.decode()

    def test_delete_note(self):
        note = AssignmentNote.objects.create(assignment=self.assignment, author=self.owner, text="Weg")
        r = self.client.post(
            reverse("assignment-note-delete", args=[self.assignment.id, note.id]), headers={"hx-request": "true"}
        )
        assert r.status_code == 200
        assert not AssignmentNote.objects.filter(id=note.id).exists()

    def test_non_owner_cannot_manage(self):
        other = User.objects.create_user(email="outsider@rijksoverheid.nl")
        c = Client()
        c.force_login(other)
        r = c.post(
            reverse("assignment-note-save", args=[self.assignment.id, 0]),
            {"text": "x"},
            HTTP_HX_REQUEST="true",
        )
        assert r.status_code == 403

    def test_show_on_board_note_visible_on_card(self):
        """Alleen een show_on_board-notitie staat zichtbaar op de bord-kaart."""
        AssignmentNote.objects.create(
            assignment=self.assignment, author=self.owner, text="Zichtbaar op bord", show_on_board=True
        )
        AssignmentNote.objects.create(
            assignment=self.assignment, author=self.owner, text="Verborgen", show_on_board=False
        )
        body = self.client.get(reverse("bm-board")).content.decode()
        assert f'id="bm-card-{self.assignment.id}"' in body
        assert "Zichtbaar op bord" in body
        assert "Verborgen" not in body

    def test_board_panel_stays_on_board_url(self):
        """?opdracht= op /bord opent het paneel daar (refresh-bestendig); de
        note-URL's blijven op /bord."""
        body = self.client.get(reverse("bm-board") + f"?opdracht={self.assignment.id}").content.decode()
        assert self.assignment.name in body
        assert "notitie=nieuw" in body

    def test_note_save_returns_oob_card(self):
        """Na opslaan komt de bord-kaart als OOB-swap mee, zodat het bord live
        bijwerkt zonder reload."""
        r = self.client.post(
            reverse("assignment-note-save", args=[self.assignment.id, 0]),
            {"text": "OOB test", "show_on_board": "1"},
            headers={"hx-request": "true"},
        )
        assert r.status_code == 200
        body = r.content.decode()
        assert 'hx-swap-oob="true"' in body
        assert f'id="bm-card-{self.assignment.id}"' in body
        assert "OOB test" in body
