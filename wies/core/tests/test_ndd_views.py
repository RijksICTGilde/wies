"""Tests voor de NDD design system POC views.

Verifieert dat:
- /ndd/ rendert met NDD-specifieke assets en geen RVO assets meelaadt.
- HTMX partials de juiste NDD-templates gebruiken.
- Side panel partial wordt geserveerd voor HX-Target=ndd-side-panel-container.
- Geen NDD tags lekken naar non-NDD templates (isolatie-garantie).
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
    user = User.objects.create_user(email="ndd-test@rijksoverheid.nl", first_name="NDD", last_name="Tester")
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
        # NDD vendor + layout assets aanwezig
        assert "vendor/ndd/ndd.styles.css" in body
        assert "vendor/ndd/ndd.bundle.js" in body
        assert "css/ndd/layout.css" in body
        assert "js/ndd/htmx-bridge.js" in body
        # NDD specifieke layout class aanwezig
        assert 'class="ndd-app"' in body
        # Géén RVO assets in de NDD pagina
        assert "@nl-rvo/component-library-css" not in body
        assert "rvo-theme" not in body

    def test_ndd_filter_partial_returns_correct_template(self):
        # Met HX-Request rendert PlacementListNDDView.get_template_names()
        # ndd/parts/filter_and_table_container.html — herkenbaar aan de
        # outer container ID.
        response = self.client.get(reverse("ndd-home"), headers={"hx-request": "true"})
        assert response.status_code == 200
        body = response.content.decode()
        assert 'id="ndd-filter-and-table-container"' in body
        # De volledige page chrome (ndd-app body) hoort niet in de partial.
        assert 'class="ndd-app"' not in body


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
            headers={"hx-request": "true", "hx-target": "ndd-side-panel-content"},
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert self.colleague.name in body
        assert "ndd-panel" in body
        # Géén volledige page render
        assert 'class="ndd-app"' not in body

    def test_ndd_panel_partial_for_opdracht(self):
        response = self.client.get(
            reverse("ndd-home"),
            {"opdracht": str(self.assignment.id)},
            headers={"hx-request": "true", "hx-target": "ndd-side-panel-content"},
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert self.assignment.name in body
        assert "ndd-panel" in body
        assert 'class="ndd-app"' not in body


class NDDClientModalTest(TestCase):
    def setUp(self):
        self.client = Client()
        _login(self.client)

    def test_ndd_modal_query_param_returns_ndd_template(self):
        response = self.client.get("/client-modal/", {"ndd": "1"})
        assert response.status_code == 200
        body = response.content.decode()
        assert 'id="ndd-client-modal"' in body
        assert "js/ndd/client_tree.js" in body
        # RVO modal-id mag NIET in deze response zitten
        assert 'id="clientModal"' not in body

    def test_rvo_modal_default_returns_rvo_template(self):
        response = self.client.get("/client-modal/")
        assert response.status_code == 200
        body = response.content.decode()
        assert 'id="clientModal"' in body
        assert 'id="ndd-client-modal"' not in body


class NDDIsolationTest(TestCase):
    """Garantie: geen NDD-tags in non-NDD templates en omgekeerd."""

    REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    JINJA_ROOT = REPO_ROOT / "wies" / "core" / "jinja2"

    def test_no_ndd_tags_in_rvo_templates(self):
        offenders = []
        for path in self.JINJA_ROOT.rglob("*.html"):
            # Sla NDD subtree over
            if "ndd/" in str(path.relative_to(self.JINJA_ROOT)):
                continue
            text = path.read_text(encoding="utf-8")
            if "ndd-" in text or "<ndd-" in text:
                offenders.append(str(path.relative_to(self.REPO_ROOT)))
        assert offenders == [], f"NDD tags lekken naar RVO templates: {offenders}"

    def test_no_rvo_classes_in_ndd_templates(self):
        offenders = []
        ndd_dir = self.JINJA_ROOT / "ndd"
        rvo_markers = ("rvo-button", "rvo-form", "rvo-dialog", "utrecht-icon", "rvo-checkbox")
        for path in ndd_dir.rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            offenders.extend(
                f"{path.relative_to(self.REPO_ROOT)}: {marker}" for marker in rvo_markers if marker in text
            )
        assert offenders == [], f"RVO classes lekken naar NDD templates: {offenders}"
