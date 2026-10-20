"""K1: adding an aanvraag or a placed consultant starts at "Bij welke opdracht?".

Covers the query behind the step (``find_pickable_assignments``), the team
count in words, the panel on ``?nieuwe-aanvraag`` / ``?nieuwe-plaatsing``, the
``assignment-pick-results`` search route, the split button that opens it, the
back target of the team member sheet, and the rights per role.
"""

import re
from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from config.jinja2 import datum_nl
from wies.core.models import Assignment, Colleague, OrganizationUnit
from wies.core.roles import ROLE_USER_ADMIN, setup_roles
from wies.core.services.assignments import find_pickable_assignments, team_count_text
from wies.core.tests.role_helpers import (
    STAFF_EMAIL,
    grant_business_manager,
    grant_consultant,
    make_business_manager_user,
    make_staff_user,
)
from wies.core.tests.test_assignment_duplicate_hint import add_placement, add_request, make_assignment
from wies.rijksauth.models import User

PICK_URL = reverse("assignment-pick-results")
LIST_URL = reverse("assignment-list")
PANEL_HEADERS = {"hx-request": "true", "hx-target": "side-panel-content"}


def set_created(assignment, days_ago):
    Assignment.objects.filter(pk=assignment.pk).update(created_at=timezone.now() - timedelta(days=days_ago))


def tag(content, name, text):
    """The opening tag of the ``name`` element whose text attribute is ``text``."""
    match = re.search(rf'<{name}\b[^>]*\btext="{re.escape(text)}"[^>]*>', content)
    assert match, f'<{name} text="{text}"> missing'
    return match.group(0)


