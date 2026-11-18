"""An htmx side-panel request returns the panel before the list builds its page."""

import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Placement, Service, Skill
from wies.core.roles import setup_roles
from wies.core.tests.role_helpers import make_business_manager_user
from wies.core.views.assignments import AanvraagListView
from wies.core.views.placements import PlacementOverviewView

User = get_user_model()

PANEL = {"hx-request": "true", "hx-target": "side-panel-content"}


class PanelRequestTest(TestCase):
    def setUp(self):
        # The roles' permissions: the create panel needs core.add_assignment.
        setup_roles()
        self.user = make_business_manager_user()
        self.colleague = self.user.colleague
        today = timezone.now().date()
        self.assignment = Assignment.objects.create(
            name="Cloud Migratie", start_date=today - timedelta(days=30), end_date=today + timedelta(days=30)
        )
        skill = Skill.objects.create(name="Ontwikkelaar")
        placed = Service.objects.create(assignment=self.assignment, description="Rol", skill=skill, source="wies")
        Placement.objects.create(colleague=self.colleague, service=placed, source="wies")
        self.aanvraag = Service.objects.create(
            assignment=self.assignment, description="Open rol", skill=skill, status="OPEN", source="wies"
        )
        self.client.force_login(self.user)

    def _panel(self, url_name, params, view_cls):
        # Where each view starts building its page: the cards, or ListView's context.
        page_build = "_cards_context" if view_cls is PlacementOverviewView else "get_context_data"
        with patch.object(view_cls, page_build) as page:
            response = self.client.get(reverse(url_name), params, headers=PANEL)
        page.assert_not_called()
        return response

    def test_wie_zit_waar_colleague_panel(self):
        response = self._panel("home", {"collega": self.colleague.public_id}, PlacementOverviewView)
        assert response.status_code == 200
        assert response.template_name == "parts/colleague_panel_content.html"
        assert self.colleague.name in response.content.decode()

    def test_wie_zit_waar_opdracht_panel(self):
        params = {"opdracht": self.assignment.public_id, "weergave": "opdracht"}
        response = self._panel("home", params, PlacementOverviewView)
        assert response.status_code == 200
        assert response.template_name == "parts/assignment_panel_content.html"
        assert response.context_data["panel_data"]["assignment"] == self.assignment

    def test_aanvragen_aanvraag_panel(self):
        response = self._panel("assignment-list", {"aanvraag": self.aanvraag.public_id}, AanvraagListView)
        assert response.status_code == 200
        assert response.template_name == "parts/aanvraag_panel_content.html"

    def test_aanvragen_create_panel(self):
        response = self._panel("assignment-list", {"nieuwe-opdracht": ""}, AanvraagListView)
        assert response.status_code == 200
        assert response.template_name == "parts/assignment_create_panel_content.html"

    def test_an_unknown_object_is_still_a_404(self):
        for url_name, param in (("home", "collega"), ("home", "opdracht"), ("assignment-list", "aanvraag")):
            response = self.client.get(reverse(url_name), {param: uuid.uuid4()}, headers=PANEL)
            assert response.status_code == 404, (url_name, param)

    def test_a_full_page_load_still_opens_the_panel(self):
        response = self.client.get(reverse("home"), {"collega": self.colleague.public_id})
        assert response.status_code == 200
        assert response.context_data["panel_data"] is not None
        assert "cards" in response.context_data

    def test_a_panel_request_with_nothing_to_open_says_niet_gevonden(self):
        for url_name, view_cls in (("home", PlacementOverviewView), ("assignment-list", AanvraagListView)):
            response = self._panel(url_name, {}, view_cls)
            assert response.status_code == 200, url_name
            assert response.template_name == "parts/assignment_panel_content.html"
            assert response.context_data["panel_data"] is None
            assert 'text="Niet gevonden"' in response.content.decode()

    def test_bezetting_with_nothing_to_open_says_niet_gevonden_without_building_rows(self):
        with patch("wies.core.views.bezetting.colleague_occupancy") as occupancy:
            response = self.client.get(reverse("bezetting"), headers=PANEL)
        occupancy.assert_not_called()
        assert response.status_code == 200
        assert 'text="Niet gevonden"' in response.content.decode()

    def test_the_create_form_without_the_permission_says_niet_gevonden(self):
        self.client.force_login(User.objects.create_user(email="geen@rijksoverheid.nl"))
        response = self._panel("assignment-list", {"nieuwe-opdracht": ""}, AanvraagListView)
        assert response.status_code == 200
        assert response.context_data["panel_data"] is None
