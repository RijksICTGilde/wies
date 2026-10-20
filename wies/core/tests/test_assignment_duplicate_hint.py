"""The hint on the create form that the opdracht may already exist.

Covers the matching rule (``find_running_assignments_for_client``), the team
summary in words, the ``assignment-duplicate-check`` endpoint per role, and the
"Toevoegen" URLs it shares with the opdracht panel (``_member_add_urls``).
"""

import re
from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from config.jinja2 import datum_nl
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    Placement,
    Service,
)
from wies.core.roles import ROLE_USER_ADMIN, setup_roles
from wies.core.services.assignments import find_running_assignments_for_client, team_summary_text
from wies.core.tests.role_helpers import (
    STAFF_EMAIL,
    grant_consultant,
    make_business_manager_user,
    make_staff_user,
)
from wies.core.tests.test_assignment_create import org_formset_data
from wies.rijksauth.models import User

URL = reverse("assignment-duplicate-check")


def make_assignment(name, organization=None, *, role="PRIMARY", start=None, end=None, source="wies", owner=None):
    assignment = Assignment.objects.create(name=name, start_date=start, end_date=end, source=source, owner=owner)
    if organization is not None:
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=organization, role=role)
    return assignment


def add_request(assignment):
    return Service.objects.create(assignment=assignment, source="wies")


def add_placement(assignment, colleague, *, start=None, end=None):
    service = Service.objects.create(assignment=assignment, source="wies")
    if start is None and end is None:
        return Placement.objects.create(service=service, colleague=colleague, source="wies")
    return Placement.objects.create(
        service=service,
        colleague=colleague,
        source="wies",
        period_source=Placement.PLACEMENT,
        specific_start_date=start,
        specific_end_date=end,
    )


