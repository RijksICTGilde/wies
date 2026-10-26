"""The aanvraag panel: the read view of one open role on an opdracht.

A team row for a placement opens that colleague's panel; an aanvraag has no
colleague, so ``?aanvraag=`` opens this one instead of leaving the row a dead
end.
"""

import json
import re
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.editables.service import request_period_text
from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.tests.role_helpers import make_business_manager_user

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
            request_description="We zoeken een developer voor het zaaksysteem.",
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

    def _place(self, name, **placement):
        colleague = Colleague.objects.create(
            name=name, email=f"{name.split()[0].lower()}@rijksoverheid.nl", source="wies"
        )
        role = Service.objects.create(assignment=self.assignment, skill=self.skill, source="wies")
        Placement.objects.create(colleague=colleague, service=role, source="wies", **placement)
        return colleague

    def _team_text(self):
        body = self._panel()
        row = re.search(r'text="Team".*?text="([^"]*)"', body, re.S)
        assert row, "team row missing"
        return row.group(1)

    def test_the_team_row_names_who_is_placed(self):
        cases = (
            ([], "Nog niemand geplaatst"),
            (["Anke de Vries"], "Anke de Vries"),
            (["Bram Jansen"], "Anke de Vries en Bram Jansen"),
            (["Chris Bakker"], "Anke de Vries, Bram Jansen en 1 ander"),
            (["Dewi Smit"], "Anke de Vries, Bram Jansen en 2 anderen"),
        )
        for new_names, expected in cases:
            for name in new_names:
                self._place(name)
            with self.subTest(expected=expected):
                assert self._team_text() == expected

    def test_a_colleague_in_two_roles_counts_once(self):
        anke = self._place("Anke de Vries")
        second_role = Service.objects.create(assignment=self.assignment, skill=self.skill, source="wies")
        Placement.objects.create(colleague=anke, service=second_role, source="wies")
        assert self._team_text() == "Anke de Vries"

    def test_the_team_row_leaves_out_an_ended_placement_the_viewer_may_not_see(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        self._place(
            "Oud Lid",
            period_source=Placement.PLACEMENT,
            specific_start_date=yesterday - timedelta(days=90),
            specific_end_date=yesterday,
        )
        assert self._team_text() == "Nog niemand geplaatst"

    def test_the_team_row_leaves_out_an_ended_placement_for_a_business_manager(self):
        """A Business Manager sees the ended placement in the opdracht panel,
        labelled as such; the team row names who is on the opdracht now."""
        self.client.force_login(make_business_manager_user(email="bm@rijksoverheid.nl"))
        yesterday = timezone.now().date() - timedelta(days=1)
        self._place(
            "Oud Lid",
            period_source=Placement.PLACEMENT,
            specific_start_date=yesterday - timedelta(days=90),
            specific_end_date=yesterday,
        )
        assert self._team_text() == "Nog niemand geplaatst"

    def test_the_team_row_is_not_a_second_link(self):
        """The Opdracht row above already leads to the team; a second link row
        in an nldd-list is reachable by arrow key only, not by Tab."""
        body = self._panel()
        team_item = re.search(r'<nldd-list-item[^>]*>(?:(?!</nldd-list-item>).)*text="Team"', body, re.S)
        assert team_item
        assert "href=" not in team_item.group(0)

    def test_the_panel_shows_the_hours_and_the_description(self):
        body = self._panel()

        assert "24 uur" in body
        assert "Uren per week" in body
        assert 'text="Wie we zoeken"' in body
        assert "We zoeken een developer voor het zaaksysteem." in body

    def test_the_panel_shows_the_vacancy_text_not_the_taken(self):
        """The taken belong to whoever fills the role; an aanvraag is read by
        its vacancy text."""
        body = self._panel()

        assert 'text="Taken"' not in body
        assert "Bouwt de koppeling." not in body

    def test_a_long_description_shows_whole_without_toon_meer(self):
        self.service.request_description = "Wat ga je doen?\n" + "x" * 3000 + " einde."
        self.service.save()

        body = self._panel()

        assert "einde." in body
        assert "Toon meer" not in body

    def test_an_aanvraag_without_hours_leaves_the_row_out(self):
        self.service.hours_per_week = None
        self.service.save()

        body = self._panel()

        assert "Uren per week" not in body

    def test_a_viewer_without_edit_rights_gets_no_edit_action(self):
        body = self._panel()

        assert "Aanvraag wijzigen" not in body

    def test_an_otys_aanvraag_says_why_it_cannot_be_changed(self):
        """Even a business manager gets no pencil on an OTYS opdracht; the
        panel says where it is managed instead."""
        bdm = make_business_manager_user(email="bdm@rijksoverheid.nl")
        self.assignment.owner = bdm.colleague
        self.assignment.source = "otys_iir"
        self.assignment.save()
        self.client.force_login(bdm)

        body = self._panel()

        assert "Aanvraag wijzigen" not in body
        assert "Wordt beheerd in OTYS IIR. Wijzigen kan alleen daar." in body

    def test_a_wies_aanvraag_has_no_managed_elsewhere_line(self):
        assert "Wordt beheerd in" not in self._panel()

    def test_the_edit_toolbar_has_an_accessible_name(self):
        bdm = make_business_manager_user(email="bdm@rijksoverheid.nl")
        self.assignment.owner = bdm.colleague
        self.assignment.save()
        self.client.force_login(bdm)

        assert '<nldd-toolbar accessible-label="Aanvraag">' in self._panel()

    def test_a_team_editor_can_reach_the_edit_sheet_from_the_panel(self):
        bdm = make_business_manager_user(email="bdm@rijksoverheid.nl")
        self.assignment.owner = bdm.colleague
        self.assignment.save()
        self.client.force_login(bdm)

        body = self._panel()

        assert "Aanvraag wijzigen" in body
        assert f"teamlid={self.service.public_id}" in body

    def test_editing_from_the_panel_opens_the_sheet_and_returns_to_the_aanvraag(self):
        """The edit URL carries ?aanvraag= as well, so saving and going back
        land on this panel; with ?teamlid= the sheet wins over the panel."""
        bdm = make_business_manager_user(email="bdm3@rijksoverheid.nl")
        self.assignment.owner = bdm.colleague
        self.assignment.save()
        self.client.force_login(bdm)
        edit_url = (
            reverse("home")
            + f"?opdracht={self.assignment.public_id}&aanvraag={self.service.public_id}&teamlid={self.service.public_id}"
        )

        body = self.client.get(edit_url, headers=HX).content.decode()

        assert edit_url.replace("&", "&amp;") in self._panel()
        assert "data-member-form" in body
        assert 'back-text="Aanvraag"' in body
        assert (
            f'name="terug_url" value="/?opdracht={self.assignment.public_id}&amp;aanvraag={self.service.public_id}"'
            in body
        )

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
        bdm = make_business_manager_user(email="bdm2@rijksoverheid.nl")
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
    """A filled or hidden row resolved here would show the hours and taken that
    the team row withholds, to anyone holding a service public_id (#693)."""

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
            assignment=self.assignment,
            request_description="Open aanvraag.",
            skill=self.skill,
            hours_per_week=36,
            source="wies",
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
        assert "Open aanvraag." in body

    def test_a_full_page_load_renders_without_the_panel(self):
        """No HX-Request: a filled row gives the list page, not a 404 -- the
        same as an unknown id, so nothing distinguishes the two."""
        url = reverse("home") + f"?opdracht={self.assignment.public_id}&aanvraag={self.filled.public_id}"
        response = self.client.get(url)

        assert response.status_code == 200
        assert "Taken van Anke Jacobs." not in response.content.decode()


class AanvraagFormRequestDescriptionTest(TestCase):
    """The teamlid sheet keeps the vacancy text of an aanvraag apart from the
    taken of a placement: one shows per status, both post."""

    def setUp(self):
        self.client = Client()
        self.bdm = make_business_manager_user(email="bdm@rijksoverheid.nl")
        self.assignment = Assignment.objects.create(name="Zaaksysteem", source="wies", owner=self.bdm.colleague)
        self.skill = Skill.objects.create(name="Dev")
        self.client.force_login(self.bdm)

    def _post(self, **fields):
        return self.client.post(
            reverse("assignment-member-edit", args=[self.assignment.public_id]),
            {"skill": str(self.skill.public_id), "is_filled": "aanvraag", "has_custom_period": "on", **fields},
        )

    def test_a_vacancy_text_longer_than_the_taken_limit_is_saved(self):
        text = "Wat ga je doen?\n" + "x" * 9000

        response = self._post(request_description=text, description="")

        assert response.status_code == 204, response.content
        [service] = self.assignment.services.all()
        assert service.request_description == text
        assert service.description == ""

    def test_editing_an_aanvraag_keeps_both_texts(self):
        service = Service.objects.create(
            assignment=self.assignment, skill=self.skill, description="Oude taken.", source="wies"
        )

        response = self._post(
            service_public_id=str(service.public_id), request_description="Nieuwe tekst.", description="Oude taken."
        )

        assert response.status_code == 204, response.content
        service.refresh_from_db()
        assert service.request_description == "Nieuwe tekst."
        assert service.description == "Oude taken."

    def test_a_new_aanvraag_shows_the_description_and_hides_the_taken(self):
        body = self.client.get(
            reverse("home"), {"opdracht": self.assignment.public_id, "teamlid": "nieuw-aanvraag"}
        ).content.decode()

        assert re.search(r"<div data-request-field\s*>", body)
        assert re.search(r"<div data-tasks-field\s*hidden>", body)
        assert 'text="Per direct"' in body

    def test_a_new_placement_shows_the_taken_and_hides_the_description(self):
        body = self.client.get(
            reverse("home"), {"opdracht": self.assignment.public_id, "teamlid": "nieuw-ingevuld"}
        ).content.decode()

        assert re.search(r"<div data-request-field\s*hidden>", body)
        assert re.search(r"<div data-tasks-field\s*>", body)


class AanvraagFlexiblePeriodTest(TestCase):
    """An aanvraag can start "per direct" and run for a duration instead of
    dates; a placement cannot, so filling one drops both."""

    def setUp(self):
        self.client = Client()
        self.bdm = make_business_manager_user(email="bdm@rijksoverheid.nl")
        self.assignment = Assignment.objects.create(name="Zaaksysteem", source="wies", owner=self.bdm.colleague)
        self.skill = Skill.objects.create(name="Dev")
        self.client.force_login(self.bdm)

    def _post(self, **fields):
        return self.client.post(
            reverse("assignment-member-edit", args=[self.assignment.public_id]),
            {"skill": str(self.skill.public_id), "is_filled": "aanvraag", **fields},
        )

    def _panel(self, service):
        url = reverse("home") + f"?opdracht={self.assignment.public_id}&aanvraag={service.public_id}"
        return self.client.get(url, headers=HX).content.decode()

    def test_per_direct_for_a_year_is_saved_and_shown(self):
        response = self._post(start_mode="NOW", end_mode="DURATION", duration_months="12", location="Den Haag, hybride")

        assert response.status_code == 204, response.content
        [service] = self.assignment.services.all()
        assert service.starts_immediately
        assert service.duration_months == 12
        assert service.period_source == Service.SERVICE
        body = self._panel(service)
        assert 'text="Per direct, voor 1 jaar"' in body
        assert 'text="Den Haag, hybride"' in body

    def test_per_direct_drops_a_leftover_start_date(self):
        response = self._post(start_mode="NOW", placement_start_date="2026-11-01")

        assert response.status_code == 204, response.content
        [service] = self.assignment.services.all()
        assert service.specific_start_date is None
        assert 'text="Per direct"' in self._panel(service)

    def test_a_start_date_with_a_duration_reads_as_from_for(self):
        self._post(placement_start_date="2026-11-01", duration_months="6")

        [service] = self.assignment.services.all()
        assert 'text="Vanaf 1 nov 2026, voor 6 maanden"' in self._panel(service)

    def test_an_end_date_wins_over_a_duration(self):
        self._post(placement_start_date="2026-11-01", placement_end_date="2027-04-30", duration_months="6")

        [service] = self.assignment.services.all()
        assert service.duration_months is None
        assert 'text="1 nov 2026 t/m 30 apr 2027"' in self._panel(service)

    def test_an_own_period_still_needs_something(self):
        response = self._post()

        assert response.status_code == 200
        assert not self.assignment.services.exists()

    def test_period_errors_point_at_their_date_field(self):
        """Start and Einde each open with a choice, which a validation list
        without `for` would take as its control; the error then stays hidden."""
        body = self._post(placement_start_date="2026-11-01", placement_end_date="2026-10-01").content.decode()

        end_id = re.search(r'name="placement_end_date" id="([^"]+)" accessible-label="Einddatum"', body)[1]
        assert f'<nldd-validation-list for="{end_id}">' in body

        body = self._post().content.decode()
        start_id = re.search(r'name="placement_start_date" id="([^"]+)" accessible-label="Startdatum"', body)[1]
        assert f'<nldd-validation-list for="{start_id}">' in body

    def test_date_field_ids_change_per_render(self):
        """htmx settles an element whose id was already on the page, which
        strips the style the date field set on itself: it shrinks after an
        error. A fresh id keeps the swapped-in field new."""
        pattern = r'name="placement_end_date" id="([^"]+)"'
        first = re.search(pattern, self._post().content.decode())[1]
        second = re.search(pattern, self._post().content.decode())[1]
        assert first != second

    def test_duur_without_a_duration_asks_for_one(self):
        response = self._post(start_mode="NOW", end_mode="DURATION")

        assert response.status_code == 200
        assert "Kies een duur." in response.content.decode()
        assert not self.assignment.services.exists()

    def test_filling_an_aanvraag_drops_per_direct_and_the_duration(self):
        consultant = Colleague.objects.create(name="Anke Jacobs", email="anke@rijksoverheid.nl", source="wies")
        service = Service.objects.create(
            assignment=self.assignment,
            skill=self.skill,
            period_source=Service.SERVICE,
            starts_immediately=True,
            duration_months=12,
            source="wies",
        )

        response = self._post(
            service_public_id=str(service.public_id),
            is_filled="ingevuld",
            colleague=str(consultant.public_id),
            start_mode="NOW",
            end_mode="DURATION",
            duration_months="12",
            placement_start_date="2026-11-01",
        )

        assert response.status_code == 204, response.content
        service.refresh_from_db()
        assert not service.starts_immediately
        assert service.duration_months is None

    def test_the_team_row_shows_the_flexible_period(self):
        Service.objects.create(
            assignment=self.assignment,
            skill=self.skill,
            period_source=Service.SERVICE,
            starts_immediately=True,
            duration_months=24,
            source="wies",
        )

        body = self.client.get(reverse("home") + f"?opdracht={self.assignment.public_id}", headers=HX).content.decode()

        assert "Per direct, voor 2 jaar" in body

    def test_the_sheet_reopens_on_the_flexible_period(self):
        """An opdracht without dates matches a per-direct aanvraag's empty
        dates; the sheet must still open on "Anders...", not "Van opdracht"."""
        service = Service.objects.create(
            assignment=self.assignment,
            skill=self.skill,
            period_source=Service.SERVICE,
            starts_immediately=True,
            duration_months=6,
            source="wies",
        )

        body = self.client.get(
            reverse("home"), {"opdracht": self.assignment.public_id, "teamlid": str(service.public_id)}
        ).content.decode()

        assert re.search(r'value="PLACEMENT"[^>]*data-period-choice', body)
        assert re.search(r'value="NOW"[^>]*data-start-choice', body)
        assert re.search(r'value="DURATION"[^>]*data-end-choice', body)

    def test_the_sheet_reopens_on_an_end_date(self):
        """The end-date choice must open on "Op datum" for a saved end date;
        otherwise the date is wiped on save."""
        service = Service.objects.create(
            assignment=self.assignment,
            skill=self.skill,
            period_source=Service.SERVICE,
            specific_start_date=date(2026, 11, 1),
            specific_end_date=date(2027, 4, 30),
            source="wies",
        )

        body = self.client.get(
            reverse("home"), {"opdracht": self.assignment.public_id, "teamlid": str(service.public_id)}
        ).content.decode()

        assert re.search(r'value="DATE"[^>]*data-end-choice', body)
        assert re.search(r"<div data-end-date\s*>", body)
        assert re.search(r'name="end_mode"\s+value="DATE"', body)

    def test_onbekend_drops_a_leftover_end_date_and_duration(self):
        response = self._post(
            placement_start_date="2026-11-01",
            end_mode="OPEN",
            placement_end_date="2027-04-30",
            duration_months="6",
        )

        assert response.status_code == 204, response.content
        service = self.assignment.services.get()
        assert service.specific_end_date is None
        assert service.duration_months is None

    def test_op_datum_drops_a_leftover_duration(self):
        self._post(
            placement_start_date="2026-11-01", end_mode="DATE", placement_end_date="2027-04-30", duration_months="6"
        )

        assert self.assignment.services.get().duration_months is None


class RequestPeriodTextTest(SimpleTestCase):
    """Every combination the period of an aanvraag can be in, in words."""

    def _text(self, **fields):
        return request_period_text(Service(period_source=Service.SERVICE, **fields))

    def test_each_combination_reads_as_a_sentence(self):
        cases = {
            "1 nov 2026 t/m 30 apr 2027": {
                "specific_start_date": date(2026, 11, 1),
                "specific_end_date": date(2027, 4, 30),
            },
            "Per direct t/m 30 apr 2027": {"starts_immediately": True, "specific_end_date": date(2027, 4, 30)},
            "t/m 30 apr 2027": {"specific_end_date": date(2027, 4, 30)},
            "Per direct, voor 1 jaar": {"starts_immediately": True, "duration_months": 12},
            "Vanaf 1 nov 2026, voor 6 maanden": {"specific_start_date": date(2026, 11, 1), "duration_months": 6},
            "Voor 6 maanden": {"duration_months": 6},
            "Per direct": {"starts_immediately": True},
            "Vanaf 1 nov 2026": {"specific_start_date": date(2026, 11, 1)},
            "": {},
        }
        for expected, fields in cases.items():
            with self.subTest(expected):
                assert self._text(**fields) == expected


class LeavingAnAanvraagTest(TestCase):
    """Filling or deleting an aanvraag from its panel returns to the opdracht:
    the aanvraag panel the sheet came from no longer exists, and htmx swaps
    nothing on its 404, leaving the sheet open."""

    def setUp(self):
        self.client = Client()
        self.bdm = make_business_manager_user(email="bdm@rijksoverheid.nl")
        self.assignment = Assignment.objects.create(name="Zaaksysteem", source="wies", owner=self.bdm.colleague)
        self.skill = Skill.objects.create(name="Dev")
        self.service = Service.objects.create(assignment=self.assignment, skill=self.skill, source="wies")
        self.terug_url = f"/?opdracht={self.assignment.public_id}&aanvraag={self.service.public_id}"
        self.client.force_login(self.bdm)

    def _follow(self, response):
        assert response.status_code == 204, response.content
        path = json.loads(response["HX-Location"])["path"]
        return path, self.client.get(path, headers=HX)

    def test_filling_returns_to_the_opdracht_panel(self):
        consultant = Colleague.objects.create(name="Anke Jacobs", email="anke@rijksoverheid.nl", source="wies")

        response = self.client.post(
            reverse("assignment-member-edit", args=[self.assignment.public_id]),
            {
                "service_public_id": str(self.service.public_id),
                "skill": str(self.skill.public_id),
                "is_filled": "ingevuld",
                "colleague": str(consultant.public_id),
                "has_custom_period": "on",
                "terug_url": self.terug_url,
            },
        )

        path, follow = self._follow(response)
        assert path == f"/?opdracht={self.assignment.public_id}"
        assert follow.status_code == 200

    def test_editing_an_aanvraag_returns_to_its_panel(self):
        response = self.client.post(
            reverse("assignment-member-edit", args=[self.assignment.public_id]),
            {
                "service_public_id": str(self.service.public_id),
                "skill": str(self.skill.public_id),
                "is_filled": "aanvraag",
                "has_custom_period": "on",
                "terug_url": self.terug_url,
            },
        )

        path, follow = self._follow(response)
        assert path == self.terug_url
        assert follow.status_code == 200

    def test_deleting_returns_to_the_opdracht_panel(self):
        response = self.client.post(
            reverse("assignment-member-delete", args=[self.assignment.public_id, self.service.public_id]),
            {"terug_url": self.terug_url},
        )

        path, follow = self._follow(response)
        assert path == f"/?opdracht={self.assignment.public_id}"
        assert follow.status_code == 200


class FillingAanvraagTakenTest(TestCase):
    """Filling an aanvraag: "Taken" are the consultant's own words."""

    def setUp(self):
        self.client = Client()
        self.bdm = make_business_manager_user(email="bdm@rijksoverheid.nl")
        self.assignment = Assignment.objects.create(name="Zaaksysteem", source="wies", owner=self.bdm.colleague)
        self.skill = Skill.objects.create(name="Dev")
        self.client.force_login(self.bdm)

    def test_taken_take_up_to_500_characters(self):
        consultant = Colleague.objects.create(name="Anke Jacobs", email="anke@rijksoverheid.nl", source="wies")
        url = reverse("assignment-member-edit", args=[self.assignment.public_id])
        fields = {
            "skill": str(self.skill.public_id),
            "is_filled": "ingevuld",
            "colleague": str(consultant.public_id),
            "has_custom_period": "on",
        }

        assert self.client.post(url, {**fields, "description": "x" * 501}).status_code == 200
        assert self.client.post(url, {**fields, "description": "x" * 500}).status_code == 204
        assert self.assignment.services.get().description == "x" * 500
