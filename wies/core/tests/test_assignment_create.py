from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    Skill,
    User,
)
from wies.core.roles import setup_roles

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


class AssignmentCreateTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()

        self.bdm_user = User.objects.create(
            username="bdm_user",
            email="bdm@rijksoverheid.nl",
            first_name="BDM",
            last_name="User",
        )
        add_assignment = Permission.objects.get(codename="add_assignment")
        add_service = Permission.objects.get(codename="add_service")
        add_placement = Permission.objects.get(codename="add_placement")
        self.bdm_user.user_permissions.add(add_assignment, add_service, add_placement)

        self.regular_user = User.objects.create(
            username="regular_user",
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
        assert b"Nieuwe opdracht" in response.content

    def test_post_creates_assignment_with_open_service(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Test Opdracht",
                "owner": self.bdm_colleague.id,
                "primary_organization": self.org.id,
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
                "primary_organization": self.org.id,
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
                **FORMSET_MGMT_1,
                "service-0-description": "Dienst",
                "service-0-skill": self.skill.id,
                "primary_organization": self.org.id,
                "involved_organization": self.org2.id,
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
                "primary_organization": self.org.id,
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
                "service-TOTAL_FORMS": "1",
                "service-INITIAL_FORMS": "0",
                "service-MIN_NUM_FORMS": "1",
                "service-MAX_NUM_FORMS": "1000",
                "service-0-description": "",
            },
        )
        # Formset is valid (empty form ignored) but no services_data → re-renders with error
        assert response.status_code == 200
        assert Assignment.objects.count() == 0

    def test_post_creates_new_skill_inline(self):
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Opdracht Nieuwe Rol",
                "owner": self.bdm_colleague.id,
                "primary_organization": self.org.id,
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
                **FORMSET_MGMT_1,
                "service-0-skill": self.skill.id,
                "service-0-description": "Dienst",
            },
        )
        assert response.status_code == 200
        assert Assignment.objects.count() == 0

    def test_post_multiple_primary_orgs_demotes_to_involved(self):
        """Extra primary_organization values beyond the first become INVOLVED."""
        self.client.force_login(self.bdm_user)
        response = self.client.post(
            reverse("assignment-create"),
            {
                "name": "Multi Primary Opdracht",
                "owner": self.bdm_colleague.id,
                **FORMSET_MGMT_1,
                "service-0-skill": self.skill.id,
                "service-0-description": "Dienst",
                "primary_organization": [self.org.id, self.org2.id],
            },
        )
        assert response.status_code == 302
        assignment = Assignment.objects.get(name="Multi Primary Opdracht")
        primary = AssignmentOrganizationUnit.objects.get(assignment=assignment, role="PRIMARY")
        assert primary.organization == self.org
        involved = AssignmentOrganizationUnit.objects.get(assignment=assignment, role="INVOLVED")
        assert involved.organization == self.org2

    def test_source_wies_on_service_and_placement(self):
        """source='wies' is set on Service and Placement, not just Assignment."""
        self.client.force_login(self.bdm_user)
        self.client.post(
            reverse("assignment-create"),
            {
                "name": "Source Check",
                "owner": self.bdm_colleague.id,
                "primary_organization": self.org.id,
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
            username="bdm_user",
            email="bdm@rijksoverheid.nl",
        )
        add_assignment = Permission.objects.get(codename="add_assignment")
        self.bdm_user.user_permissions.add(add_assignment)

        self.regular_user = User.objects.create(
            username="regular_user",
            email="regular@rijksoverheid.nl",
        )

    def test_bdm_sees_create_button(self):
        self.client.force_login(self.bdm_user)
        response = self.client.get(reverse("assignment-list"))
        assert b"Opdracht toevoegen" in response.content

    def test_regular_user_does_not_see_create_button(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("assignment-list"))
        assert b"Opdracht toevoegen" not in response.content
