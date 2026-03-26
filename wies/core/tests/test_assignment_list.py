from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    User,
)


class AssignmentListViewTest(TestCase):
    """Tests for the assignment list (vacancy cards) view"""

    def setUp(self):
        self.client = Client()
        self.list_url = reverse("assignment-list")

        self.auth_user = User.objects.create(
            username="testuser",
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )

        self.org = OrganizationUnit.objects.create(name="Test Org", label="Test Org")
        self.org2 = OrganizationUnit.objects.create(name="Other Org", label="Other Org")
        self.skill = Skill.objects.create(name="Python Developer")
        self.skill2 = Skill.objects.create(name="Data Engineer")

        # Vacancy assignment (has unfilled OPEN service → should appear)
        self.vacancy = Assignment.objects.create(
            name="Open Vacature",
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

    def test_shows_only_vacature_assignments(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Open Vacature" in content
        assert "Ingevulde Opdracht" not in content

    def test_search_filter(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"zoek": "Open Vacature"})
        content = response.content.decode()
        assert "Open Vacature" in content

        response = self.client.get(self.list_url, {"zoek": "nonexistent"})
        content = response.content.decode()
        assert "Open Vacature" not in content

    def test_filter_by_rol(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"rol": str(self.skill.id)})
        content = response.content.decode()
        assert "Open Vacature" in content

        response = self.client.get(self.list_url, {"rol": str(self.skill2.id)})
        content = response.content.decode()
        assert "Open Vacature" not in content

    def test_filter_by_org(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"org_self": str(self.org.id)})
        content = response.content.decode()
        assert "Open Vacature" in content

        response = self.client.get(self.list_url, {"org_self": str(self.org2.id)})
        content = response.content.decode()
        assert "Open Vacature" not in content

    def test_htmx_filter_returns_card_container(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, headers={"hx-request": "true"})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="filter-and-table-container"' in content

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
        response = self.client.get(self.list_url, {"rol": str(self.skill2.id)})
        content = response.content.decode()
        assert "Mix Opdracht" in content

        # Filtering by skill (filled) should NOT show Mix Opdracht
        response = self.client.get(self.list_url, {"rol": str(self.skill.id)})
        content = response.content.decode()
        assert "Mix Opdracht" not in content