class FindPickableAssignmentsTest(TestCase):
    def setUp(self):
        self.today = timezone.now().date()
        self.org = OrganizationUnit.objects.create(name="Belastingdienst Centraal", label="Belastingdienst")
        self.owner = Colleague.objects.create(name="Bm", email="bm@rijksoverheid.nl", source="wies")
        self.other = Colleague.objects.create(name="Ander", email="ander@rijksoverheid.nl", source="wies")

    def find(self, term="", owner=None, limit=20):
        found, total = find_pickable_assignments(term, owner=owner, today=self.today, limit=limit)
        return found, total

    def names(self, term="", owner=None, limit=20):
        return [a.name for a in self.find(term, owner, limit)[0]]

    def test_running_wies_opdrachten_only(self):
        make_assignment("Doorlopend", self.org, start=self.today - timedelta(days=400))
        make_assignment("Laatste dag", self.org, end=self.today)
        make_assignment("Begint later", self.org, start=self.today + timedelta(days=30))
        make_assignment("Afgelopen", self.org, end=self.today - timedelta(days=1))
        make_assignment("Uit OTYS", self.org, source="otys")
        assert set(self.names()) == {"Doorlopend", "Laatste dag", "Begint later"}

    def test_opdracht_without_client_counts(self):
        # The step lists opdrachten, not clients: no opdrachtgever is no reason to leave one out.
        make_assignment("Zonder opdrachtgever")
        assert self.names() == ["Zonder opdrachtgever"]

    def test_excluded_client_is_left_out(self):
        aivd = OrganizationUnit.objects.create(name="Algemene Inlichtingen- en Veiligheidsdienst")
        make_assignment("Geheim", aivd)
        make_assignment("Zichtbaar", self.org)
        assert self.names() == ["Zichtbaar"]
        assert self.find()[1] == 1

    def test_search_on_name_is_case_insensitive(self):
        make_assignment("Zaaksysteem Toeslagen", self.org)
        make_assignment("Datalab", self.org)
        assert self.names("zaaksys") == ["Zaaksysteem Toeslagen"]

    def test_search_on_client_name_label_and_abbreviation(self):
        org = OrganizationUnit.objects.create(
            name="Rijkswaterstaat Centrale Informatievoorziening", label="RWS CIV", abbreviations=["CIVX"]
        )
        make_assignment("Datalab", org)
        make_assignment("Elders", self.org)
        for term in ("informatievoorziening", "rws civ", "civx"):
            assert self.names(term) == ["Datalab"], term

    def test_two_matching_clients_give_the_opdracht_once(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        douane = OrganizationUnit.objects.create(name="Belastingdienst Douane", label="Douane")
        assignment.organization_relations.create(organization=douane, role="INVOLVED")
        add_request(assignment)
        add_request(assignment)
        found, total = self.find("belastingdienst")
        assert [a.name for a in found] == ["Zaaksysteem"]
        assert total == 1
        # The two clients must not double the team counts either.
        assert (found[0].open_count, found[0].placed_count) == (2, 0)

    def test_no_match(self):
        make_assignment("Zaaksysteem", self.org)
        assert self.find("onbekend") == ([], 0)

    def test_own_opdrachten_first_then_newest(self):
        own_old = make_assignment("Eigen oud", self.org, owner=self.owner)
        own_new = make_assignment("Eigen nieuw", self.org, owner=self.owner)
        other_new = make_assignment("Ander nieuw", self.org, owner=self.other)
        other_old = make_assignment("Ander oud", self.org, owner=self.other)
        for assignment, days_ago in ((own_old, 10), (own_new, 5), (other_new, 1), (other_old, 20)):
            set_created(assignment, days_ago)
        assert self.names(owner=self.owner) == ["Eigen nieuw", "Eigen oud", "Ander nieuw", "Ander oud"]

    def test_without_owner_newest_first(self):
        old = make_assignment("Oud", self.org, owner=self.owner)
        new = make_assignment("Nieuw", self.org, owner=self.other)
        set_created(old, 10)
        set_created(new, 1)
        assert self.names() == ["Nieuw", "Oud"]

    def test_limit_with_total(self):
        for i in range(5):
            make_assignment(f"Opdracht {i}", self.org)
        found, total = self.find(limit=3)
        assert len(found) == 3
        assert total == 5

    def test_team_counts_including_an_opdracht_without_roles(self):
        consultant = Colleague.objects.create(name="Piet", email="piet@rijksoverheid.nl", source="wies")
        mixed = make_assignment("Gemengd", self.org)
        set_created(mixed, 1)
        add_request(mixed)
        add_request(mixed)
        add_placement(mixed, consultant)
        empty = make_assignment("Leeg", self.org)
        set_created(empty, 2)
        found, _total = self.find()
        assert [(a.name, a.open_count, a.placed_count) for a in found] == [("Gemengd", 2, 1), ("Leeg", 0, 0)]


class TeamCountTextTest(TestCase):
    def test_empty_team(self):
        assert team_count_text(0, 0) == "nog geen rollen"

    def test_singular(self):
        assert team_count_text(1, 0) == "1 aanvraag"
        assert team_count_text(0, 1) == "1 plaatsing"

    def test_plural_and_mixed(self):
        assert team_count_text(2, 1) == "2 aanvragen, 1 plaatsing"
        assert team_count_text(1, 3) == "1 aanvraag, 3 plaatsingen"
        assert team_count_text(0, 2) == "2 plaatsingen"


class PickBase(TestCase):
    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.bm = make_business_manager_user()
        self.org = OrganizationUnit.objects.create(name="Belastingdienst Centraal", label="Belastingdienst")

    def login(self, user=None):
        self.client.force_login(user or self.bm)

    def consultant_user(self):
        return grant_consultant(User.objects.create_user(email="consultant@rijksoverheid.nl"))

    def user_admin_user(self):
        user = User.objects.create_user(email="beheer@rijksoverheid.nl")
        user.groups.add(Group.objects.get(name=ROLE_USER_ADMIN))
        return user

    def no_role_user(self):
        return User.objects.create_user(email="niemand@rijksoverheid.nl")


class PickPanelTest(PickBase):
    def panel(self, params):
        self.login()
        response = self.client.get(LIST_URL, params, headers=PANEL_HEADERS)
        assert response.status_code == 200
        return response.content.decode()

    def test_aanvraag_panel_title_question_and_search(self):
        content = self.panel({"nieuwe-aanvraag": ""})
        assert re.search(r'<nldd-top-title-bar[^>]*text="Aanvraag toevoegen"', content)
        assert '<h2 id="panel-title" tabindex="-1">Bij welke opdracht?</h2>' in content
        field = re.search(r"<nldd-search-field.*?>", content, re.DOTALL).group(0)
        assert f'hx-get="{PICK_URL}?soort=aanvraag"' in field
        assert 'hx-target="#assignment-pick-results"' in field
        assert 'placeholder="Opdracht of opdrachtgever zoeken"' in field
        assert 'accessible-label="Zoek op opdracht of opdrachtgever"' in field

    def test_new_assignment_button_carries_daarna_and_comes_before_the_search(self):
        content = self.panel({"nieuwe-aanvraag": ""})
        button = tag(content, "nldd-button", "Nieuwe opdracht invoeren")
        assert f'hx-get="{LIST_URL}?nieuwe-opdracht=&amp;daarna=aanvraag"' in button
        assert content.index("Nieuwe opdracht invoeren") < content.index("<nldd-search-field")

    def test_rows_show_name_and_details_and_open_the_aanvraag_sheet(self):
        start, end = self.today - timedelta(days=30), self.today + timedelta(days=200)
        assignment = make_assignment("Zaaksysteem", self.org, start=start, end=end)
        add_request(assignment)
        add_request(assignment)
        add_placement(assignment, Colleague.objects.create(name="Piet", email="piet@rijksoverheid.nl", source="wies"))
        content = self.panel({"nieuwe-aanvraag": ""})
        assert "<span>Zaaksysteem</span>" in content
        details = f"Belastingdienst · {datum_nl(start)} t/m {datum_nl(end)} · 2 aanvragen, 1 plaatsing"
        assert f'<span slot="supporting-text">{details}</span>' in content
        pid = assignment.public_id
        assert f'hx-get="{LIST_URL}?opdracht={pid}&amp;teamlid=nieuw-aanvraag"' in content

    def test_row_without_client_or_period(self):
        make_assignment("Kaal")
        content = self.panel({"nieuwe-aanvraag": ""})
        assert '<span slot="supporting-text">Geen periode opgegeven · nog geen rollen</span>' in content

    def test_rows_are_buttons_without_href(self):
        make_assignment("Zaaksysteem", self.org)
        content = self.panel({"nieuwe-aanvraag": ""})
        items = re.findall(r"<nldd-list-item[^>]*>", content)
        assert len(items) == 1
        assert " button " in items[0]
        assert "href=" not in items[0]

    def test_plaatsing_panel(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        content = self.panel({"nieuwe-plaatsing": ""})
        assert re.search(r'<nldd-top-title-bar[^>]*text="Geplaatste consultant toevoegen"', content)
        assert "Bij welke opdracht?" in content
        assert f'hx-get="{PICK_URL}?soort=plaatsing"' in content
        button = tag(content, "nldd-button", "Nieuwe opdracht invoeren")
        assert "daarna=plaatsing" in button
        assert f"opdracht={assignment.public_id}&amp;teamlid=nieuw-ingevuld" in content
        assert "nieuw-aanvraag" not in content

    def test_page_filters_are_kept_and_panel_params_dropped(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        content = self.panel({"zoek": "data", "nieuwe-aanvraag": "", "collega": "5"})
        pid = assignment.public_id
        assert f'hx-get="{LIST_URL}?zoek=data&amp;opdracht={pid}&amp;teamlid=nieuw-aanvraag"' in content
        button = tag(content, "nldd-button", "Nieuwe opdracht invoeren")
        assert f'hx-get="{LIST_URL}?zoek=data&amp;nieuwe-opdracht=&amp;daarna=aanvraag"' in button
        assert "collega=5" not in content

    def test_the_page_search_does_not_filter_the_rows(self):
        # ?zoek= belongs to the list behind the panel; the panel starts unfiltered.
        make_assignment("Zaaksysteem", self.org)
        content = self.panel({"zoek": "iets anders", "nieuwe-aanvraag": ""})
        assert "<span>Zaaksysteem</span>" in content

    def test_full_page_get_opens_the_panel_on_the_list(self):
        self.login()
        response = self.client.get(LIST_URL, {"nieuwe-aanvraag": ""})
        assert response.status_code == 200
        self.assertContains(response, "Bij welke opdracht?")
        self.assertContains(response, "<nldd-split-button")

    def test_empty_panel(self):
        content = self.panel({"nieuwe-aanvraag": ""})
        assert 'data-announce="Er lopen nu geen opdrachten"' in content
        assert "Voer eerst een nieuwe opdracht in." in content

    def test_bezetting_opens_the_same_panel_with_urls_on_bezetting(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        self.login()
        url = reverse("bezetting")
        content = self.client.get(url, {"nieuwe-plaatsing": ""}, headers=PANEL_HEADERS).content.decode()
        assert "Bij welke opdracht?" in content
        assert f'hx-get="{url}?opdracht={assignment.public_id}&amp;teamlid=nieuw-ingevuld"' in content
        button = tag(content, "nldd-button", "Nieuwe opdracht invoeren")
        assert f'hx-get="{url}?nieuwe-opdracht=&amp;daarna=plaatsing"' in button


class PickResultsTest(PickBase):
    def results(self, user=None, headers=None, **params):
        self.login(user)
        return self.client.get(PICK_URL, {"soort": "aanvraag", **params}, headers=headers or {})

    def test_business_manager_gets_the_rows(self):
        make_assignment("Zaaksysteem", self.org)
        response = self.results()
        assert response.status_code == 200
        self.assertContains(response, "<span>Zaaksysteem</span>")
        # Only the results: the search field stays in place while typing.
        self.assertNotContains(response, "<nldd-search-field")

    def test_unknown_or_missing_kind_is_a_bad_request(self):
        assert self.results(soort="onzin").status_code == 400
        self.login()
        assert self.client.get(PICK_URL).status_code == 400

    def test_search_filters_on_name_and_client(self):
        make_assignment("Zaaksysteem", self.org)
        make_assignment("Datalab", OrganizationUnit.objects.create(name="Rijkswaterstaat", label="RWS"))
        content = self.results(zoek="zaak").content.decode()
        assert "<span>Zaaksysteem</span>" in content
        assert "Datalab" not in content
        content = self.results(zoek="rws").content.decode()
        assert "<span>Datalab</span>" in content
        assert "Zaaksysteem" not in content

    def test_search_term_is_stripped(self):
        make_assignment("Zaaksysteem", self.org)
        self.assertContains(self.results(zoek="  zaak  "), "<span>Zaaksysteem</span>")

    def test_count_is_announced(self):
        make_assignment("Zaaksysteem", self.org)
        make_assignment("Zaakregistratie", self.org)
        self.assertContains(self.results(), 'data-announce="2 opdrachten"')
        self.assertContains(self.results(zoek="zaak"), 'data-announce="2 opdrachten gevonden"')
        self.assertContains(self.results(zoek="systeem"), 'data-announce="1 opdracht gevonden"')

    def test_no_match_with_term(self):
        make_assignment("Zaaksysteem", self.org)
        response = self.results(zoek="onbekend")
        self.assertContains(response, 'data-announce="Geen opdrachten gevonden"')
        self.assertContains(response, "Zoek op een andere naam of opdrachtgever. Of voer een nieuwe opdracht in.")
        self.assertNotContains(response, "<nldd-list-item")

    def test_nothing_running_without_term(self):
        make_assignment("Afgelopen", self.org, end=self.today - timedelta(days=1))
        response = self.results()
        self.assertContains(response, 'data-announce="Er lopen nu geen opdrachten"')
        self.assertNotContains(response, "Afgelopen")

    def test_more_than_the_limit(self):
        for i in range(21):
            make_assignment(f"Opdracht {i}", self.org)
        content = self.results().content.decode()
        assert content.count("<nldd-list-item") == 20
        assert 'data-announce="De eerste 20 van 21 opdrachten"' in content
        assert "De eerste 20 van 21 opdrachten. Zoek om de lijst kleiner te maken." in content

    def test_at_the_limit_shows_no_cut_off(self):
        for i in range(20):
            make_assignment(f"Opdracht {i}", self.org)
        content = self.results().content.decode()
        assert content.count("<nldd-list-item") == 20
        assert "De eerste" not in content
        assert 'data-announce="20 opdrachten"' in content

    def test_row_urls_on_the_page_behind_the_panel(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        bezetting = reverse("bezetting")
        response = self.results(
            soort="plaatsing",
            headers={"HX-Current-URL": f"https://testserver{bezetting}?merk=x&nieuwe-plaatsing=&collega=5"},
        )
        pid = assignment.public_id
        self.assertContains(response, f'hx-get="{bezetting}?merk=x&amp;opdracht={pid}&amp;teamlid=nieuw-ingevuld"')
        self.assertNotContains(response, "nieuwe-plaatsing")
        self.assertNotContains(response, "collega=5")

    def test_row_urls_fall_back_to_the_list(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        response = self.results()
        self.assertContains(response, f'hx-get="{LIST_URL}?opdracht={assignment.public_id}&amp;teamlid=nieuw-aanvraag"')


class PickResultsPermissionTest(PickBase):
    def get(self, user):
        self.client.force_login(user)
        return self.client.get(PICK_URL, {"soort": "aanvraag"})

    def test_business_manager_may(self):
        assert self.get(self.bm).status_code == 200

    def test_consultant_is_forbidden(self):
        assert self.get(self.consultant_user()).status_code == 403

    def test_user_admin_is_forbidden(self):
        assert self.get(self.user_admin_user()).status_code == 403

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_bare_application_admin_is_forbidden(self):
        assert self.get(make_staff_user()).status_code == 403

    def test_user_without_role_is_forbidden(self):
        assert self.get(self.no_role_user()).status_code == 403

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_application_admin_with_business_manager_role_may(self):
        assert self.get(grant_business_manager(make_staff_user())).status_code == 200


class SplitButtonTest(PickBase):
    def page(self, url=LIST_URL, user=None, params=None):
        self.login(user)
        response = self.client.get(url, params or {})
        assert response.status_code == 200
        return response.content.decode()

    def assert_split_button(self, content, base):
        split = re.search(r"<nldd-split-button\b[^>]*>", content)
        assert split, "split button missing"
        split = split.group(0)
        assert 'variant="primary"' in split
        assert 'text="Aanvraag toevoegen"' in split
        assert 'hx-trigger="action-click"' in split
        assert f'hx-get="{base}nieuwe-aanvraag="' in split
        assert 'hx-push-url="false"' in split
        menu = re.search(r"<nldd-split-button\b.*?</nldd-split-button>", content, re.DOTALL).group(0)
        placed = tag(menu, "nldd-menu-item", "Geplaatste consultant toevoegen")
        assert f'hx-get="{base}nieuwe-plaatsing="' in placed
        create = tag(menu, "nldd-menu-item", "Opdracht invoeren")
        assert f'hx-get="{base}nieuwe-opdracht="' in create
        # Placement first, then a divider, then the exception.
        assert menu.index(placed) < menu.index("<nldd-menu-divider") < menu.index(create)

    def assert_overflow_twins(self, content):
        overflow = re.findall(r'<nldd-menu-item slot="overflow"[^>]*>', content)
        texts = {}
        for item in overflow:
            text = re.search(r'text="([^"]*)"', item).group(1)
            texts[text] = item
        for text, param in (
            ("Aanvraag toevoegen", "nieuwe-aanvraag"),
            ("Geplaatste consultant toevoegen", "nieuwe-plaatsing"),
            ("Opdracht invoeren", "nieuwe-opdracht"),
        ):
            assert text in texts, f"overflow item {text!r} missing"
            assert 'hx-trigger="select"' in texts[text]
            assert f"{param}=" in texts[text]

    def test_business_manager_sees_the_split_button_on_aanvragen(self):
        content = self.page()
        self.assert_split_button(content, f"{LIST_URL}?")
        self.assert_overflow_twins(content)

    def test_split_button_keeps_the_page_filters(self):
        content = self.page(params={"zoek": "data"})
        self.assert_split_button(content, f"{LIST_URL}?zoek=data&amp;")

    def test_bezetting_has_the_same_split_button(self):
        url = reverse("bezetting")
        content = self.page(url)
        self.assert_split_button(content, f"{url}?")
        self.assert_overflow_twins(content)

    def test_without_the_permission_no_button(self):
        for user in (self.consultant_user(), self.user_admin_user(), self.no_role_user()):
            content = self.page(user=user)
            assert "<nldd-split-button" not in content, user.email
            assert "nieuwe-aanvraag" not in content, user.email
            assert "nieuwe-plaatsing" not in content, user.email

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_bare_application_admin_sees_no_button(self):
        content = self.page(user=make_staff_user())
        assert "<nldd-split-button" not in content

    def test_user_list_has_no_split_button(self):
        content = self.page(reverse("admin-users"), user=self.user_admin_user())
        assert "<nldd-split-button" not in content


class PickPanelPermissionTest(PickBase):
    """Without ``core.add_assignment`` the list shows without a panel: no 403,
    these are list pages."""

    def assert_no_panel(self, user):
        self.client.force_login(user)
        for param in ("nieuwe-aanvraag", "nieuwe-plaatsing"):
            response = self.client.get(LIST_URL, {param: ""})
            assert response.status_code == 200, (user.email, param)
            self.assertNotContains(response, "Bij welke opdracht?")

    def test_business_manager_gets_the_panel(self):
        self.client.force_login(self.bm)
        for param in ("nieuwe-aanvraag", "nieuwe-plaatsing"):
            self.assertContains(self.client.get(LIST_URL, {param: ""}), "Bij welke opdracht?")

    def test_consultant(self):
        self.assert_no_panel(self.consultant_user())

    def test_user_admin(self):
        self.assert_no_panel(self.user_admin_user())

    def test_user_without_role(self):
        self.assert_no_panel(self.no_role_user())

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_bare_application_admin(self):
        self.assert_no_panel(make_staff_user())

    def test_add_assignment_without_business_manager_role_sees_the_panel(self):
        # The gate is the permission; the rights on the chosen opdracht are the
        # team member sheet's to check.
        user = User.objects.create_user(email="los@rijksoverheid.nl")
        user.user_permissions.add(Permission.objects.get(codename="add_assignment"))
        self.client.force_login(user)
        self.assertContains(self.client.get(LIST_URL, {"nieuwe-aanvraag": ""}), "Bij welke opdracht?")


class MemberSheetBackUrlTest(PickBase):
    """The team member sheet says where Terug goes (``data-back-url``), so the
    label and the target agree however the sheet was reached."""

    def setUp(self):
        super().setUp()
        self.assignment = make_assignment("Zaaksysteem", self.org)

    def sheet(self, params, user=None):
        self.login(user)
        response = self.client.get(LIST_URL, params, headers=PANEL_HEADERS)
        assert response.status_code == 200
        return response.content.decode()

    def title_bar(self, content):
        return re.search(r"<nldd-top-title-bar\b[^>]*>", content).group(0)

    def test_add_sheet_goes_back_to_the_opdracht(self):
        pid = self.assignment.public_id
        bar = self.title_bar(self.sheet({"zoek": "data", "opdracht": pid, "teamlid": "nieuw-aanvraag"}))
        assert 'text="Aanvraag toevoegen"' in bar
        assert 'back-text="Zaaksysteem"' in bar
        assert f'data-back-url="{LIST_URL}?zoek=data&amp;opdracht={pid}"' in bar

    def test_sheet_from_the_aanvraag_panel_goes_back_there(self):
        service = add_request(self.assignment)
        pid, spid = self.assignment.public_id, service.public_id
        bar = self.title_bar(self.sheet({"opdracht": pid, "aanvraag": spid, "teamlid": spid}))
        assert 'back-text="Aanvraag"' in bar
        assert f'data-back-url="{LIST_URL}?opdracht={pid}&amp;aanvraag={spid}"' in bar

    def test_consultant_gets_the_plain_opdracht_panel(self):
        content = self.sheet(
            {"opdracht": self.assignment.public_id, "teamlid": "nieuw-aanvraag"}, user=self.consultant_user()
        )
        assert "data-back-url" not in content
        assert "Aanvraag toevoegen" not in content