class FindRunningAssignmentsForClientTest(TestCase):
    def setUp(self):
        self.today = timezone.now().date()
        self.org = OrganizationUnit.objects.create(name="Belastingdienst", label="Belastingdienst")
        self.other_org = OrganizationUnit.objects.create(name="Rijkswaterstaat", label="RWS")

    def find(self, start=None, end=None, **kwargs):
        return list(find_running_assignments_for_client(self.org, start, end, today=self.today, **kwargs))

    def test_same_primary_client_matches(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        assert self.find() == [assignment]

    def test_client_only_involved_does_not_match(self):
        make_assignment("Zaaksysteem", self.org, role="INVOLVED")
        assert self.find() == []

    def test_other_client_does_not_match(self):
        make_assignment("Zaaksysteem", self.other_org)
        assert self.find() == []

    def test_only_wies_assignments_match(self):
        # A role cannot be added to an opdracht from another system.
        make_assignment("Uit OTYS", self.org, source="otys")
        assert self.find() == []

    def test_ended_assignment_does_not_match(self):
        make_assignment(
            "Afgelopen", self.org, start=self.today - timedelta(days=60), end=self.today - timedelta(days=1)
        )
        assert self.find() == []

    def test_assignment_ending_today_still_runs(self):
        assignment = make_assignment("Laatste dag", self.org, end=self.today)
        assert self.find() == [assignment]

    def test_empty_end_date_counts_as_running(self):
        assignment = make_assignment("Doorlopend", self.org, start=self.today - timedelta(days=400))
        assert self.find() == [assignment]

    def test_new_start_after_existing_end_does_not_overlap(self):
        make_assignment("Loopt tot volgende maand", self.org, end=self.today + timedelta(days=30))
        assert self.find(start=self.today + timedelta(days=31)) == []

    def test_new_end_before_existing_start_does_not_overlap(self):
        make_assignment("Begint later", self.org, start=self.today + timedelta(days=60))
        assert self.find(end=self.today + timedelta(days=59)) == []

    def test_touching_periods_overlap(self):
        assignment = make_assignment(
            "Grens", self.org, start=self.today + timedelta(days=10), end=self.today + timedelta(days=30)
        )
        assert self.find(start=self.today + timedelta(days=30)) == [assignment]
        assert self.find(end=self.today + timedelta(days=10)) == [assignment]

    def test_empty_dates_on_either_side_are_open(self):
        no_dates = make_assignment("Zonder datums", self.org)
        far_future = make_assignment("Ver weg", self.org, start=self.today + timedelta(days=700))
        found = self.find(start=self.today + timedelta(days=800), end=self.today + timedelta(days=900))
        assert set(found) == {no_dates, far_future}
        # Without a period every running opdracht of the client matches.
        assert set(self.find()) == {no_dates, far_future}

    def test_newest_first(self):
        oldest = make_assignment("Oud", self.org)
        newest = make_assignment("Nieuw", self.org)
        middle = make_assignment("Midden", self.org)
        now = timezone.now()
        Assignment.objects.filter(pk=oldest.pk).update(created_at=now - timedelta(days=3))
        Assignment.objects.filter(pk=middle.pk).update(created_at=now - timedelta(days=2))
        Assignment.objects.filter(pk=newest.pk).update(created_at=now - timedelta(days=1))
        assert self.find() == [newest, middle, oldest]

    def test_exclude_public_ids(self):
        dismissed = make_assignment("Weggeklikt", self.org)
        kept = make_assignment("Blijft", self.org)
        assert self.find(exclude_public_ids=[dismissed.public_id]) == [kept]

    def test_excluded_client_never_matches(self):
        aivd = OrganizationUnit.objects.create(name="Algemene Inlichtingen- en Veiligheidsdienst")
        make_assignment("Geheim", aivd)
        assert list(find_running_assignments_for_client(aivd, None, None, today=self.today)) == []


class TeamSummaryTextTest(TestCase):
    def test_no_rows(self):
        assert team_summary_text([]) == "nog geen rollen"

    def test_singular(self):
        assert team_summary_text([{"placement": None}]) == "1 aanvraag"
        assert team_summary_text([{"placement": object()}]) == "1 plaatsing"

    def test_plural_and_mixed(self):
        rows = [{"placement": None}, {"placement": None}, {"placement": object()}]
        assert team_summary_text(rows) == "2 aanvragen, 1 plaatsing"
        assert team_summary_text([{"placement": object()}] * 2) == "2 plaatsingen"


class DuplicateCheckBase(TestCase):
    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.bm = make_business_manager_user()
        self.bm_colleague = Colleague.objects.get(user=self.bm)
        self.org = OrganizationUnit.objects.create(name="Belastingdienst Centraal", label="Belastingdienst")
        self.other_org = OrganizationUnit.objects.create(name="Rijkswaterstaat", label="RWS")
        self.consultant = Colleague.objects.create(name="Piet Consultant", email="piet@rijksoverheid.nl", source="wies")

    def post(self, orgs=None, user=None, headers=None, **data):
        self.client.force_login(user or self.bm)
        payload = org_formset_data([(self.org, "PRIMARY")] if orgs is None else orgs)
        payload.update(data)
        return self.client.post(URL, payload, headers=headers or {})

    @staticmethod
    def dismissed_value(response) -> str:
        match = re.search(r'name="dubbel_genegeerd" value="([^"]*)"', response.content.decode())
        assert match, "hidden dubbel_genegeerd input missing"
        return match.group(1)


class DuplicateCheckPermissionTest(DuplicateCheckBase):
    def test_business_manager_gets_the_hint(self):
        make_assignment("Zaaksysteem", self.org)
        response = self.post()
        assert response.status_code == 200
        self.assertContains(response, "Zaaksysteem")

    def test_consultant_is_forbidden(self):
        user = grant_consultant(User.objects.create_user(email="consultant@rijksoverheid.nl"))
        assert self.post(user=user).status_code == 403

    def test_user_admin_is_forbidden(self):
        user = User.objects.create_user(email="beheer@rijksoverheid.nl")
        user.groups.add(Group.objects.get(name=ROLE_USER_ADMIN))
        assert self.post(user=user).status_code == 403

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_bare_application_admin_is_forbidden(self):
        assert self.post(user=make_staff_user()).status_code == 403

    def test_user_without_role_is_forbidden(self):
        user = User.objects.create_user(email="niemand@rijksoverheid.nl")
        assert self.post(user=user).status_code == 403

    def test_get_is_not_allowed(self):
        self.client.force_login(self.bm)
        assert self.client.get(URL).status_code == 405


class DuplicateCheckViewTest(DuplicateCheckBase):
    def test_no_client_gives_empty_fragment_with_hidden_input(self):
        make_assignment("Zaaksysteem", self.org)
        response = self.post(orgs=[])
        assert response.status_code == 200
        assert self.dismissed_value(response) == ""
        self.assertNotContains(response, "nldd-banner")

    def test_no_primary_client_gives_empty_fragment(self):
        make_assignment("Zaaksysteem", self.org)
        response = self.post(orgs=[(self.org, "INVOLVED")])
        assert response.status_code == 200
        self.assertContains(response, 'name="dubbel_genegeerd"')
        self.assertNotContains(response, "Zaaksysteem")

    def test_unknown_or_malformed_client_gives_empty_fragment(self):
        make_assignment("Zaaksysteem", self.org)
        response = self.post(
            orgs=[], **{"org-TOTAL_FORMS": "1", "org-0-organization": "geen-uuid", "org-0-role": "PRIMARY"}
        )
        assert response.status_code == 200
        self.assertNotContains(response, "nldd-banner")

    def test_no_match_gives_empty_fragment(self):
        make_assignment("Elders", self.other_org)
        response = self.post()
        self.assertContains(response, 'name="dubbel_genegeerd"')
        self.assertNotContains(response, "nldd-banner")

    def test_match_shows_name_period_and_team(self):
        start, end = self.today - timedelta(days=30), self.today + timedelta(days=200)
        assignment = make_assignment("Zaaksysteem", self.org, start=start, end=end)
        add_request(assignment)
        add_request(assignment)
        add_placement(assignment, self.consultant)
        response = self.post()
        self.assertContains(response, "Er loopt al een opdracht bij Belastingdienst")
        self.assertContains(response, 'data-announce="Er loopt al een opdracht bij Belastingdienst"')
        self.assertContains(response, f"{datum_nl(start)} t/m {datum_nl(end)}")
        self.assertContains(response, "2 aanvragen, 1 plaatsing")
        self.assertContains(response, 'accessible-label="Teamlid toevoegen aan Zaaksysteem"')
        self.assertContains(response, "Hoort je aanvraag of plaatsing bij deze opdracht? Kies dan Toevoegen.")

    def test_period_variants(self):
        start = self.today - timedelta(days=5)
        end = self.today + timedelta(days=5)
        make_assignment("Alleen start", self.org, start=start)
        make_assignment("Alleen eind", self.org, end=end)
        response = self.post()
        content = response.content.decode()
        assert f"Vanaf {datum_nl(start)} · " in content
        assert f"t/m {datum_nl(end)} · " in content
        # More than one match: the plural heading and supporting text.
        assert "Er lopen al opdrachten bij Belastingdienst" in content
        assert "bij een van deze opdrachten? Kies dan Toevoegen bij die opdracht." in content

    def test_singular_and_empty_team(self):
        with_request = make_assignment("Met aanvraag", self.org)
        add_request(with_request)
        make_assignment("Leeg", self.org)
        response = self.post()
        self.assertContains(response, "1 aanvraag")
        self.assertNotContains(response, "1 aanvragen")
        self.assertContains(response, "nog geen rollen")

    def test_overlap_with_entered_dates(self):
        make_assignment("Loopt kort", self.org, end=self.today + timedelta(days=10))
        response = self.post(start_date=(self.today + timedelta(days=11)).isoformat())
        self.assertNotContains(response, "Loopt kort")
        response = self.post(start_date=(self.today + timedelta(days=5)).isoformat())
        self.assertContains(response, "Loopt kort")

    def test_ended_and_otys_assignments_are_left_out(self):
        make_assignment("Afgelopen", self.org, end=self.today - timedelta(days=1))
        make_assignment("Uit OTYS", self.org, source="otys")
        make_assignment("Betrokken", self.org, role="INVOLVED")
        response = self.post()
        self.assertNotContains(response, "nldd-banner")

    def test_invalid_date_counts_as_open(self):
        make_assignment("Doorlopend", self.org)
        response = self.post(start_date="31-02-2026", end_date="morgen")
        assert response.status_code == 200
        self.assertContains(response, "Doorlopend")

    def test_at_most_three_shown_plus_count(self):
        assignments = [make_assignment(f"Opdracht {i}", self.org) for i in range(5)]
        now = timezone.now()
        for i, assignment in enumerate(assignments):
            Assignment.objects.filter(pk=assignment.pk).update(created_at=now - timedelta(days=10 - i))
        response = self.post()
        content = response.content.decode()
        for shown in ("Opdracht 4", "Opdracht 3", "Opdracht 2"):
            assert f"<span>{shown}</span>" in content
        for hidden in ("Opdracht 1", "Opdracht 0"):
            assert f"<span>{hidden}</span>" not in content
        assert "En nog 2 andere lopende opdrachten bij Belastingdienst." in content
        # "Toch nieuwe opdracht invoeren" dismisses all five, not only the three on show.
        negeer = re.search(r'"negeer": "([^"]*)"', content).group(1)
        assert set(negeer.split(",")) == {str(a.public_id) for a in assignments}

    def test_one_more_is_singular(self):
        for i in range(4):
            make_assignment(f"Opdracht {i}", self.org)
        self.assertContains(self.post(), "En nog 1 andere lopende opdracht bij Belastingdienst.")

    def test_negeer_and_dubbel_genegeerd_leave_assignments_out(self):
        first = make_assignment("Eerste", self.org)
        second = make_assignment("Tweede", self.org)
        make_assignment("Derde", self.org)
        response = self.post(negeer=str(first.public_id), dubbel_genegeerd=str(second.public_id))
        self.assertNotContains(response, "Eerste")
        self.assertNotContains(response, "Tweede")
        self.assertContains(response, "Derde")
        assert set(self.dismissed_value(response).split(",")) == {str(first.public_id), str(second.public_id)}

    def test_dismissing_all_gives_empty_fragment_keeping_the_dismissed(self):
        only = make_assignment("Enige", self.org)
        response = self.post(negeer=str(only.public_id))
        self.assertNotContains(response, "nldd-banner")
        assert self.dismissed_value(response) == str(only.public_id)

    def test_malformed_public_ids_are_dropped(self):
        first = make_assignment("Eerste", self.org)
        response = self.post(negeer=f"geen-uuid,{first.public_id},", dubbel_genegeerd="123,,abc")
        assert response.status_code == 200
        self.assertNotContains(response, "Eerste")
        assert self.dismissed_value(response) == str(first.public_id)

    def test_menu_urls_on_page_behind_panel(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        response = self.post(
            headers={"HX-Current-URL": "https://testserver/plaatsingen/?zoek=data&nieuwe-opdracht=&collega=5"}
        )
        pid = assignment.public_id
        self.assertContains(response, f'hx-get="/plaatsingen/?zoek=data&amp;opdracht={pid}&amp;teamlid=nieuw-aanvraag"')
        self.assertContains(response, f'hx-get="/plaatsingen/?zoek=data&amp;opdracht={pid}&amp;teamlid=nieuw-ingevuld"')
        self.assertNotContains(response, "nieuwe-opdracht")
        self.assertNotContains(response, "collega=5")

    def test_menu_urls_fall_back_to_assignment_list(self):
        assignment = make_assignment("Zaaksysteem", self.org)
        response = self.post()
        list_url = reverse("assignment-list")
        pid = assignment.public_id
        self.assertContains(response, f'hx-get="{list_url}?opdracht={pid}&amp;teamlid=nieuw-aanvraag"')
        self.assertContains(response, f'hx-get="{list_url}?opdracht={pid}&amp;teamlid=nieuw-ingevuld"')


class DuplicateCheckVisibilityTest(DuplicateCheckBase):
    """The team summary counts only rows the viewer may see (``visible_service_rows``)."""

    def setUp(self):
        super().setUp()
        assignment = make_assignment("Zaaksysteem", self.org)
        add_request(assignment)
        add_placement(
            assignment, self.consultant, start=self.today - timedelta(days=90), end=self.today - timedelta(days=1)
        )

    def test_business_manager_counts_ended_placement(self):
        self.assertContains(self.post(), "1 aanvraag, 1 plaatsing")

    def test_add_assignment_without_bm_role_does_not_count_ended_placement(self):
        user = User.objects.create_user(email="los@rijksoverheid.nl")
        user.user_permissions.add(Permission.objects.get(codename="add_assignment"))
        response = self.post(user=user)
        assert response.status_code == 200
        self.assertContains(response, "1 aanvraag")
        self.assertNotContains(response, "1 aanvraag, 1 plaatsing")


class CreatePanelMountTest(DuplicateCheckBase):
    def test_create_panel_has_hint_mount(self):
        self.client.force_login(self.bm)
        response = self.client.get(
            reverse("assignment-list"),
            {"nieuwe-opdracht": ""},
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        content = response.content.decode()
        mount = re.search(r'<div id="assignment-duplicate-hint"[^>]*>', content)
        assert mount, "hint mount point missing"
        assert f'hx-post="{URL}"' in mount.group(0)
        assert 'hx-include="closest form"' in mount.group(0)
        # Only the fields that can change the outcome set the check off; a blur
        # of the name would otherwise read the banner out again.
        trigger = re.search(r'hx-trigger="([^"]*)"', mount.group(0)).group(1)
        assert "change from:#assignment-org-inputs" in trigger
        assert "change from:[name=start_date]" in trigger
        assert "change from:[name=end_date]" in trigger
        assert "closest form" not in trigger

    def test_dismissed_opdrachten_survive_a_failed_submit(self):
        self.client.force_login(self.bm)
        dismissed = make_assignment("Weggeklikt", self.org)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {"name": "", "dubbel_genegeerd": f"{dismissed.public_id},geen-uuid"},
            headers={"hx-request": "true"},
        )
        content = response.content.decode()
        assert re.search(rf'name="dubbel_genegeerd"\s+value="{dismissed.public_id}"', content)
        assert "geen-uuid" not in content

    def test_menu_items_send_no_form_and_push_no_url(self):
        """The mount's hx-include would put the whole form in the URL, and
        side_panel.js pushes the clean URL itself."""
        self.client.force_login(self.bm)
        make_assignment("Zaaksysteem", self.org)
        content = self.client.post(URL, org_formset_data([(self.org, "PRIMARY")])).content.decode()
        items = re.findall(r"<nldd-menu-item[^>]*>", content)
        # One menu per button: the text button above md, the icon button below.
        assert len(items) == 4
        for item in items:
            assert 'hx-params="none"' in item
            assert 'hx-push-url="false"' in item


class AssignmentPanelMemberAddUrlsTest(DuplicateCheckBase):
    """Regression: the panel's "Toevoegen" menu now builds its URLs via _member_add_urls."""

    def test_panel_member_add_urls_keep_filters_and_drop_panel_params(self):
        assignment = make_assignment("Zaaksysteem", self.org, owner=self.bm_colleague)
        self.client.force_login(self.bm)
        response = self.client.get(
            reverse("assignment-list"), {"zoek": "data", "opdracht": assignment.public_id, "uitgeklapt": "x"}
        )
        assert response.status_code == 200
        base = reverse("assignment-list")
        pid = assignment.public_id
        self.assertContains(response, f'hx-get="{base}?zoek=data&amp;opdracht={pid}&amp;teamlid=nieuw-aanvraag"')
        self.assertContains(response, f'hx-get="{base}?zoek=data&amp;opdracht={pid}&amp;teamlid=nieuw-ingevuld"')
