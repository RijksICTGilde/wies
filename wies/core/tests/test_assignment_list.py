from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Ministry, Service, Skill, User


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

        self.ministry = Ministry.objects.create(name="Ministerie van BZK", abbreviation="BZK")
        self.ministry2 = Ministry.objects.create(name="Ministerie van EZK", abbreviation="EZK")
        self.skill = Skill.objects.create(name="Python Developer")
        self.skill2 = Skill.objects.create(name="Data Engineer")

        # Vacancy assignment (should appear)
        self.vacancy = Assignment.objects.create(
            name="Open Vacature",
            status="OPEN",
            organization="Test Org",
            ministry=self.ministry,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            source="wies",
        )
        Service.objects.create(
            assignment=self.vacancy,
            description="Service 1",
            skill=self.skill,
            source="wies",
        )

        # Filled assignment (should NOT appear)
        self.filled = Assignment.objects.create(
            name="Ingevulde Opdracht",
            status="INGEVULD",
            organization="Other Org",
            ministry=self.ministry,
            source="wies",
        )

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

    def test_filter_by_ministerie(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"ministerie": str(self.ministry.id)})
        content = response.content.decode()
        assert "Open Vacature" in content

        response = self.client.get(self.list_url, {"ministerie": str(self.ministry2.id)})
        content = response.content.decode()
        assert "Open Vacature" not in content

    def test_filter_by_opdrachtgever(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"opdrachtgever": "Test Org"})
        content = response.content.decode()
        assert "Open Vacature" in content

        response = self.client.get(self.list_url, {"opdrachtgever": "Nonexistent"})
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

    def test_side_panel_ignores_filled_assignment(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(self.list_url, {"opdracht": str(self.filled.id)})
        assert response.status_code == 200
        content = response.content.decode()
        # The panel should not open for a non-OPEN assignment
        assert "panel_data" not in content or "side_panel-container" in content
