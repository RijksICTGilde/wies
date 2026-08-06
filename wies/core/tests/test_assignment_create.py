import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    Colleague,
    Event,
    OrganizationUnit,
    Skill,
)
from wies.core.roles import setup_roles

User = get_user_model()

# Formset management form data for the service formset (prefix="service")
FORMSET_MGMT_1 = {
    "service-TOTAL_FORMS": "1",
    "service-INITIAL_FORMS": "0",
    "service-MIN_NUM_FORMS": "1",
    "service-MAX_NUM_FORMS": "1000",
}

FORMSET_MGMT_2 = {
    "service-TOTAL_FORMS": "2",
    "service-INITIAL_FORMS": "0",
    "service-MIN_NUM_FORMS": "1",
    "service-MAX_NUM_FORMS": "1000",
}


def org_formset_data(orgs):
    """Build org formset POST data from list of (org, role) tuples."""
    data = {
        "org-TOTAL_FORMS": str(len(orgs)),
        "org-INITIAL_FORMS": "0",
        "org-MIN_NUM_FORMS": "1",
        "org-MAX_NUM_FORMS": "1000",
    }
    for i, (org, role) in enumerate(orgs):
        data[f"org-{i}-organization"] = org.public_id
        data[f"org-{i}-role"] = role
    return data


class AssignmentCreateTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()

        self.bdm_user = User.objects.create(
            email="bdm@rijksoverheid.nl",
            first_name="BDM",
            last_name="User",
        )
        bdm_group = Group.objects.get(name="Business Development Manager")
        self.bdm_user.groups.add(bdm_group)
        add_assignment = Permission.objects.get(codename="add_assignment")
        add_service = Permission.objects.get(codename="add_service")
        add_placement = Permission.objects.get(codename="add_placement")
        self.bdm_user.user_permissions.add(add_assignment, add_service, add_placement)

        self.regular_user = User.objects.create(
            email="regular@rijksoverheid.nl",
            first_name="Regular",
            last_name="User",
        )

        self.colleague = Colleague.objects.create(
            name="Test Consultant",
            email="consultant@rijksoverheid.nl",
            source="wies",
        )
        self.bdm_colleague = Colleague.objects.create(
            name="BDM Colleague",
            email="bdm@rijksoverheid.nl",
            source="wies",
            user=self.bdm_user,
        )
        self.skill = Skill.objects.create(name="Python Developer")
        self.org = OrganizationUnit.objects.create(
            name="Rijkswaterstaat",
            label="RWS Hoofdkantoor",
        )
        self.org2 = OrganizationUnit.objects.create(
            name="Belastingdienst",
            label="Belastingdienst",
        )

    # --- Aanmaak via het zijpaneel (assignment-create-sheet) ---
    # Zelfde opdrachtvelden als de full-page create, maar zonder rollen: die
    # voeg je daarna in het opdrachtpaneel toe. Bij succes een 204 met
    # HX-Location naar ?opdracht=<id>.

    def test_sheet_requires_add_assignment_permission(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("assignment-create-sheet"))
        assert response.status_code == 403

    def test_sheet_get_returns_form(self):
        self.client.force_login(self.bdm_user)
        response = self.client.get(reverse("assignment-create-sheet"))
        assert response.status_code == 200
        assert b"Opdracht invoeren" in response.content
        assert b"Voer opdracht in" in response.content

    def test_sheet_post_creates_assignment_without_services(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Sheet Opdracht",
                "owner": self.bdm_colleague.public_id,
                **org_formset_data([(self.org, "PRIMARY")]),
                "terug_url": reverse("assignment-list"),
            },
        )
        assert response.status_code == 204
        # HX-Location stuurt de client naar het nieuwe opdrachtpaneel.
        assignment = Assignment.objects.get(name="Sheet Opdracht")
        assert f"opdracht={assignment.public_id}" in response["HX-Location"]
        # Geen rollen: die komen later via het paneel.
        assert assignment.services.count() == 0

    def test_sheet_post_emits_create_event(self):
        self.client.force_login(self.bdm_user)
        self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Sheet Audit",
                "owner": self.bdm_colleague.public_id,
                **org_formset_data([(self.org, "PRIMARY")]),
                "terug_url": reverse("assignment-list"),
            },
        )
        assignment = Assignment.objects.get(name="Sheet Audit")
        event = Event.objects.get(object_type="Assignment", action="create", object_id=assignment.id)
        assert event.context["name"] == "Sheet Audit"

    def test_sheet_post_validation_no_org_rerenders_form(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Zonder Opdrachtgever",
                "owner": self.bdm_colleague.public_id,
                **org_formset_data([]),
                "terug_url": reverse("assignment-list"),
            },
        )
        # Ongeldig formulier: opnieuw renderen (200), geen opdracht aangemaakt.
        assert response.status_code == 200
        assert not Assignment.objects.filter(name="Zonder Opdrachtgever").exists()
        # De org-fout moet GEKOPPELD renderen, anders toont nldd-form-field hem op
        # hoogte 0 en lijkt "Aanmaken" niks te doen. De error-text draagt een id en
        # de picker-div wijst er via error-message naar (+ invalid). Zie
        # org_picker.html en wire_field_errors.
        html = response.content.decode()
        assert 'id="error-organizations-1"' in html
        assert 'error-message="error-organizations-1"' in html
        # De picker-div draagt id + invalid; die staan in de template op aparte
        # regels, dus matchen op het element in plaats van op één platte substring.
        picker = re.search(r'<div id="assignment-org-picker"(.*?)>', html, re.DOTALL)
        assert picker is not None
        assert "invalid" in picker.group(1)

    def test_sheet_success_banner_rides_along_on_panel_load(self):
        """De 'is aangemaakt'-banner reist als OOB-swap mee met de panel-response
        die op de HX-Location volgt — base.html herlaadt niet bij een panel-swap.
        """
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Banner Opdracht",
                "owner": self.bdm_colleague.public_id,
                **org_formset_data([(self.org, "PRIMARY")]),
                "terug_url": reverse("assignment-list"),
            },
        )
        assert response.status_code == 204
        assignment = Assignment.objects.get(name="Banner Opdracht")

        # De vervolg-request (zoals htmx die na HX-Location doet): panel-load.
        panel = self.client.get(
            reverse("assignment-list"),
            {"opdracht": assignment.id},
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        html = panel.content.decode()
        assert 'id="flash-messages"' in html
        assert "hx-swap-oob" in html
        assert "Banner Opdracht" in html
        assert "is aangemaakt" in html
        assert "Bekijk opdracht" in html


class AssignmentListButtonTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()

        self.bdm_user = User.objects.create(
            email="bdm@rijksoverheid.nl",
        )
        add_assignment = Permission.objects.get(codename="add_assignment")
        self.bdm_user.user_permissions.add(add_assignment)

        self.regular_user = User.objects.create(
            email="regular@rijksoverheid.nl",
        )

    def test_bdm_sees_create_button(self):
        self.client.force_login(self.bdm_user)
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        assert b"Opdracht invoeren" in response.content

    def test_regular_user_does_not_see_create_button(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        assert b"Opdracht invoeren" not in response.content
