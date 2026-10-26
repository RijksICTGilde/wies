import html as html_module
import json
import re
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    OrganizationUnitRole,
    Placement,
    Service,
    Skill,
)
from wies.core.querysets import annotate_service_dates
from wies.core.tests.role_helpers import grant_consultant, make_business_manager_user, make_other_business_manager_user
from wies.core.views import AssignmentListView

User = get_user_model()

# The aanvraag public_id in a card's href; the hx-get repeats it, so only href.
CARD_AANVRAAG_RE = re.compile(r'<nldd-card[^>]*\shref="[^"]*aanvraag=([0-9a-f-]{36})')


class AssignmentListViewTest(TestCase):
    """Tests for the assignment list (aanvragen cards) view."""

    def setUp(self):
        self.client = Client()
        self.list_url = reverse("assignment-list")

        self.auth_user = User.objects.create_user(
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )

        self.org = OrganizationUnit.objects.create(name="Test Org", label="Test Org")
        self.org2 = OrganizationUnit.objects.create(name="Other Org", label="Other Org")
        self.skill = Skill.objects.create(name="Python Developer")
        self.skill2 = Skill.objects.create(name="Data Engineer")

        # Has an unfilled OPEN service, so it should appear.
        self.vacancy = Assignment.objects.create(
            name="Open Aanvraag",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            source="wies",
        )
        AssignmentOrganizationUnit.objects.create(assignment=self.vacancy, organization=self.org)
        self.vacancy_service = Service.objects.create(
            assignment=self.vacancy,
            description="Service 1",
            skill=self.skill,
            status="OPEN",
            source="wies",
        )

        # Every service is filled, so it should not appear.
        self.filled = Assignment.objects.create(
            name="Ingevulde Opdracht",
            source="wies",
        )
        AssignmentOrganizationUnit.objects.create(assignment=self.filled, organization=self.org)
        filled_service = Service.objects.create(
            assignment=self.filled,
            description="Filled Service",
            skill=self.skill,
            status="OPEN",
            source="wies",
        )
        colleague = Colleague.objects.create(name="Test Colleague", email="col@test.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=filled_service, source="wies")

    def test_login_required(self):
        response = self.client.get(self.list_url)
        assert response.status_code == 302
        assert "/inloggen/" in response.url

    def test_shows_only_aanvraag_assignments(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Open Aanvraag" in content
        assert "Ingevulde Opdracht" not in content

    def test_search_filter(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"zoek": "Open Aanvraag"})
        content = response.content.decode()
        assert "Open Aanvraag" in content

        response = self.client.get(self.list_url, {"zoek": "nonexistent"})
        content = response.content.decode()
        assert "Open Aanvraag" not in content

    def test_filter_by_rol(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"rol": str(self.skill.public_id)})
        content = response.content.decode()
        assert "Open Aanvraag" in content

        response = self.client.get(self.list_url, {"rol": str(self.skill2.public_id)})
        content = response.content.decode()
        assert "Open Aanvraag" not in content

    def test_filter_by_org(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"org_self": str(self.org.public_id)})
        content = response.content.decode()
        assert "Open Aanvraag" in content

        response = self.client.get(self.list_url, {"org_self": str(self.org2.public_id)})
        content = response.content.decode()
        assert "Open Aanvraag" not in content

    def test_htmx_filter_returns_card_container(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, headers={"hx-request": "true"})
        assert response.status_code == 200
        content = response.content.decode()
        # The partial returns the results line (the swap target) plus the card
        # grid as an out-of-band swap.
        assert 'id="results"' in content
        assert 'id="assignment-card-grid"' in content
        assert 'hx-swap-oob="outerHTML"' in content

    def test_htmx_pagina_returns_card_rows(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"pagina": "1"}, headers={"hx-request": "true"})
        assert response.status_code == 200

    def test_side_panel_with_opdracht_param(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"opdracht": str(self.vacancy.id)})
        assert response.status_code == 200
        content = response.content.decode()
        assert "side_panel" in content

    def test_the_menu_marks_aanvragen_as_current(self):
        self.client.force_login(self.auth_user)
        body = self.client.get(self.list_url).content.decode()
        assert re.search(r'<nldd-menu-bar-item text="Aanvragen" href="/aanvragen/"\s+current>', body)

    def test_old_opdrachten_url_redirects_with_its_filters(self):
        self.client.force_login(self.auth_user)
        response = self.client.get("/opdrachten/?zoek=Data&pagina=2")
        assert response.status_code == 302
        assert response["Location"] == "/aanvragen/?zoek=Data&pagina=2"

    def test_side_panel_opens_for_any_assignment(self):
        """An opdracht without an open aanvraag has no card, but its panel still
        opens on the list via ?opdracht=."""
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"opdracht": str(self.filled.public_id)})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="panel-title"' in content
        assert "Ingevulde Opdracht" in content

    def test_query_count_does_not_grow_with_the_cards(self):
        """The cards read the opdracht, the role and the first opdrachtgever
        from the select_related and the prefetch, not one query per card."""
        self.client.force_login(self.auth_user)

        def add_aanvragen(count):
            for i in range(count):
                assignment = Assignment.objects.create(name=f"Extra {i}", source="wies")
                AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=self.org2)
                Service.objects.create(assignment=assignment, skill=self.skill2, status="OPEN", source="wies")

        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.client.get(self.list_url, headers={"hx-request": "true"})
            return len(captured)

        add_aanvragen(2)
        few = queries()
        add_aanvragen(10)
        assert queries() == few

    def test_concept_services_not_shown(self):
        """An assignment with only CONCEPT services does not appear."""
        concept_assignment = Assignment.objects.create(name="Concept Opdracht", source="wies")
        Service.objects.create(
            assignment=concept_assignment, description="Concept Service", status="CONCEPT", source="wies"
        )
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url)
        content = response.content.decode()
        assert "Concept Opdracht" not in content

    def test_all_open_services_filled_not_shown(self):
        """An assignment whose OPEN services are all filled does not appear."""
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url)
        content = response.content.decode()
        assert "Ingevulde Opdracht" not in content

    def test_mix_of_filled_and_unfilled_services(self):
        """An assignment with both filled and unfilled OPEN services appears."""
        mix_assignment = Assignment.objects.create(name="Mix Opdracht", source="wies")
        filled_svc = Service.objects.create(
            assignment=mix_assignment, description="Filled", skill=self.skill, status="OPEN", source="wies"
        )
        colleague = Colleague.objects.create(name="Mix Col", email="mix@test.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=filled_svc, source="wies")
        Service.objects.create(
            assignment=mix_assignment, description="Unfilled", skill=self.skill2, status="OPEN", source="wies"
        )

        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url)
        content = response.content.decode()
        assert "Mix Opdracht" in content

    def _filter_groups(self, query_params=None):
        """Builds the view's ``filter_groups`` context without rendering a template.

        Jinja2 does not populate ``response.context``, so the view is driven
        directly. ``created_at`` is nulled to mirror fixture-loaded assignments
        (``auto_now_add`` does not fire on ``loaddata``): distinct timestamps in
        the ``order_by`` SELECT otherwise hid the count collapse.
        """
        Assignment.objects.update(created_at=None)
        request = RequestFactory().get(self.list_url, query_params or {})
        request.user = self.auth_user
        view = AssignmentListView()
        view.request = request
        view.kwargs = {}
        view.object_list = view.get_queryset()
        return view.get_context_data()["filter_groups"]

    def _org_count(self, groups, org):
        """Returns the sidebar 'org' facet count for ``org``."""
        for group in groups:
            if group["name"] == "organisatie":
                for option in group["top_options"]:
                    if option["param"] == "org" and option["value"] == str(org.public_id):
                        return option["count"]
        return None

    def _rol_count(self, groups, skill):
        """Returns the sidebar 'rol' facet count for ``skill``."""
        for group in groups:
            if group["name"] == "rol":
                for option in group["options"]:
                    if option["value"] == str(skill.public_id):
                        return option["count"]
        return None

    def _open_aanvraag(self, name, org, skill):
        """Creates an aanvraag on ``org`` with one unfilled OPEN service for ``skill``."""
        assignment = Assignment.objects.create(name=name, source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        Service.objects.create(
            assignment=assignment, description=f"{name} service", skill=skill, status="OPEN", source="wies"
        )
        return assignment

    def _two_org_aanvraag(self):
        """One open aanvraag on an opdracht with two opdrachtgevers whose names
        both match "Zoekorg". Returns ``(org_a, org_b, service)``."""
        org_a = OrganizationUnit.objects.create(name="Zoekorg Een", label="Zoekorg Een")
        org_b = OrganizationUnit.objects.create(name="Zoekorg Twee", label="Zoekorg Twee")
        assignment = Assignment.objects.create(name="Gedeelde Opdracht", source="wies")
        # Only one PRIMARY org per assignment is allowed, so the second is INVOLVED.
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=org_a, role=OrganizationUnitRole.PRIMARY
        )
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=org_b, role=OrganizationUnitRole.INVOLVED
        )
        service = Service.objects.create(
            assignment=assignment, description="svc", skill=self.skill2, status="OPEN", source="wies"
        )
        return org_a, org_b, service

    def test_org_count_does_not_collapse_multiple_aanvragen(self):
        """Two aanvragen on the same org count as 2, not 1.

        Regression: ``SELECT DISTINCT organizations.id`` collapsed both aanvragen
        into one row, so the sidebar showed 1 while the filter returned 2.
        """
        self._open_aanvraag("Second Aanvraag", self.org, self.skill)

        groups = self._filter_groups()
        assert self._org_count(groups, self.org) == 2

    def test_excluded_org_hidden_from_list_and_quick_filters(self):
        """Intelligence-service orgs are hidden from the aanvragen list and its
        org quick-filters, matching how the plaatsingen list already hides them.

        Regression: AssignmentListView never excluded ``get_excluded_org_ids``,
        so an excluded org could surface as a list card and a top-N quick filter.
        """
        aivd = OrganizationUnit.objects.create(
            name="Algemene Inlichtingen- en Veiligheidsdienst",
            label="AIVD",
        )
        self._open_aanvraag("Geheime Aanvraag", aivd, self.skill)

        # Not in the rendered list.
        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        assert "Geheime Aanvraag" not in content

        # Not offered as an org quick-filter, and if it were it would count 0.
        groups = self._filter_groups()
        assert self._org_count(groups, aivd) is None

    def test_rol_count_does_not_collapse_multiple_aanvragen(self):
        """Two aanvragen sharing a skill count as 2, not 1.

        Same ``SELECT DISTINCT services.skill_id`` collapse as the org count.
        """
        self._open_aanvraag("Second Aanvraag", self.org, self.skill)

        groups = self._filter_groups()
        assert self._rol_count(groups, self.skill) == 2

    def test_rol_count_only_counts_open_unfilled_services(self):
        """A rol count equals what selecting that rol returns.

        Selecting a rol matches assignments with an OPEN *unfilled* service for
        that skill, so the count must ignore filled and CONCEPT services.
        """
        assignment = self._open_aanvraag("Mixed Services", self.org2, self.skill2)
        # Filled, so selecting self.skill would not return this assignment.
        filled_svc = Service.objects.create(
            assignment=assignment, description="filled", skill=self.skill, status="OPEN", source="wies"
        )
        colleague = Colleague.objects.create(name="Col", email="mix-col@test.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=filled_svc, source="wies")
        # CONCEPT, so also not selectable.
        Service.objects.create(
            assignment=assignment, description="concept", skill=self.skill, status="CONCEPT", source="wies"
        )

        groups = self._filter_groups()
        assert self._rol_count(groups, self.skill) == 1
        assert self._rol_count(groups, self.skill2) == 1

    def test_rol_count_counts_each_aanvraag_for_the_same_skill(self):
        """Two open aanvragen for the same rol on one opdracht count 2.

        The list shows a card per aanvraag, so the count follows the cards.
        """
        assignment = Assignment.objects.create(name="Two Same-Skill Services", source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=self.org2)
        Service.objects.create(
            assignment=assignment, description="svc one", skill=self.skill2, status="OPEN", source="wies"
        )
        Service.objects.create(
            assignment=assignment, description="svc two", skill=self.skill2, status="OPEN", source="wies"
        )

        groups = self._filter_groups()
        assert self._rol_count(groups, self.skill2) == 2

    def test_org_count_counts_each_aanvraag_on_one_opdracht(self):
        """Two aanvragen on one opdracht count 2 for its opdrachtgever, and a
        rol filter narrows that to the aanvragen of that rol (cross-filter)."""
        fanout_org = OrganizationUnit.objects.create(name="Fanout Org", label="Fanout Org")
        assignment = Assignment.objects.create(name="Two Service Aanvraag", source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=fanout_org)
        Service.objects.create(
            assignment=assignment, description="svc a", skill=self.skill, status="OPEN", source="wies"
        )
        Service.objects.create(
            assignment=assignment, description="svc b", skill=self.skill2, status="OPEN", source="wies"
        )

        both = {"rol": [str(self.skill.public_id), str(self.skill2.public_id)]}
        assert self._org_count(self._filter_groups(both), fanout_org) == 2
        assert self._org_count(self._filter_groups({"rol": str(self.skill2.public_id)}), fanout_org) == 1

    def test_org_count_not_inflated_by_a_second_opdrachtgever(self):
        """One aanvraag on an opdracht with two opdrachtgevers counts 1 for each,
        also when the search matches both (the M2M join must not fan out)."""
        org_a, org_b, _service = self._two_org_aanvraag()

        for params in ({}, {"zoek": "Zoekorg"}):
            with self.subTest(params=params):
                groups = self._filter_groups(params)
                assert self._org_count(groups, org_a) == 1
                assert self._org_count(groups, org_b) == 1

    def test_rol_count_not_inflated_by_org_fanout(self):
        """One aanvraag on two orgs counts once per skill.

        With an org filter active the ``organizations`` join fans the row out to 2,
        so the rol count must stay 1.
        """
        org_a = OrganizationUnit.objects.create(name="Fanout Org A", label="Fanout Org A")
        org_b = OrganizationUnit.objects.create(name="Fanout Org B", label="Fanout Org B")
        assignment = Assignment.objects.create(name="Two Org Aanvraag", source="wies")
        # Only one PRIMARY org per assignment is allowed, so the second is INVOLVED.
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=org_a, role=OrganizationUnitRole.PRIMARY
        )
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=org_b, role=OrganizationUnitRole.INVOLVED
        )
        Service.objects.create(
            assignment=assignment, description="svc", skill=self.skill2, status="OPEN", source="wies"
        )

        # An org filter on both orgs matches via organizations and fans out.
        groups = self._filter_groups({"org_self": [str(org_a.public_id), str(org_b.public_id)]})
        assert self._rol_count(groups, self.skill2) == 1

    def _modal_org_count(self, org, query_params=None):
        """The count the opdrachtgever modal shows for ``org`` on Aanvragen.

        Drives the real endpoint and reads the ``json_script`` payload back:
        these templates are Jinja2, so there is no ``response.context``.
        """
        self.client.force_login(self.auth_user)
        response = self.client.get(
            "/client-modal/", {"count_mode": "open_assignments", "ndd": "1", **(query_params or {})}
        )
        assert response.status_code == 200
        raw = response.content.decode().split('<script id="client-data" type="application/json">')[1]
        nodes = json.loads(html_module.unescape(raw.split("</script>")[0]))
        while nodes:
            node = nodes.pop()
            if node["id"] == str(org.public_id):
                return node["nr_of_placements"]
            nodes.extend(node.get("children", []))
        return None

    def test_modal_org_count_does_not_collapse_multiple_aanvragen(self):
        """The org modal counts every aanvraag on an org, rather than collapsing to 1."""
        self._open_aanvraag("Second Aanvraag", self.org, self.skill)

        assert self._modal_org_count(self.org) == 2

    def test_modal_org_count_counts_each_aanvraag_on_one_opdracht(self):
        """Same as the sidebar: two aanvragen on one opdracht count 2, and the
        rol filter narrows the count to that rol."""
        fanout_org = OrganizationUnit.objects.create(name="Modal Fanout Org", label="Modal Fanout Org")
        assignment = Assignment.objects.create(name="Two Service Aanvraag", source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=fanout_org)
        Service.objects.create(
            assignment=assignment, description="svc a", skill=self.skill, status="OPEN", source="wies"
        )
        Service.objects.create(
            assignment=assignment, description="svc b", skill=self.skill2, status="OPEN", source="wies"
        )

        assert self._modal_org_count(fanout_org) == 2
        assert self._modal_org_count(fanout_org, {"rol": str(self.skill2.public_id)}) == 1

    def test_modal_org_count_not_inflated_by_a_second_opdrachtgever(self):
        """One aanvraag on two opdrachtgevers counts 1 for each in the modal."""
        org_a, org_b, _service = self._two_org_aanvraag()

        assert self._modal_org_count(org_a, {"zoek": "Zoekorg"}) == 1
        assert self._modal_org_count(org_b, {"zoek": "Zoekorg"}) == 1

    def test_filter_by_rol_excludes_filled_services(self):
        """The rol filter matches only assignments with an OPEN unfilled service."""
        mix_assignment = Assignment.objects.create(name="Mix Opdracht", source="wies")
        filled_svc = Service.objects.create(
            assignment=mix_assignment, description="Filled", skill=self.skill, status="OPEN", source="wies"
        )
        colleague = Colleague.objects.create(name="Col", email="col2@test.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=filled_svc, source="wies")
        Service.objects.create(
            assignment=mix_assignment, description="Unfilled", skill=self.skill2, status="OPEN", source="wies"
        )

        self.client.force_login(self.auth_user)

        response = self.client.get(self.list_url, {"rol": str(self.skill2.public_id)})
        content = response.content.decode()
        assert "Mix Opdracht" in content

        response = self.client.get(self.list_url, {"rol": str(self.skill.public_id)})
        content = response.content.decode()
        assert "Mix Opdracht" not in content

    # --- One card per aanvraag -------------------------------------------

    def _aanvraag(self, assignment, skill=None, **fields):
        """An open, unfilled aanvraag on ``assignment``."""
        fields.setdefault("description", "")
        return Service.objects.create(assignment=assignment, skill=skill, status="OPEN", source="wies", **fields)

    def _card_ids(self, params=None, **request_kwargs):
        """The aanvraag public_ids of the cards on the list, in order, duplicates kept."""
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, params or {}, **request_kwargs)
        assert response.status_code == 200
        return CARD_AANVRAAG_RE.findall(response.content.decode())

    def test_one_card_per_open_aanvraag(self):
        """Two open aanvragen on one opdracht are two cards, both naming the opdracht."""
        assignment = Assignment.objects.create(name="Twee Rollen Opdracht", source="wies")
        first = self._aanvraag(assignment, self.skill)
        second = self._aanvraag(assignment, self.skill2)

        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        assert sorted(CARD_AANVRAAG_RE.findall(content)) == sorted(
            [str(first.public_id), str(second.public_id), str(self.vacancy_service.public_id)]
        )
        assert content.count('<p class="wies-text-secondary">Twee Rollen Opdracht</p>') == 2
        assert "<h2>Python Developer</h2>" in content
        assert "<h2>Data Engineer</h2>" in content

    def test_filled_and_not_open_aanvragen_are_not_listed(self):
        """Only OPEN unfilled roles are cards: not a filled one, not a CONCEPT one,
        even when they sit on the same opdracht as an open aanvraag."""
        assignment = Assignment.objects.create(name="Gemengde Opdracht", source="wies")
        open_service = self._aanvraag(assignment, self.skill)
        filled = self._aanvraag(assignment, self.skill2)
        colleague = Colleague.objects.create(name="Bezet", email="bezet@test.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=filled, source="wies")
        concept = Service.objects.create(
            assignment=assignment, description="", skill=self.skill2, status="CONCEPT", source="wies"
        )

        ids = self._card_ids()
        assert str(open_service.public_id) in ids
        assert str(filled.public_id) not in ids
        assert str(concept.public_id) not in ids

    def test_assignment_without_aanvraag_is_not_listed(self):
        """An opdracht without any role has no card (it used to, as "no roles yet")."""
        Assignment.objects.create(name="Lege Opdracht", source="wies")
        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        assert "Lege Opdracht" not in content
        assert CARD_AANVRAAG_RE.findall(content) == [str(self.vacancy_service.public_id)]

    def test_two_matching_opdrachtgevers_give_one_card(self):
        """An opdracht with two opdrachtgevers that both match the search or the
        org filter still gives one card per aanvraag."""
        org_a, org_b, service = self._two_org_aanvraag()

        for params in (
            {"zoek": "Zoekorg"},
            {"org_self": [str(org_a.public_id), str(org_b.public_id)]},
            {"org": [str(org_a.public_id), str(org_b.public_id)]},
        ):
            with self.subTest(params=params):
                assert self._card_ids(params) == [str(service.public_id)]

    def test_card_content(self):
        org = OrganizationUnit.objects.create(name="Ministerie van Kaarten", label="Kaartenministerie")
        assignment = Assignment.objects.create(name="Kaartopdracht", source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        skill = Skill.objects.create(name="Kwartiermaker")
        service = self._aanvraag(
            assignment,
            skill,
            hours_per_week=24,
            location="Den Haag",
            request_description="Begin van de tekst. " + "vulling " * 30 + "SLOTZIN",
            starts_immediately=True,
            duration_months=12,
        )

        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        panel_url = f"{self.list_url}?opdracht={assignment.public_id}&amp;aanvraag={service.public_id}"
        assert f'href="{panel_url}"' in content
        assert f'hx-get="{panel_url}"' in content
        assert 'accessible-label="Kwartiermaker bij Kaartopdracht"' in content
        assert "<h2>Kwartiermaker</h2>" in content
        assert '<p class="wies-text-secondary">Kaartopdracht</p>' in content
        assert 'text="24 uur per week"' in content
        # "Wie we zoeken" stays in the panel: on the card it mostly repeated
        # the role.
        assert "Begin van de tekst." not in content
        assert 'text="Kaartenministerie"' in content
        assert 'text="Den Haag"' in content
        assert 'text="Per direct, voor 1 jaar"' in content

    def test_card_without_skill_hours_or_period(self):
        assignment = Assignment.objects.create(name="Kale Opdracht", source="wies")
        self._aanvraag(assignment)

        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url, {"zoek": "Kale Opdracht"}).content.decode()
        assert "<h2>Rol niet ingevuld</h2>" in content
        assert 'accessible-label="Aanvraag zonder rol bij Kale Opdracht"' in content
        assert 'text="Geen periode opgegeven"' in content
        assert "uur per week" not in content

    def test_card_period_follows_the_opdracht(self):
        """A role that follows the opdracht shows the opdracht's dates."""
        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        assert 'text="1 jan 2025 t/m 31 dec 2025"' in content

    def test_card_opens_the_aanvraag_panel(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(
            self.list_url,
            {"opdracht": str(self.vacancy.public_id), "aanvraag": str(self.vacancy_service.public_id)},
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 200
        self.assertContains(response, 'text="Aanvraag: Python Developer"')

    # --- Search ------------------------------------------------------------

    def test_search_matches_aanvraag_opdracht_and_opdrachtgever_fields(self):
        """Role, standplaats and "Wie we zoeken" match one aanvraag; the opdracht
        and opdrachtgever fields match every aanvraag on that opdracht. "Taken"
        (``description``) is cv text and is not searched."""
        org = OrganizationUnit.objects.create(
            name="Ministerie van Testzaken", label="Testzakenlabel", abbreviations=["MVTZ"]
        )
        assignment = Assignment.objects.create(
            name="Opdracht Alfa", extra_info="Omschrijving met zeppelin", source="wies"
        )
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        target = self._aanvraag(
            assignment,
            Skill.objects.create(name="Kwartiermaker"),
            location="Zwolle",
            request_description="Ervaring met blockchain",
            description="Taken: tuinieren",
        )
        sibling = self._aanvraag(assignment, self.skill2)
        only_target = [str(target.public_id)]
        whole_opdracht = sorted([str(target.public_id), str(sibling.public_id)])

        for term, expected in (
            ("kwartiermaker", only_target),
            ("zwolle", only_target),
            ("blockchain", only_target),
            ("Opdracht Alfa", whole_opdracht),
            ("zeppelin", whole_opdracht),
            ("Ministerie van Testzaken", whole_opdracht),
            ("Testzakenlabel", whole_opdracht),
            ("MVTZ", whole_opdracht),
            ("tuinieren", []),
        ):
            with self.subTest(term=term):
                assert sorted(self._card_ids({"zoek": term})) == expected

    # --- Beschikbaar vanaf ---------------------------------------------------

    def test_beschikbaar_vanaf(self):
        """Per direct, undated and already started aanvragen always stay; one
        that starts later only when its effective start is on or after the
        date, whether it follows the opdracht or has its own period."""
        today = timezone.now().date()
        soon, later = today + timedelta(days=30), today + timedelta(days=150)
        early = Assignment.objects.create(name="Vroeg", start_date=soon, source="wies")
        late = Assignment.objects.create(name="Laat", start_date=later, source="wies")
        started = Assignment.objects.create(name="Loopt al", start_date=today - timedelta(days=100), source="wies")
        undated = Assignment.objects.create(name="Zonder datum", source="wies")
        services = {
            "per_direct": self._aanvraag(early, starts_immediately=True),
            "no_date": self._aanvraag(undated),
            "started": self._aanvraag(started),
            "follows_early": self._aanvraag(early),
            "follows_late": self._aanvraag(late),
            # Own period opposite to the opdracht's, so the wrong source fails.
            "own_late": self._aanvraag(early, period_source="SERVICE", specific_start_date=later),
            "own_early": self._aanvraag(late, period_source="SERVICE", specific_start_date=soon),
            "setup_vacancy": self.vacancy_service,  # follows its opdracht, started in 2025
        }

        def ids(*names):
            return sorted(str(services[name].public_id) for name in names)

        always = ("per_direct", "no_date", "started", "setup_vacancy")
        for vanaf, expected in (
            (soon + timedelta(days=1), ids(*always, "follows_late", "own_late")),
            (later, ids(*always, "follows_late", "own_late")),
            (soon, ids(*always, "follows_early", "follows_late", "own_late", "own_early")),
        ):
            with self.subTest(vanaf=vanaf):
                assert sorted(self._card_ids({"beschikbaar_vanaf": vanaf.isoformat()})) == expected

        # An invalid date filters nothing and gets no chip (it used to 500 on
        # the chip, which formats the value as a date).
        assert sorted(self._card_ids({"beschikbaar_vanaf": "geen-datum"})) == ids(*services)

    # --- Filters and counts on aanvraag level -------------------------------

    def test_rol_filter_shows_only_the_aanvragen_of_that_rol(self):
        """The other aanvraag on the same opdracht is not a card under the filter."""
        assignment = Assignment.objects.create(name="Twee Rollen", source="wies")
        python = self._aanvraag(assignment, self.skill)
        data = self._aanvraag(assignment, self.skill2)

        ids = self._card_ids({"rol": str(self.skill2.public_id)})
        assert ids == [str(data.public_id)]
        assert str(python.public_id) not in ids

    def test_rol_count_follows_the_org_filter(self):
        """Cross-filter: the rol count counts only the aanvragen at the selected org."""
        assignment = self._open_aanvraag("Org2 Aanvraag", self.org2, self.skill)
        self._aanvraag(assignment, self.skill)

        assert self._rol_count(self._filter_groups(), self.skill) == 3
        assert self._rol_count(self._filter_groups({"org_self": str(self.org2.public_id)}), self.skill) == 2

    def _standplaats_options(self, groups):
        """The sidebar 'standplaats' options as {value: (label, count)}."""
        (group,) = [g for g in groups if g["name"] == "standplaats"]
        return {o["value"]: (o["label"], o["count"]) for o in group["options"] if o["value"]}

    def test_standplaats_filter_shows_only_the_aanvragen_there(self):
        assignment = Assignment.objects.create(name="Twee Plekken", source="wies")
        utrecht = self._aanvraag(assignment, self.skill, location="Utrecht")
        self._aanvraag(assignment, self.skill, location="Den Haag")

        assert self._card_ids({"standplaats": "utrecht"}) == [str(utrecht.public_id)]

    def test_standplaats_ignores_case_and_spaces(self):
        """Free text: "Den Haag" and "den haag " are one option and one filter."""
        assignment = Assignment.objects.create(name="Spelling", source="wies")
        first = self._aanvraag(assignment, self.skill, location="Den Haag")
        second = self._aanvraag(assignment, self.skill, location="den haag ")

        options = self._standplaats_options(self._filter_groups())
        assert options == {"den haag": ("Den Haag", 2)}
        assert sorted(self._card_ids({"standplaats": "Den Haag"})) == sorted(
            [str(first.public_id), str(second.public_id)]
        )

    def test_standplaats_count_follows_the_rol_filter(self):
        assignment = Assignment.objects.create(name="Telling", source="wies")
        self._aanvraag(assignment, self.skill, location="Utrecht")
        self._aanvraag(assignment, self.skill2, location="Utrecht")

        assert self._standplaats_options(self._filter_groups())["utrecht"][1] == 2
        groups = self._filter_groups({"rol": str(self.skill2.public_id)})
        assert self._standplaats_options(groups)["utrecht"][1] == 1

    def test_unknown_standplaats_filters_nothing(self):
        """No option means no chip to undo it, so it must not empty the list."""
        self._aanvraag(self.vacancy, self.skill, location="Utrecht")

        assert len(self._card_ids({"standplaats": "Atlantis"})) == len(self._card_ids())

    def test_standplaats_chip_shows_the_spelling(self):
        self._aanvraag(self.vacancy, self.skill, location="Den Haag")
        self.client.force_login(self.auth_user)

        content = self.client.get(self.list_url, {"standplaats": "den haag"}).content.decode()
        assert re.search(r'<nldd-token[^>]*data-filter-name="standplaats"[^>]*>Den Haag</nldd-token>', content)

    # --- Paging, count and texts ---------------------------------------------

    def test_pagination_per_aanvraag(self):
        """61 aanvragen: 60 cards and "Meer tonen", the 61st on ``?pagina=2``."""
        Service.objects.bulk_create(
            Service(assignment=self.vacancy, description="", skill=self.skill, status="OPEN", source="wies")
            for _ in range(60)
        )

        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        assert len(CARD_AANVRAAG_RE.findall(content)) == 60
        assert "<p>61 aanvragen</p>" in content
        assert 'text="Meer tonen"' in content

        rows = self.client.get(self.list_url, {"pagina": "2"}, headers={"hx-request": "true"}).content.decode()
        assert len(CARD_AANVRAAG_RE.findall(rows)) == 1
        # Only the rows template: no results line, no grid wrapper, no next page.
        assert 'id="results"' not in rows
        assert 'id="assignment-card-grid"' not in rows
        assert 'text="Meer tonen"' not in rows

    def test_count_says_aanvraag_or_aanvragen(self):
        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        assert "<p>1 aanvraag</p>" in content

        self._aanvraag(self.vacancy, self.skill2)
        content = self.client.get(self.list_url).content.decode()
        assert "<p>2 aanvragen</p>" in content

    def test_empty_state(self):
        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url, {"zoek": "niets-dat-past"}).content.decode()
        assert 'text="Geen aanvragen gevonden"' in content
        assert "Geen opdrachten gevonden" not in content

    def test_empty_state_without_filters_says_there_are_none(self):
        """Nothing to adjust without a filter or search, so no advice to."""
        Service.objects.all().delete()
        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        assert 'text="Er zijn nu geen aanvragen"' in content
        assert "Pas de filters" not in content

    def test_search_placeholder(self):
        self.client.force_login(self.auth_user)
        content = self.client.get(self.list_url).content.decode()
        assert 'placeholder="Rol, opdracht of opdrachtgever zoeken"' in content


class AnnotateServiceDatesTest(TestCase):
    def test_follows_the_opdracht_or_its_own_period(self):
        assignment = Assignment.objects.create(
            name="Datumopdracht", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), source="wies"
        )
        follows = Service.objects.create(assignment=assignment, description="", source="wies")
        # Own dates set on the follower too: the ASSIGNMENT branch must ignore them.
        Service.objects.filter(pk=follows.pk).update(
            specific_start_date=date(2030, 1, 1), specific_end_date=date(2030, 2, 1)
        )
        own = Service.objects.create(
            assignment=assignment,
            description="",
            source="wies",
            period_source="SERVICE",
            specific_start_date=date(2026, 3, 1),
            specific_end_date=date(2026, 9, 30),
        )

        rows = {s.pk: s for s in annotate_service_dates(Service.objects.all())}
        assert rows[follows.pk].effective_start_date == date(2026, 1, 1)
        assert rows[follows.pk].effective_end_date == date(2026, 12, 31)
        assert rows[own.pk].effective_start_date == date(2026, 3, 1)
        assert rows[own.pk].effective_end_date == date(2026, 9, 30)


class AanvragenVisibilityTest(TestCase):
    """Every logged-in role sees the same aanvragen, hours included: a vacancy
    is public (``can_view_role_hours`` without a placement)."""

    def setUp(self):
        owner = make_other_business_manager_user()
        assignment = Assignment.objects.create(name="Zichtbare Opdracht", source="wies", owner=owner.colleague)
        self.service = Service.objects.create(
            assignment=assignment,
            description="",
            skill=Skill.objects.create(name="Architect"),
            status="OPEN",
            source="wies",
            hours_per_week=32,
        )

    def test_every_role_sees_the_aanvraag_with_its_hours(self):
        users = {
            "consultant": grant_consultant(User.objects.create_user(email="consultant@rijksoverheid.nl")),
            "zonder rol": User.objects.create_user(email="geenrol@rijksoverheid.nl"),
            "business manager": make_business_manager_user(),
        }
        for role, user in users.items():
            with self.subTest(role=role):
                self.client.force_login(user)
                response = self.client.get(reverse("assignment-list"))
                assert response.status_code == 200
                content = response.content.decode()
                assert CARD_AANVRAAG_RE.findall(content) == [str(self.service.public_id)]
                assert 'text="32 uur per week"' in content
