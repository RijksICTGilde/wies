from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
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
        data[f"org-{i}-organization"] = org.id
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

    def test_requires_login(self):
        response = self.client.get(reverse("assignment-create"))
        assert response.status_code == 302

    def test_requires_add_assignment_permission(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("assignment-create"))
        assert response.status_code == 403

    def test_get_returns_form(self):
        self.client.force_login(self.bdm_user)
        response = self.client.get(reverse("assignment-create"))
        assert response.status_code == 200
        assert b"Opdracht invoeren" in response.content

    def test_post_creates_assignment_with_open_service(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Test Opdracht",
                "owner": self.bdm_colleague.id,
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_1,
                "service-0-description": "Backend ontwikkeling",
                "service-0-skill": self.skill.id,
            },
        )
        assert response.status_code == 302
        assignment = Assignment.objects.get(name="Test Opdracht")
        assert assignment.source == "wies"
        service = assignment.services.first()
        assert service.description == "Backend ontwikkeling"
        assert service.skill == self.skill
        assert service.status == "OPEN"
        assert service.placements.count() == 0

    def test_post_creates_assignment_with_placement(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Ingevulde Opdracht",
                "owner": self.bdm_colleague.id,
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_1,
                "service-0-description": "Backend ontwikkeling",
                "service-0-skill": self.skill.id,
                "service-0-is_filled": "on",
                "service-0-colleague": self.colleague.id,
            },
        )
        assert response.status_code == 302
        assignment = Assignment.objects.get(name="Ingevulde Opdracht")
        service = assignment.services.first()
        assert service.status == "OPEN"
        assert service.placements.first().colleague == self.colleague

    def test_post_with_organizations(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Opdracht met Org",
                "owner": self.bdm_colleague.id,
                **org_formset_data([(self.org, "PRIMARY"), (self.org2, "INVOLVED")]),
                **FORMSET_MGMT_1,
                "service-0-description": "Dienst",
                "service-0-skill": self.skill.id,
            },
        )
        assert response.status_code == 302
        assignment = Assignment.objects.get(name="Opdracht met Org")
        primary = AssignmentOrganizationUnit.objects.get(assignment=assignment, role="PRIMARY")
        assert primary.organization == self.org
        involved = AssignmentOrganizationUnit.objects.get(assignment=assignment, role="INVOLVED")
        assert involved.organization == self.org2

    def test_post_multiple_services(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Multi Service Opdracht",
                "owner": self.bdm_colleague.id,
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_2,
                "service-0-description": "Frontend",
                "service-0-skill": self.skill.id,
                "service-1-description": "Backend",
                "service-1-skill": self.skill.id,
            },
        )
        assert response.status_code == 302
        assignment = Assignment.objects.get(name="Multi Service Opdracht")
        assert assignment.services.count() == 2

    def test_post_validation_missing_name(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "",
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_1,
                "service-0-skill": self.skill.id,
                "service-0-description": "Dienst",
            },
        )
        assert response.status_code == 200
        assert Assignment.objects.count() == 0

    def test_post_validation_no_org(self):
        """Submitting without an org should fail validation."""
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Opdracht Zonder Org",
                "owner": self.bdm_colleague.id,
                "org-TOTAL_FORMS": "0",
                "org-INITIAL_FORMS": "0",
                "org-MIN_NUM_FORMS": "1",
                "org-MAX_NUM_FORMS": "1000",
                **FORMSET_MGMT_1,
                "service-0-skill": self.skill.id,
                "service-0-description": "Dienst",
            },
        )
        assert response.status_code == 200
        assert Assignment.objects.count() == 0

    def test_post_validation_no_services(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Opdracht Zonder Dienst",
                **org_formset_data([(self.org, "PRIMARY")]),
                "service-TOTAL_FORMS": "1",
                "service-INITIAL_FORMS": "0",
                "service-MIN_NUM_FORMS": "1",
                "service-MAX_NUM_FORMS": "1000",
                "service-0-description": "",
            },
        )
        assert response.status_code == 200
        assert Assignment.objects.count() == 0

    def test_post_creates_new_skill_inline(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Opdracht Nieuwe Rol",
                "owner": self.bdm_colleague.id,
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_1,
                "service-0-description": "Nieuwe dienst",
                "service-0-skill": "__new__",
                "service-0-new_skill_name": "Blockchain Developer",
            },
        )
        assert response.status_code == 302
        assert Skill.objects.filter(name="Blockchain Developer").exists()
        service = Assignment.objects.get(name="Opdracht Nieuwe Rol").services.first()
        assert service.skill.name == "Blockchain Developer"

    def test_post_validation_end_before_start(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Datum Opdracht",
                "start_date": "2026-06-01",
                "end_date": "2026-01-01",
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_1,
                "service-0-skill": self.skill.id,
                "service-0-description": "Dienst",
            },
        )
        assert response.status_code == 200
        assert Assignment.objects.count() == 0

    def test_invalid_org_id_rejected(self):
        """Non-existent org IDs should not create an assignment."""
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Test Opdracht",
                "owner": self.bdm_colleague.id,
                "org-TOTAL_FORMS": "1",
                "org-INITIAL_FORMS": "0",
                "org-MIN_NUM_FORMS": "1",
                "org-MAX_NUM_FORMS": "1000",
                "org-0-organization": "99999",
                "org-0-role": "PRIMARY",
                **FORMSET_MGMT_1,
                "service-0-skill": self.skill.id,
                "service-0-description": "Dienst",
            },
        )
        assert response.status_code == 200
        assert Assignment.objects.count() == 0

    def test_formset_size_capped_at_100(self):
        """Submitting TOTAL_FORMS > 100 should not crash the server."""
        self.client.force_login(self.bdm_user)
        data = {
            "name": "Test Opdracht",
            "owner": self.bdm_colleague.id,
            **org_formset_data([(self.org, "PRIMARY")]),
            "service-TOTAL_FORMS": "9999",
            "service-INITIAL_FORMS": "0",
            "service-MIN_NUM_FORMS": "1",
            "service-MAX_NUM_FORMS": "1000",
            "service-0-skill": self.skill.id,
            "service-0-description": "Dienst",
        }
        response = self.client.post(reverse("assignment-create"), data)
        assert response.status_code in (200, 302)

    def test_new_skill_empty_name_rejected(self):
        """Selecting __new__ without providing a skill name should fail validation."""
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Test Opdracht",
                "owner": self.bdm_colleague.id,
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_1,
                "service-0-skill": "__new__",
                "service-0-new_skill_name": "",
                "service-0-description": "Dienst",
            },
        )
        assert response.status_code == 200
        assert Assignment.objects.count() == 0
        assert Skill.objects.filter(name="").count() == 0

    def test_is_filled_without_consultant_rejected(self):
        """Checking 'role filled' without selecting a consultant should fail validation."""
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Test Opdracht",
                "owner": self.bdm_colleague.id,
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_1,
                "service-0-skill": self.skill.id,
                "service-0-is_filled": "on",
                # no service-0-colleague
            },
        )
        assert response.status_code == 200
        assert Assignment.objects.count() == 0

    def test_source_wies_on_service_and_placement(self):
        """source='wies' is set on Service and Placement, not just Assignment."""
        self.client.force_login(self.bdm_user)
        self.client.post(
            reverse("assignment-create"),
            {
                "name": "Source Check",
                "owner": self.bdm_colleague.id,
                **org_formset_data([(self.org, "PRIMARY")]),
                **FORMSET_MGMT_1,
                "service-0-skill": self.skill.id,
                "service-0-description": "Dienst",
                "service-0-is_filled": "on",
                "service-0-colleague": self.colleague.id,
            },
        )
        assignment = Assignment.objects.get(name="Source Check")
        service = assignment.services.first()
        assert service.source == "wies"
        placement = service.placements.first()
        assert placement.source == "wies"


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
        assert b"Opdracht invoeren" in response.content

    def test_regular_user_does_not_see_create_button(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("assignment-list"))
        assert b"Opdracht invoeren" not in response.content
