"""Each list response (Wie zit waar?, Aanvragen, Gebruikers) builds only the context layer its template renders."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.tests.role_helpers import make_business_manager_user
from wies.core.views.assignments import AanvraagListView
from wies.core.views.placements import PlacementOverviewView
from wies.core.views.users import UserListView

User = get_user_model()

HTMX = {"hx-request": "true"}


class ListResponseTest(TestCase):
    def setUp(self):
        self.client.force_login(make_business_manager_user())
        today = timezone.now().date()
        assignment = Assignment.objects.create(
            name="Cloud Migratie", start_date=today - timedelta(days=30), end_date=today + timedelta(days=30)
        )
        skill = Skill.objects.create(name="Ontwikkelaar")
        for name in ("Anna Bakker", "Bob Jansen", "Carla de Vries"):
            colleague = Colleague.objects.create(name=name, email=f"{name.split()[0].lower()}@rijksoverheid.nl")
            service = Service.objects.create(assignment=assignment, description=name, skill=skill, source="wies")
            Placement.objects.create(colleague=colleague, service=service, source="wies")
        self.colleague = colleague

    def test_meer_tonen_renders_the_next_cards_without_the_sidebar(self):
        with (
            patch.object(PlacementOverviewView, "paginate_by", 1),
            patch.object(PlacementOverviewView, "_filter_groups") as filter_groups,
        ):
            response = self.client.get(reverse("home"), {"pagina": "2"}, headers=HTMX)
        filter_groups.assert_not_called()
        assert response.status_code == 200
        assert response.template_name == "parts/placement_cards.html"
        assert len(response.context_data["cards"]) == 1
        assert "pagina=3" in response.context_data["next_page_url"]
        assert "filter_groups" not in response.context_data

    def test_a_toggle_or_sort_click_with_a_panel_param_gets_the_results(self):
        """After a page load with ?collega=, the weergave toggle and sort links keep it
        in their url; their htmx request targets #results, not the panel."""
        params = {"collega": self.colleague.public_id, "weergave": "opdracht"}
        with patch("wies.core.views.placements.resolve_side_panel") as resolve:
            response = self.client.get(reverse("home"), params, headers={**HTMX, "hx-target": "results"})
        resolve.assert_not_called()
        assert response.status_code == 200
        assert response.template_name == "parts/placement_results.html"
        assert "filter_groups" in response.context_data
        assert "view_options" in response.context_data
        assert "panel_data" not in response.context_data

    def test_the_full_page_has_every_layer(self):
        response = self.client.get(reverse("home"), {"collega": self.colleague.public_id})
        assert response.status_code == 200
        for key in ("cards", "filter_groups", "view_options", "panel_data", "show_missing_opdrachten_banner"):
            assert key in response.context_data, key
        assert response.context_data["panel_data"] is not None


class AanvraagListResponseTest(TestCase):
    def setUp(self):
        self.client.force_login(make_business_manager_user())
        today = timezone.now().date()
        assignment = Assignment.objects.create(
            name="Cloud Migratie", start_date=today - timedelta(days=30), end_date=today + timedelta(days=30)
        )
        skill = Skill.objects.create(name="Ontwikkelaar")
        for description in ("Rol A", "Rol B", "Rol C"):
            Service.objects.create(
                assignment=assignment, description=description, skill=skill, status="OPEN", source="wies"
            )

    def test_meer_tonen_renders_the_next_cards_without_the_sidebar(self):
        with (
            patch.object(AanvraagListView, "paginate_by", 1),
            patch.object(AanvraagListView, "_filter_groups") as filter_groups,
        ):
            response = self.client.get(reverse("assignment-list"), {"pagina": "2"}, headers=HTMX)
        filter_groups.assert_not_called()
        assert response.status_code == 200
        assert response.template_name == "parts/aanvraag_cards.html"
        assert len(response.context_data["cards"]) == 1
        assert "pagina=3" in response.context_data["next_page_url"]
        assert "filter_groups" not in response.context_data

    def test_a_filter_change_gets_the_results_without_the_panel(self):
        with patch("wies.core.views.assignments.resolve_side_panel") as resolve:
            response = self.client.get(reverse("assignment-list"), {"zoek": "Cloud"}, headers=HTMX)
        resolve.assert_not_called()
        assert response.status_code == 200
        assert response.template_name == "parts/aanvraag_results.html"
        assert "filter_groups" in response.context_data
        assert response.context_data["result_announcement"] == "3 aanvragen"
        assert "panel_data" not in response.context_data
        assert "primary_button" not in response.context_data

    def test_the_full_page_has_every_layer(self):
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        assert response.template_name == "assignments.html"
        for key in ("cards", "filter_groups", "result_announcement", "panel_data", "primary_button"):
            assert key in response.context_data, key


class UserListResponseTest(TestCase):
    def setUp(self):
        viewer = User.objects.create_user(email="beheer@rijksoverheid.nl", first_name="Beheer", last_name="Der")
        viewer.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(viewer)
        for first_name in ("Anna", "Bob"):
            User.objects.create_user(email=f"{first_name.lower()}@rijksoverheid.nl", first_name=first_name)

    def test_meer_tonen_renders_the_next_rows_without_the_sheet(self):
        with (
            patch.object(UserListView, "paginate_by", 1),
            patch.object(UserListView, "_filter_groups") as filter_groups,
        ):
            response = self.client.get(reverse("admin-users"), {"pagina": "2"}, headers=HTMX)
        filter_groups.assert_not_called()
        assert response.status_code == 200
        assert response.template_name == "parts/user_rows.html"
        assert len(response.context_data["rows"]) == 1
        assert "pagina=3" in response.context_data["next_page_url"]
        assert "filter_groups" not in response.context_data

    def test_a_filter_change_gets_the_results(self):
        response = self.client.get(reverse("admin-users"), {"zoek": "rijksoverheid"}, headers=HTMX)
        assert response.status_code == 200
        assert response.template_name == "parts/user_results.html"
        assert "filter_groups" in response.context_data
        assert response.context_data["result_announcement"] == "3 gebruikers"

    def test_the_full_page_has_every_layer(self):
        response = self.client.get(reverse("admin-users"))
        assert response.status_code == 200
        assert response.template_name == "user_admin.html"
        for key in ("rows", "filter_groups", "result_announcement", "active_sort_label"):
            assert key in response.context_data, key
