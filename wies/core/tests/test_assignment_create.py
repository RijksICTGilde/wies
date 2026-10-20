import json
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
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
from wies.core.tests.role_helpers import grant_business_manager

User = get_user_model()


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

        self.business_manager_user = User.objects.create(
            email="business_manager@rijksoverheid.nl",
            first_name="Business Manager",
            last_name="User",
        )
        grant_business_manager(self.business_manager_user)
        add_assignment = Permission.objects.get(codename="add_assignment")
        add_service = Permission.objects.get(codename="add_service")
        add_placement = Permission.objects.get(codename="add_placement")
        self.business_manager_user.user_permissions.add(add_assignment, add_service, add_placement)

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
        self.business_manager_colleague = Colleague.objects.create(
            name="Business Manager Colleague",
            email="business_manager@rijksoverheid.nl",
            source="wies",
            user=self.business_manager_user,
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
        self.client.force_login(self.business_manager_user)
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
        self.client.force_login(self.business_manager_user)
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
        self.client.force_login(self.business_manager_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Sheet Opdracht",
                "owner": self.business_manager_colleague.public_id,
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
        self.client.force_login(self.business_manager_user)
        self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Sheet Audit",
                "owner": self.business_manager_colleague.public_id,
                **org_formset_data([(self.org, "PRIMARY")]),
                "terug_url": reverse("assignment-list"),
            },
        )
        assignment = Assignment.objects.get(name="Sheet Audit")
        event = Event.objects.get(object_type="Assignment", action="create", object_id=assignment.id)
        assert event.context["name"] == "Sheet Audit"

    def test_sheet_post_validation_no_org_rerenders_form(self):
        self.client.force_login(self.business_manager_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Zonder Opdrachtgever",
                "owner": self.business_manager_colleague.public_id,
                **org_formset_data([]),
                "terug_url": reverse("assignment-list"),
            },
        )
        # Invalid form: re-render (200), no assignment created.
        assert response.status_code == 200
        assert not Assignment.objects.filter(name="Zonder Opdrachtgever").exists()
        # The org error must render id-wired (unmet + invalid), or
        # nldd-form-field shows it at height 0 and "Aanmaken" appears dead.
        html = response.content.decode()
        assert 'id="error-organizations-1"' in html
        assert 'unmet="error-organizations-1"' in html
        # The template splits the picker div's attributes over lines, so match
        # the element rather than one flat substring.
        picker = re.search(r'<div id="assignment-org-picker"(.*?)>', html, re.DOTALL)
        assert picker is not None
        assert "invalid" in picker.group(1)

    def test_sheet_post_unsafe_terug_url_falls_back_to_list(self):
        # _safe_return_path rejects a protocol-relative terug_url, so the
        # HX-Location falls back to the list.
        self.client.force_login(self.business_manager_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Onveilige Terug",
                "owner": self.business_manager_colleague.public_id,
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
        self.client.force_login(self.business_manager_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Banner Opdracht",
                "owner": self.business_manager_colleague.public_id,
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
        # The panel that opens is the opdracht, so the banner carries no link to it.
        assert 'text="Bekijk opdracht"' not in html

    def test_success_message_asks_for_an_aanvraag(self):
        """Aanvragen lists aanvragen only, so until entering asks for the roles
        (PR C) the message tells a new opdracht needs one to show up there."""
        self.client.force_login(self.business_manager_user)
        self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Opdracht Zonder Rol",
                "owner": self.business_manager_colleague.public_id,
                **org_formset_data([(self.org, "PRIMARY")]),
                "terug_url": reverse("assignment-list"),
            },
        )
        assignment = Assignment.objects.get(name="Opdracht Zonder Rol")
        panel = self.client.get(
            reverse("assignment-list"),
            {"opdracht": assignment.public_id},
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        self.assertContains(panel, "Voeg een aanvraag toe. Zonder aanvraag staat de opdracht niet bij Aanvragen.")

    # --- daarna: the create form reached from "Bij welke opdracht?" ---
    # ``daarna`` (aanvraag | plaatsing) says which add-sheet follows the save.

    def create_panel(self, **params):
        self.client.force_login(self.business_manager_user)
        response = self.client.get(
            reverse("assignment-list"),
            {"nieuwe-opdracht": "", **params},
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 200
        return response.content.decode()

    def post_create(self, name, **data):
        self.client.force_login(self.business_manager_user)
        return self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": name,
                "owner": self.business_manager_colleague.public_id,
                **org_formset_data([(self.org, "PRIMARY")]),
                "terug_url": reverse("assignment-list"),
                **data,
            },
        )

    def test_daarna_gives_heading_and_hidden_input(self):
        html = self.create_panel(daarna="plaatsing")
        assert re.search(r'<nldd-top-title-bar[^>]*text="Nieuwe opdracht invoeren"', html)
        assert '<input type="hidden" name="daarna" value="plaatsing">' in html
        assert 'text="Opdracht invoeren"' not in html

    def test_without_daarna_the_form_is_as_before(self):
        html = self.create_panel()
        assert re.search(r'<nldd-top-title-bar[^>]*text="Opdracht invoeren"', html)
        assert 'name="daarna"' not in html

    def test_unknown_daarna_is_ignored(self):
        html = self.create_panel(daarna="onzin")
        assert re.search(r'<nldd-top-title-bar[^>]*text="Opdracht invoeren"', html)
        assert 'name="daarna"' not in html

    def test_daarna_survives_a_rejected_form(self):
        self.client.force_login(self.business_manager_user)
        response = self.client.post(
            reverse("assignment-create-sheet"),
            {
                "name": "Zonder Opdrachtgever",
                "owner": self.business_manager_colleague.public_id,
                **org_formset_data([]),
                "terug_url": reverse("assignment-list"),
                "daarna": "aanvraag",
            },
        )
        assert response.status_code == 200
        html = response.content.decode()
        assert '<input type="hidden" name="daarna" value="aanvraag">' in html
        assert re.search(r'<nldd-top-title-bar[^>]*text="Nieuwe opdracht invoeren"', html)
        # The way back to "Bij welke opdracht?" stays, though a POST is no
        # step in the panel stack.
        bar = re.search(r"<nldd-top-title-bar\b[^>]*>", html).group(0)
        assert 'back-text="Aanvraag toevoegen"' in bar
        assert f'data-back-url="{reverse("assignment-list")}?nieuwe-aanvraag="' in bar

    def test_daarna_aanvraag_goes_on_to_the_aanvraag_sheet(self):
        response = self.post_create("Met Aanvraag", daarna="aanvraag")
        assert response.status_code == 204
        assignment = Assignment.objects.get(name="Met Aanvraag")
        location = json.loads(response["HX-Location"])
        assert (
            location["path"] == f"{reverse('assignment-list')}?opdracht={assignment.public_id}&teamlid=nieuw-aanvraag"
        )
        assert location["target"] == "#side-panel-content"

    def test_daarna_plaatsing_goes_on_to_the_placement_sheet_keeping_the_page(self):
        terug = f"{reverse('bezetting')}?merk=x"
        response = self.post_create("Met Plaatsing", daarna="plaatsing", terug_url=terug)
        assignment = Assignment.objects.get(name="Met Plaatsing")
        location = json.loads(response["HX-Location"])
        assert location["path"] == f"{terug}&opdracht={assignment.public_id}&teamlid=nieuw-ingevuld"

    def test_sheet_after_daarna_goes_back_to_the_new_opdracht(self):
        """Terug in the add-sheet leads to the opdracht, not to the create form
        that was already sent."""
        response = self.post_create("Terug Naar Opdracht", daarna="aanvraag")
        path = json.loads(response["HX-Location"])["path"]
        sheet = self.client.get(path, headers={"hx-request": "true", "hx-target": "side-panel-content"})
        assignment = Assignment.objects.get(name="Terug Naar Opdracht")
        bar = re.search(r"<nldd-top-title-bar\b[^>]*>", sheet.content.decode()).group(0)
        assert 'text="Aanvraag toevoegen"' in bar
        assert f'data-back-url="{reverse("assignment-list")}?opdracht={assignment.public_id}"' in bar

    def test_the_sheet_after_daarna_shows_the_message(self):
        """The add-sheet is where the user lands, so the confirmation rides
        along with it."""
        response = self.post_create("Met Melding", daarna="aanvraag")
        path = json.loads(response["HX-Location"])["path"]
        sheet = self.client.get(path, headers={"hx-request": "true", "hx-target": "side-panel-content"})
        assert 'Opdracht "Met Melding" is aangemaakt.' in sheet.content.decode().replace("&#34;", '"')

    def test_message_with_daarna_leaves_out_the_aanvraag_hint(self):
        response = self.post_create("Stap Op Weg", daarna="plaatsing")
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        assert texts == ['Opdracht "Stap Op Weg" is aangemaakt.']

    def test_unknown_daarna_on_post_behaves_as_without(self):
        response = self.post_create("Onzin Daarna", daarna="onzin")
        assignment = Assignment.objects.get(name="Onzin Daarna")
        location = json.loads(response["HX-Location"])
        assert location["path"] == f"{reverse('assignment-list')}?opdracht={assignment.public_id}"
        (text,) = [str(m) for m in get_messages(response.wsgi_request)]
        assert text.startswith('Opdracht "Onzin Daarna" is aangemaakt.')
        assert "Voeg een aanvraag toe. Zonder aanvraag staat de opdracht niet bij Aanvragen." in text

    def test_post_with_daarna_requires_add_assignment_permission(self):
        self.client.force_login(self.regular_user)
        response = self.client.post(reverse("assignment-create-sheet"), {"daarna": "aanvraag"})
        assert response.status_code == 403


class AssignmentListButtonTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()

        self.business_manager_user = User.objects.create(
            email="business_manager@rijksoverheid.nl",
        )
        add_assignment = Permission.objects.get(codename="add_assignment")
        self.business_manager_user.user_permissions.add(add_assignment)

        self.regular_user = User.objects.create(
            email="regular@rijksoverheid.nl",
        )

    def test_bdm_sees_create_button(self):
        # Since K1 the primary action is the split button "Aanvraag toevoegen";
        # "Opdracht invoeren" is an item in its menu.
        self.client.force_login(self.business_manager_user)
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        html = response.content.decode()
        assert re.search(r'<nldd-split-button[^>]*text="Aanvraag toevoegen"', html)
        assert re.search(r'<nldd-menu-item text="Opdracht invoeren"', html)

    def test_create_button_targets_list_sentinel(self):
        # The menu item opens the create sheet as a panel on the list
        # (?nieuwe-opdracht), not via /invoeren/?terug=.
        self.client.force_login(self.business_manager_user)
        response = self.client.get(reverse("assignment-list"))
        html = response.content.decode()
        item = re.search(r'<nldd-menu-item text="Opdracht invoeren"[^>]*>', html).group(0)
        assert "nieuwe-opdracht" in item
        # side_panel.js pushes the URL; htmx pushing it broke browser-back.
        assert 'hx-push-url="false"' in item
        assert "invoeren/?terug=" not in html

    def test_regular_user_does_not_see_create_button(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        assert b"Opdracht invoeren" not in response.content
        assert b"<nldd-split-button" not in response.content
