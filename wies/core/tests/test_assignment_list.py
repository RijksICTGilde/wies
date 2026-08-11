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
from wies.core.views import AssignmentListView

User = get_user_model()


class AssignmentListViewTest(TestCase):
    """Tests for the assignment list (aanvragen cards) view"""

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

        # Aanvraag assignment (has unfilled OPEN service → should appear)
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

        # Filled assignment (all services have placements → should NOT appear)
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
        # De partial levert de resultatenregel (het swap-doel) plus de card grid
        # als out-of-band swap.
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
        """Assignment with only CONCEPT services should NOT appear on opdrachten page"""
        concept_assignment = Assignment.objects.create(name="Concept Opdracht", source="wies")
        Service.objects.create(
            assignment=concept_assignment, description="Concept Service", status="CONCEPT", source="wies"
        )
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url)
        content = response.content.decode()
        assert "Concept Opdracht" not in content

    def test_all_open_services_filled_not_shown(self):
        """Assignment where all OPEN services have placements should NOT appear"""
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url)
        content = response.content.decode()
        assert "Ingevulde Opdracht" not in content

    def test_mix_of_filled_and_unfilled_services(self):
        """Assignment with both filled and unfilled OPEN services should appear"""
        mix_assignment = Assignment.objects.create(name="Mix Opdracht", source="wies")
        # One filled service
        filled_svc = Service.objects.create(
            assignment=mix_assignment, description="Filled", skill=self.skill, status="OPEN", source="wies"
        )
        colleague = Colleague.objects.create(name="Mix Col", email="mix@test.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=filled_svc, source="wies")
        # One unfilled service
        Service.objects.create(
            assignment=mix_assignment, description="Unfilled", skill=self.skill2, status="OPEN", source="wies"
        )

        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url)
        content = response.content.decode()
        assert "Mix Opdracht" in content

    def _filter_groups(self, query_params=None):
        """Build the view's ``filter_groups`` context directly (no template render).

        Jinja2 doesn't populate ``response.context``, so we drive the view itself —
        the same way ``_filter_aware_org_counts`` instantiates a bare view — and read
        the sidebar facet counts straight from the context it builds.

        Assignments loaded from fixtures (as in production) have ``created_at = None``
        because ``auto_now_add`` does not fire on ``loaddata``. That matters: the
        buggy ``SELECT DISTINCT organizations.id`` also carried ``created_at`` in the
        SELECT for the ``order_by``, so distinct timestamps hid the collapse. We null
        every assignment's ``created_at`` here to reproduce the real fixture condition
        under which the counts collapsed.
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
        """Pull the sidebar 'org' facet count for ``org`` out of filter_groups."""
        for group in groups:
            if group["name"] == "organisatie":
                for option in group["top_options"]:
                    if option["param"] == "org" and option["value"] == str(org.public_id):
                        return option["count"]
        return None

    def _rol_count(self, groups, skill):
        """Pull the sidebar 'rol' facet count for ``skill`` out of filter_groups."""
        for group in groups:
            if group["name"] == "rol":
                for option in group["options"]:
                    if option["value"] == str(skill.public_id):
                        return option["count"]
        return None

    def _open_aanvraag(self, name, org, skill):
        """Create an aanvraag on ``org`` with a single unfilled OPEN service for ``skill``."""
        assignment = Assignment.objects.create(name=name, source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        Service.objects.create(
            assignment=assignment, description=f"{name} service", skill=skill, status="OPEN", source="wies"
        )
        return assignment

    def test_org_count_does_not_collapse_multiple_aanvragen(self):
        """Two aanvragen on the same org must count as 2, not collapse to 1.

        Regression: the count query did ``.distinct().values_list("organizations__id")``
        → ``SELECT DISTINCT organizations.id`` collapsed both aanvragen (same org id)
        into one row, so the sidebar showed 1 while selecting the filter returned 2.
        """
        # setUp already created self.vacancy on self.org with an unfilled OPEN service.
        self._open_aanvraag("Second Aanvraag", self.org, self.skill)

        groups = self._filter_groups()
        assert self._org_count(groups, self.org) == 2

    def test_rol_count_does_not_collapse_multiple_aanvragen(self):
        """Two aanvragen sharing a skill must count as 2, not collapse to 1.

        Same ``SELECT DISTINCT services.skill_id`` collapse as the org count.
        """
        # setUp's self.vacancy already has an unfilled OPEN service for self.skill.
        self._open_aanvraag("Second Aanvraag", self.org, self.skill)

        groups = self._filter_groups()
        assert self._rol_count(groups, self.skill) == 2

    def test_rol_count_only_counts_open_unfilled_services(self):
        """A rol count must equal what selecting that rol returns.

        Selecting a rol matches assignments with an OPEN *unfilled* service for that
        skill (``_apply_filters``). So the count must ignore filled and CONCEPT
        services: an assignment whose only unfilled OPEN service is for skill2 must
        NOT bump the count of self.skill, even though it has (filled / CONCEPT)
        services for self.skill.
        """
        assignment = self._open_aanvraag("Mixed Services", self.org2, self.skill2)
        # A FILLED OPEN service for self.skill — selecting self.skill would not return
        # this assignment, so it must not be counted for self.skill.
        filled_svc = Service.objects.create(
            assignment=assignment, description="filled", skill=self.skill, status="OPEN", source="wies"
        )
        colleague = Colleague.objects.create(name="Col", email="mix-col@test.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=filled_svc, source="wies")
        # A CONCEPT service for self.skill — also not selectable.
        Service.objects.create(
            assignment=assignment, description="concept", skill=self.skill, status="CONCEPT", source="wies"
        )

        groups = self._filter_groups()
        # Only self.vacancy has an unfilled OPEN service for self.skill → count 1.
        assert self._rol_count(groups, self.skill) == 1
        # self.vacancy has none for skill2; only the mixed assignment does → count 1.
        assert self._rol_count(groups, self.skill2) == 1

    def test_rol_count_counts_assignment_once_per_skill(self):
        """An assignment with two OPEN services for the SAME skill counts once.

        Selecting the rol returns that assignment a single time, so its sidebar count
        must not be bumped per service. (An aanvraag can legitimately request two of
        the same role.)
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
        """One aanvraag with two matching services must count once per org, not twice.

        Guards against a naïve ``.distinct()`` removal: with a rol filter active,
        ``_apply_filters(exclude_filter="org")`` joins ``services`` and fans the
        assignment row out to 2. The count must still be 1 (one distinct aanvraag on
        the org), which requires re-keying on distinct assignment ids — not merely
        dropping ``.distinct()``.
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

        # rol filter on both skills makes _apply_filters join services and fan out the org row.
        groups = self._filter_groups({"rol": [str(self.skill.public_id), str(self.skill2.public_id)]})
        assert self._org_count(groups, fanout_org) == 1

    def test_rol_count_not_inflated_by_org_fanout(self):
        """One aanvraag on two orgs must count once per skill, not twice.

        Guards against a naïve ``.distinct()`` removal: with an org filter active,
        ``_apply_filters(exclude_filter="rol")`` matches the assignment via its
        ``organizations`` join and fans the row out to 2. The rol count must stay 1.
        """
        org_a = OrganizationUnit.objects.create(name="Fanout Org A", label="Fanout Org A")
        org_b = OrganizationUnit.objects.create(name="Fanout Org B", label="Fanout Org B")
        assignment = Assignment.objects.create(name="Two Org Aanvraag", source="wies")
        # Only one PRIMARY org per assignment is allowed; the second is INVOLVED.
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=org_a, role=OrganizationUnitRole.PRIMARY
        )
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=org_b, role=OrganizationUnitRole.INVOLVED
        )
        Service.objects.create(
            assignment=assignment, description="svc", skill=self.skill2, status="OPEN", source="wies"
        )

        # org filter on both orgs makes _apply_filters match via organizations and fan out.
        groups = self._filter_groups({"org_self": [str(org_a.public_id), str(org_b.public_id)]})
        assert self._rol_count(groups, self.skill2) == 1

    def test_filter_by_rol_excludes_filled_services(self):
        """Rol filter should only match assignments with an OPEN unfilled service for that skill"""
        # Assignment with a filled service (skill) and an unfilled service (skill2)
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

        # Filtering by skill2 (unfilled) should show Mix Opdracht
        response = self.client.get(self.list_url, {"rol": str(self.skill2.public_id)})
        content = response.content.decode()
        assert "Mix Opdracht" in content

        # Filtering by skill (filled) should NOT show Mix Opdracht
        response = self.client.get(self.list_url, {"rol": str(self.skill.public_id)})
        content = response.content.decode()
        assert "Mix Opdracht" not in content
