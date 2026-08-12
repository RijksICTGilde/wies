from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

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
from wies.core.views import AssignmentListView, _filter_aware_org_counts

User = get_user_model()


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
        Service.objects.create(
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

    def test_side_panel_opens_for_any_assignment(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"opdracht": str(self.filled.id)})
        assert response.status_code == 200
        content = response.content.decode()
        assert "side_panel" in content

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

    def test_org_count_does_not_collapse_multiple_aanvragen(self):
        """Two aanvragen on the same org count as 2, not 1.

        Regression: ``SELECT DISTINCT organizations.id`` collapsed both aanvragen
        into one row, so the sidebar showed 1 while the filter returned 2.
        """
        self._open_aanvraag("Second Aanvraag", self.org, self.skill)

        groups = self._filter_groups()
        assert self._org_count(groups, self.org) == 2

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

    def test_rol_count_counts_assignment_once_per_skill(self):
        """An assignment with two OPEN services for the same skill counts once.

        Selecting the rol returns it once, so the count must not be bumped per
        service; an aanvraag can legitimately request two of the same role.
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
        assert self._rol_count(groups, self.skill2) == 1

    def test_org_count_not_inflated_by_service_fanout(self):
        """One aanvraag with two matching services counts once per org.

        With a rol filter active the ``services`` join fans the assignment row out
        to 2, so the count requires re-keying on distinct assignment ids rather
        than merely dropping ``.distinct()``.
        """
        fanout_org = OrganizationUnit.objects.create(name="Fanout Org", label="Fanout Org")
        assignment = Assignment.objects.create(name="Two Service Aanvraag", source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=fanout_org)
        Service.objects.create(
            assignment=assignment, description="svc a", skill=self.skill, status="OPEN", source="wies"
        )
        Service.objects.create(
            assignment=assignment, description="svc b", skill=self.skill2, status="OPEN", source="wies"
        )

        # A rol filter on both skills makes the services join fan out the org row.
        groups = self._filter_groups({"rol": [str(self.skill.public_id), str(self.skill2.public_id)]})
        assert self._org_count(groups, fanout_org) == 1

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

    def _modal_org_counts(self, query_params=None):
        """Builds the org modal's per-org self-count Counter directly.

        Calls ``_filter_aware_org_counts`` the way client_modal does, with
        ``created_at`` nulled so the SELECT DISTINCT collapse reproduces
        (see _filter_groups).
        """
        Assignment.objects.update(created_at=None)
        request = RequestFactory().get("/client-modal/", query_params or {})
        request.user = self.auth_user
        return _filter_aware_org_counts(request, "open_assignments", [])

    def test_modal_org_count_does_not_collapse_multiple_aanvragen(self):
        """The org modal counts every aanvraag on an org, rather than collapsing to 1.

        Same ``SELECT DISTINCT organizations.id`` collapse as the sidebar, in
        ``_filter_aware_org_counts``' open_assignments branch.
        """
        self._open_aanvraag("Second Aanvraag", self.org, self.skill)

        counts = self._modal_org_counts()
        assert counts[self.org.id] == 2

    def test_modal_org_count_not_inflated_by_service_fanout(self):
        """One aanvraag with two matching services counts once per org in the modal.

        An active rol filter joins services and would fan the org row out to 2
        without re-keying on distinct ids.
        """
        fanout_org = OrganizationUnit.objects.create(name="Modal Fanout Org", label="Modal Fanout Org")
        assignment = Assignment.objects.create(name="Two Service Aanvraag", source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=fanout_org)
        Service.objects.create(
            assignment=assignment, description="svc a", skill=self.skill, status="OPEN", source="wies"
        )
        Service.objects.create(
            assignment=assignment, description="svc b", skill=self.skill2, status="OPEN", source="wies"
        )

        counts = self._modal_org_counts({"rol": [str(self.skill.public_id), str(self.skill2.public_id)]})
        assert counts[fanout_org.id] == 1

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
