import json
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

    # --- Create via the side panel (assignment-create-sheet) ---
    # Same assignment fields as the full-page create, but no roles: those are
    # added afterwards in the assignment panel. Success is a 204 with an
    # HX-Location to ?opdracht=<id>.

    def test_sheet_post_requires_add_assignment_permission(self):
        # The create route is POST-only; without the permission a 403.
        self.client.force_login(self.regular_user)
        response = self.client.post(reverse("assignment-create-sheet"), {})
        assert response.status_code == 403

    def test_list_sentinel_htmx_returns_create_form(self):
        # ?nieuwe-opdracht opens the empty create form as a panel; the htmx
        # panel request gets only the fragment.
        self.client.force_login(self.bdm_user)
        response = self.client.get(
            reverse("assignment-list"),
            {"nieuwe-opdracht": ""},
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 200
        assert b"Opdracht invoeren" in response.content
        assert b"Voer opdracht in" in response.content

    def test_list_sentinel_full_page_opens_create_panel(self):
        # Full-page GET (refresh/bookmark): the whole list plus the create panel.
        self.client.force_login(self.bdm_user)
        response = self.client.get(reverse("assignment-list"), {"nieuwe-opdracht": ""})
        assert response.status_code == 200
        assert b"Opdracht invoeren" in response.content
        assert b"Voer opdracht in" in response.content

    def test_list_sentinel_without_permission_shows_list_no_panel(self):
        # Without the permission: plain list, no create panel — no 403, this is the list view.
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("assignment-list"), {"nieuwe-opdracht": ""})
        assert response.status_code == 200
        assert b"Voer opdracht in" not in response.content

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
        # HX-Location sends the client to the new assignment panel.
        assignment = Assignment.objects.get(name="Sheet Opdracht")
        assert f"opdracht={assignment.public_id}" in response["HX-Location"]
        # No roles: those are added later via the panel.
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
        # Invalid form: re-render (200), no assignment created.
        assert response.status_code == 200
        assert not Assignment.objects.filter(name="Zonder Opdrachtgever").exists()
        # The org error must render id-wired (error-message + invalid), or
        # nldd-form-field shows it at height 0 and "Aanmaken" appears dead.
        html = response.content.decode()
        assert 'id="error-organizations-1"' in html
        assert 'error-message="error-organizations-1"' in html
        # The template splits the picker div's attributes over lines, so match
        # the element rather than one flat substring.
        picker = re.search(r'<div id="assignment-org-picker"(.*?)>', html, re.DOTALL)
        assert picker is not None
        assert "invalid" in picker.group(1)

    def test_sheet_post_unsafe_terug_url_falls_back_to_list(self):
        # _safe_return_path rejects a protocol-relative terug_url, so the
        # HX-Location falls back to the list.
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Onveilige Terug",
                "owner": self.bdm_colleague.public_id,
                **org_formset_data([(self.org, "PRIMARY")]),
                "terug_url": "//evil.example",
            },
        )
        assert response.status_code == 204
        assignment = Assignment.objects.get(name="Onveilige Terug")
        location = json.loads(response["HX-Location"])
        assert location["path"] == f"{reverse('assignment-list')}?opdracht={assignment.public_id}"

    def test_sheet_success_banner_rides_along_on_panel_load(self):
        """The success banner rides along as an OOB swap on the panel response.

        base.html does not reload on a panel swap, so the banner cannot come
        from there.
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

        # The follow-up request htmx makes after HX-Location: a panel load.
        panel = self.client.get(
            reverse("assignment-list"),
            {"opdracht": assignment.public_id},
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

    def test_create_button_targets_list_sentinel(self):
        # The button opens the create sheet as a panel on the list
        # (?nieuwe-opdracht) and pushes the URL, not via /invoeren/?terug=.
        self.client.force_login(self.bdm_user)
        response = self.client.get(reverse("assignment-list"))
        html = response.content.decode()
        assert "nieuwe-opdracht" in html
        assert 'hx-push-url="true"' in html
        assert "invoeren/?terug=" not in html

    def test_regular_user_does_not_see_create_button(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        assert b"Opdracht invoeren" not in response.content
