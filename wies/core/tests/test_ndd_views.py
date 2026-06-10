"""Tests voor de NLDD design system views.

Verifieert dat:
- De homepage rendert met NLDD-specifieke assets en geen RVO assets meelaadt.
- HTMX partials de juiste templates gebruiken.
- Side panel partial wordt geserveerd voor HX-Target=nldd-side-panel-container.
- Geen NDD tags lekken naar NLDD templates (isolatie-garantie).
"""

from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    Colleague,
    Placement,
    Service,
    Skill,
)

User = get_user_model()


def _login(client):
    Group.objects.get_or_create(name="Beheerder")
    user = User.objects.create_user(email="nldd-test@rijksoverheid.nl", first_name="NDD", last_name="Tester")
    client.force_login(user)
    return user


class NDDViewRendersTest(TestCase):
    def setUp(self):
        self.client = Client()
        _login(self.client)

    def test_ndd_home_renders(self):
        response = self.client.get(reverse("ndd-home"))
        assert response.status_code == 200
        body = response.content.decode()
        # NLDD vendor assets aanwezig
        assert "vendor/nldd/ndd.styles.css" in body
        assert "vendor/nldd/ndd.bundle.js" in body
        assert "nldd-top-navigation-bar" in body
        # Géén RVO assets
        assert "@nl-rvo/component-library-css" not in body
        assert "rvo-theme" not in body

    def test_ndd_filter_partial_returns_correct_template(self):
        # Met HX-Request rendert PlacementListNDDView.get_template_names()
        # parts/filter_and_table_container.html — herkenbaar aan de
        # outer container ID.
        response = self.client.get(reverse("ndd-home"), headers={"hx-request": "true"})
        assert response.status_code == 200
        body = response.content.decode()
        assert 'id="nldd-filter-and-table-container"' in body
        # De volledige page chrome (nldd-app body) hoort niet in de partial.
        assert 'class="nldd-app"' not in body


class NDDPanelTest(TestCase):
    def setUp(self):
        self.client = Client()
        _login(self.client)

        # Minimale data: 1 collega (zonder user link), 1 assignment, 1 service, 1 placement.
        self.colleague = Colleague.objects.create(name="Anna Tester", email="anna@example.com")
        self.assignment = Assignment.objects.create(name="Test opdracht")
        self.skill = Skill.objects.create(name="Tester")
        self.service = Service.objects.create(assignment=self.assignment, skill=self.skill, status="OPEN")
        Placement.objects.create(colleague=self.colleague, service=self.service)

    def test_ndd_panel_partial_for_collega(self):
        response = self.client.get(
            reverse("ndd-home"),
            {"collega": str(self.colleague.id)},
            headers={"hx-request": "true", "hx-target": "nldd-side-panel-content"},
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert self.colleague.name in body
        assert "nldd-panel" in body
        # Géén volledige page render
        assert 'class="nldd-app"' not in body

    def test_ndd_panel_partial_for_plaatsing(self):
        placement = Placement.objects.first()
        response = self.client.get(
            reverse("ndd-home"),
            {"plaatsing": str(placement.id)},
            headers={"hx-request": "true", "hx-target": "nldd-side-panel-content"},
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert self.colleague.name in body
        assert "nldd-panel" in body
        assert 'class="nldd-app"' not in body

    def test_ndd_panel_partial_for_opdracht(self):
        response = self.client.get(
            reverse("ndd-home"),
            {"opdracht": str(self.assignment.id)},
            headers={"hx-request": "true", "hx-target": "nldd-side-panel-content"},
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert self.assignment.name in body
        assert "nldd-panel" in body
        assert 'class="nldd-app"' not in body


class NDDClientModalTest(TestCase):
    def setUp(self):
        self.client = Client()
        _login(self.client)

    def test_client_modal_returns_ndd_template(self):
        response = self.client.get("/client-modal/")
        assert response.status_code == 200
        body = response.content.decode()
        assert 'id="nldd-client-modal"' in body
        assert "js/nldd/client_tree.js" in body


class NDDIsolationTest(TestCase):
    """Garantie: geen RVO classes in NLDD templates."""

    REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    JINJA_ROOT = REPO_ROOT / "wies" / "core" / "jinja2"

    def test_no_rvo_classes_in_nldd_templates(self):
        offenders = []
        rvo_markers = ("rvo-button", "rvo-form", "rvo-dialog", "utrecht-icon", "rvo-checkbox")
        # Scan all templates in jinja2/ root and parts/, excluding nldd/ (form) and django/ subdirs.
        exclude_dirs = {"nldd", "django"}
        for path in self.JINJA_ROOT.rglob("*.html"):
            if any(part in exclude_dirs for part in path.relative_to(self.JINJA_ROOT).parts):
                continue
            text = path.read_text(encoding="utf-8")
            offenders.extend(
                f"{path.relative_to(self.REPO_ROOT)}: {marker}" for marker in rvo_markers if marker in text
            )
        assert offenders == [], f"RVO classes lekken naar NLDD templates: {offenders}"
