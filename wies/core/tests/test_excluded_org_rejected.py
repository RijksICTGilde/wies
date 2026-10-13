"""An excluded organization (intelligence service, or a unit underneath one)
can not be set as opdrachtgever: the form field and the CSV import refuse it."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.fields import OrganizationsField
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    Placement,
    Service,
)
from wies.core.services.placements import create_assignments_from_csv

User = get_user_model()

AIVD_URL = "https://organisaties.overheid.nl/9633/Algemene_Inlichtingen-_en_Veiligheidsdienst"
NORMAL_URL = "https://organisaties.overheid.nl/1/Ministerie_van_Test"

CSV_HEADERS = (
    "assignment_name,assignment_description,assignment_owner,assignment_owner_email,"
    "client_1_url,client_2_url,assignment_start_date,assignment_end_date,service_skill,"
    "placement_colleague_name,placement_colleague_email"
)


def _csv_row(name, client_1_url="", client_2_url=""):
    return (
        f"{name},Omschrijving,Owner Name,owner@rijksoverheid.nl,{client_1_url},{client_2_url},"
        "01-01-2025,31-12-2025,Python,John Doe,john@rijksoverheid.nl"
    )


class ExcludedOrgTestCase(TestCase):
    def setUp(self):
        self.aivd = OrganizationUnit.objects.create(
            name="Algemene Inlichtingen- en Veiligheidsdienst", abbreviations=["AIVD"], source_url=AIVD_URL
        )
        self.aivd_child = OrganizationUnit.objects.create(name="Directie Inlichtingen", parent=self.aivd)
        self.normal = OrganizationUnit.objects.create(name="Ministerie van Test", source_url=NORMAL_URL)


class OrganizationsFieldExcludedOrgTests(ExcludedOrgTestCase):
    def _assert_unknown_org(self, value):
        with pytest.raises(ValidationError) as ctx:
            OrganizationsField(required=True).clean(value)
        assert ctx.value.code == "unknown_org"

    def test_excluded_org_as_primary_is_refused(self):
        self._assert_unknown_org([{"organization": str(self.aivd.public_id), "role": "PRIMARY"}])

    def test_excluded_org_as_involved_is_refused(self):
        self._assert_unknown_org(
            [
                {"organization": str(self.normal.public_id), "role": "PRIMARY"},
                {"organization": str(self.aivd.public_id), "role": "INVOLVED"},
            ]
        )

    def test_descendant_of_excluded_org_is_refused(self):
        self._assert_unknown_org([{"organization": str(self.aivd_child.public_id), "role": "PRIMARY"}])

    def test_normal_org_is_accepted(self):
        cleaned = OrganizationsField(required=True).clean(
            [{"organization": str(self.normal.public_id), "role": "PRIMARY"}]
        )
        assert cleaned[0]["organization"] == self.normal


class InlineEditExcludedOrgTests(ExcludedOrgTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user(email="orgs@rijksoverheid.nl", first_name="O", last_name="O")
        self.user.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        self.client.force_login(self.user)
        self.assignment = Assignment.objects.create(
            name="Orgs test", owner=Colleague.objects.get(user=self.user), source="wies"
        )
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=self.normal, role="PRIMARY")
        self.url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "organizations"])

    def test_post_with_excluded_org_shows_error_and_saves_nothing(self):
        resp = self.client.post(
            self.url,
            {"org-TOTAL_FORMS": "1", "org-0-organization": self.aivd.public_id, "org-0-role": "PRIMARY"},
        )

        assert resp.status_code == 200
        self.assertContains(resp, "Onbekende organisatie geselecteerd.")
        linked = AssignmentOrganizationUnit.objects.filter(assignment=self.assignment)
        assert [rel.organization_id for rel in linked] == [self.normal.id]


class CsvImportExcludedOrgTests(ExcludedOrgTestCase):
    def test_excluded_primary_client_fails_the_import(self):
        result = create_assignments_from_csv(None, CSV_HEADERS + "\n" + _csv_row("Geheim", client_1_url=AIVD_URL))

        assert result["success"] is False
        assert "Rij 2" in result["errors"][0]
        assert not Assignment.objects.exists()
        assert not Service.objects.exists()
        assert not Placement.objects.exists()

    def test_excluded_involved_client_fails_the_import(self):
        result = create_assignments_from_csv(
            None, CSV_HEADERS + "\n" + _csv_row("Geheim", client_1_url=NORMAL_URL, client_2_url=AIVD_URL)
        )

        assert result["success"] is False
        assert not Assignment.objects.exists()

    def test_excluded_row_rolls_back_the_rows_before_it(self):
        content = "\n".join(
            [CSV_HEADERS, _csv_row("Gewoon", client_1_url=NORMAL_URL), _csv_row("Geheim", client_1_url=AIVD_URL)]
        )

        result = create_assignments_from_csv(None, content)

        assert result["success"] is False
        assert "Rij 3" in result["errors"][0]
        assert not Assignment.objects.exists()

    def test_normal_client_still_imports(self):
        result = create_assignments_from_csv(None, CSV_HEADERS + "\n" + _csv_row("Gewoon", client_1_url=NORMAL_URL))

        assert result["success"] is True
        assert result["organizations_linked"] == 1
