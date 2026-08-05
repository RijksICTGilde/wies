"""Tests for the BM "Opdrachten" subpage (assignments per primary client)."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    OrganizationType,
    OrganizationUnit,
    OrganizationUnitRole,
)
from wies.core.services.opdrachten_per_client import PALETTE_LEN, assignments_per_primary_client

User = get_user_model()


class AssignmentsPerPrimaryClientServiceTest(TestCase):
    def setUp(self):
        # Live overheid.nl sync lowercases ``name`` but capitalises ``label``;
        # the service filters on ``label``, so mirror that here.
        self.ministerie_type = OrganizationType.objects.create(name="ministerie", label="Ministerie")
        self.agentschap_type = OrganizationType.objects.create(name="agentschap", label="Agentschap")

        # Two ministries: one with opdrachten, one without.
        self.ocw = OrganizationUnit.objects.create(name="Onderwijs, Cultuur en Wetenschap", abbreviations=["OCW"])
        self.ocw.organization_types.add(self.ministerie_type)
        self.bzk = OrganizationUnit.objects.create(name="Binnenlandse Zaken", abbreviations=["BZK"])
        self.bzk.organization_types.add(self.ministerie_type)

        # Two agentschappen: one with an opdracht, one without.
        self.rws = OrganizationUnit.objects.create(name="Rijkswaterstaat", abbreviations=["RWS"])
        self.rws.organization_types.add(self.agentschap_type)
        self.dienst = OrganizationUnit.objects.create(name="Loze Dienst", abbreviations=["LD"])
        self.dienst.organization_types.add(self.agentschap_type)

    def _assignment_with_primary(self, org):
        assignment = Assignment.objects.create(name=f"Opdracht {org.name}", source="wies")
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=org, role=OrganizationUnitRole.PRIMARY
        )
        return assignment

    def test_all_ministries_included_even_with_zero(self):
        self._assignment_with_primary(self.ocw)
        data = assignments_per_primary_client()
        by_name = {c.name: c.count for c in data["ministeries"]}
        assert by_name == {"OCW": 1, "BZK": 0}

    def test_only_agentschappen_with_at_least_one(self):
        self._assignment_with_primary(self.rws)
        data = assignments_per_primary_client()
        names = [c.name for c in data["agentschappen"]]
        assert names == ["RWS"]  # LD (0 opdrachten) is excluded

    def test_only_primary_role_counts(self):
        assignment = self._assignment_with_primary(self.ocw)
        # An INVOLVED relation on BZK must NOT bump BZK's count.
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=self.bzk, role=OrganizationUnitRole.INVOLVED
        )
        data = assignments_per_primary_client()
        by_name = {c.name: c.count for c in data["ministeries"]}
        assert by_name["OCW"] == 1
        assert by_name["BZK"] == 0

    def test_color_index_is_stable_per_org(self):
        data = assignments_per_primary_client()
        by_name = {c.name: c.color_index for c in data["ministeries"]}
        # Keyed to the (stable) org id, so it matches org.id % PALETTE_LEN.
        assert by_name["OCW"] == self.ocw.id % PALETTE_LEN
        assert by_name["BZK"] == self.bzk.id % PALETTE_LEN

    def test_defensie_flagged(self):
        defensie = OrganizationUnit.objects.create(name="Defensie", abbreviations=["Def"])
        defensie.organization_types.add(self.ministerie_type)
        data = assignments_per_primary_client()
        flagged = {c.name: c.is_defensie for c in data["ministeries"]}
        assert flagged["Def"] is True
        assert flagged["OCW"] is False


class BmOpdrachtenViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(email="viewer@rijksoverheid.nl", first_name="V", last_name="Iewer")

    def test_page_renders_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("bm-opdrachten"))
        assert response.status_code == 200
        assert b"Ministeries" in response.content
        assert b"Agentschappen" in response.content
