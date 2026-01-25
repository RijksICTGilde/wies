"""Tests for Organization model and related functionality."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from wies.core.models import (
    Assignment,
    AssignmentOrganization,
    Colleague,
    Ministry,
    Organization,
    OrganizationRole,
    OrganizationType,
    User,
)


class OrganizationModelTest(TestCase):
    """Tests for the Organization model."""

    def test_create_root_organization(self):
        """Ministerie without parent can be created."""
        org = Organization.objects.create(
            name="Ministerie van BZK",
            abbreviation="BZK",
            organization_type=OrganizationType.MINISTERIE,
        )
        assert org.parent is None
        assert org.get_root() == org

    def test_create_child_organization(self):
        """Directoraat-Generaal under Ministerie is correctly linked."""
        ministry = Organization.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        dg = Organization.objects.create(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        assert dg.parent == ministry
        assert dg in ministry.children.all()

    def test_circular_reference_rejected(self):
        """Circular reference is rejected."""
        org1 = Organization.objects.create(name="Org1", organization_type=OrganizationType.DIRECTIE)
        org2 = Organization.objects.create(name="Org2", organization_type=OrganizationType.AFDELING, parent=org1)
        org1.parent = org2
        with pytest.raises(ValidationError):
            org1.full_clean()

    def test_hierarchy_validation_dg_under_ministry(self):
        """Directoraat-Generaal can only be placed under Ministerie."""
        ministry = Organization.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        dg = Organization(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        # Should not raise - DG under ministry is valid
        dg.full_clean()

    def test_hierarchy_validation_dg_under_afdeling_rejected(self):
        """Directoraat-Generaal cannot be placed under Afdeling."""
        afdeling = Organization.objects.create(name="Afdeling X", organization_type=OrganizationType.AFDELING)
        dg = Organization(
            name="DG Y",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=afdeling,
        )
        with pytest.raises(ValidationError):
            dg.full_clean()

    def test_root_type_cannot_have_parent(self):
        """Root types (ministerie, gemeente, etc.) cannot have a parent."""
        ministry1 = Organization.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        ministry2 = Organization(
            name="EZK",
            organization_type=OrganizationType.MINISTERIE,
            parent=ministry1,
        )
        with pytest.raises(ValidationError):
            ministry2.full_clean()

    def test_get_full_path(self):
        """get_full_path() returns correct breadcrumb."""
        ministry = Organization.objects.create(
            name="BZK", abbreviation="BZK", organization_type=OrganizationType.MINISTERIE
        )
        dg = Organization.objects.create(
            name="DGDOO",
            abbreviation="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        directie = Organization.objects.create(
            name="Directie DO",
            organization_type=OrganizationType.DIRECTIE,
            parent=dg,
        )
        assert directie.get_full_path() == "BZK > DGDOO > Directie DO"

    def test_rename_preserves_history(self):
        """rename() preserves old name in previous_names."""
        org = Organization.objects.create(name="Digitale Overheid", organization_type=OrganizationType.DIRECTIE)
        org.rename("Publieke Dienstverlening")
        org.refresh_from_db()
        assert org.name == "Publieke Dienstverlening"
        assert len(org.previous_names) == 1
        assert org.previous_names[0]["name"] == "Digitale Overheid"

    def test_oin_validation_invalid(self):
        """OIN must be exactly 20 digits - invalid rejected."""
        org = Organization(
            name="Test",
            organization_type=OrganizationType.MINISTERIE,
            oin_number="123",
        )
        with pytest.raises(ValidationError):
            org.full_clean()

    def test_oin_validation_valid(self):
        """OIN with exactly 20 digits is accepted."""
        org = Organization(
            name="Test",
            organization_type=OrganizationType.MINISTERIE,
            oin_number="00000001234567890123",
        )
        org.full_clean()  # Should not raise

    def test_predecessor_successor_chain(self):
        """Test merger scenario: Weesp -> Amsterdam."""
        amsterdam = Organization.objects.create(name="Amsterdam", organization_type=OrganizationType.GEMEENTE)
        weesp = Organization.objects.create(
            name="Weesp",
            organization_type=OrganizationType.GEMEENTE,
            successor=amsterdam,
            is_active=False,
        )

        # From Weesp perspective (is_active=False means dissolved)
        assert not weesp.is_active
        assert weesp.has_successor
        assert weesp.get_current_successor() == amsterdam

        # From Amsterdam perspective
        assert amsterdam.has_predecessors
        assert weesp in amsterdam.get_predecessors()

    def test_multiple_predecessors(self):
        """Test multiple merger: Cuijk + Boxmeer + etc -> Land van Cuijk."""
        land_van_cuijk = Organization.objects.create(
            name="Land van Cuijk",
            organization_type=OrganizationType.GEMEENTE,
        )
        predecessor_names = [
            "Cuijk",
            "Boxmeer",
            "Sint Anthonis",
            "Grave",
            "Mill en Sint Hubert",
        ]
        for name in predecessor_names:
            Organization.objects.create(
                name=name,
                organization_type=OrganizationType.GEMEENTE,
                successor=land_van_cuijk,
                is_active=False,
            )

        assert land_van_cuijk.predecessors.count() == 5
        assert len(land_van_cuijk.get_all_predecessors()) == 5

    def test_get_ancestors(self):
        """get_ancestors() returns all ancestors in order."""
        ministry = Organization.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        dg = Organization.objects.create(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        directie = Organization.objects.create(
            name="Directie DO",
            organization_type=OrganizationType.DIRECTIE,
            parent=dg,
        )
        afdeling = Organization.objects.create(
            name="Afdeling DI",
            organization_type=OrganizationType.AFDELING,
            parent=directie,
        )

        ancestors = list(afdeling.get_ancestors())
        assert len(ancestors) == 3
        assert ancestors[0] == directie
        assert ancestors[1] == dg
        assert ancestors[2] == ministry

    def test_get_descendants(self):
        """get_descendants() returns all descendants recursively."""
        ministry = Organization.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        dg = Organization.objects.create(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        directie = Organization.objects.create(
            name="Directie DO",
            organization_type=OrganizationType.DIRECTIE,
            parent=dg,
        )

        descendants = ministry.get_descendants()
        assert len(descendants) == 2
        assert dg in descendants
        assert directie in descendants

    def test_str_with_abbreviation(self):
        """__str__ includes abbreviation when present."""
        org = Organization.objects.create(
            name="Ministerie van BZK",
            abbreviation="BZK",
            organization_type=OrganizationType.MINISTERIE,
        )
        assert str(org) == "Ministerie van BZK (BZK)"

    def test_str_without_abbreviation(self):
        """__str__ shows only name when no abbreviation."""
        org = Organization.objects.create(
            name="Directie Digitale Overheid",
            organization_type=OrganizationType.DIRECTIE,
        )
        assert str(org) == "Directie Digitale Overheid"


class OrganizationQuerySetTest(TestCase):
    """Tests for OrganizationQuerySet methods."""

    def setUp(self):
        """Create test organization hierarchy."""
        self.ministry = Organization.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        self.dg = Organization.objects.create(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=self.ministry,
        )
        self.directie = Organization.objects.create(
            name="Directie DO",
            organization_type=OrganizationType.DIRECTIE,
            parent=self.dg,
        )
        self.inactive_org = Organization.objects.create(
            name="Oude Directie",
            organization_type=OrganizationType.DIRECTIE,
            is_active=False,
        )

    def test_active_filter(self):
        """active() filters to only active organizations."""
        active = Organization.objects.active()
        assert active.count() == 3
        assert self.inactive_org not in active

    def test_roots_filter(self):
        """roots() filters to organizations without parent."""
        roots = Organization.objects.roots()
        assert roots.count() == 2
        assert self.ministry in roots
        assert self.inactive_org in roots

    def test_of_type_filter(self):
        """of_type() filters by organization type."""
        ministries = Organization.objects.of_type(OrganizationType.MINISTERIE)
        assert ministries.count() == 1
        assert self.ministry in ministries

    def test_of_type_multiple_types(self):
        """of_type() accepts multiple types."""
        orgs = Organization.objects.of_type(OrganizationType.MINISTERIE, OrganizationType.DIRECTIE)
        assert orgs.count() == 3

    def test_with_descendants(self):
        """with_descendants() returns all IDs including descendants."""
        all_ids = Organization.objects.with_descendants([self.ministry.id])
        assert len(all_ids) == 3
        assert self.ministry.id in all_ids
        assert self.dg.id in all_ids
        assert self.directie.id in all_ids


class AssignmentOrganizationTest(TestCase):
    """Tests for AssignmentOrganization through model."""

    def setUp(self):
        """Create test data."""
        self.ministry_legacy = Ministry.objects.create(name="BZK", abbreviation="BZK")
        self.user = User.objects.create_user(username="test", email="test@example.com", password="test")
        self.colleague = Colleague.objects.create(
            name="Test Colleague",
            email="colleague@example.com",
            source="wies",
        )
        self.org = Organization.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)

    def test_assignment_primary_organization(self):
        """get_primary_organization() returns PRIMARY relation."""
        assignment = Assignment.objects.create(
            name="Test Opdracht",
            ministry=self.ministry_legacy,
            owner=self.colleague,
            source="wies",
        )
        AssignmentOrganization.objects.create(
            assignment=assignment,
            organization=self.org,
            role=OrganizationRole.PRIMARY,
        )
        assert assignment.get_primary_organization() == self.org

    def test_assignment_no_primary_organization(self):
        """get_primary_organization() returns None when no PRIMARY relation."""
        assignment = Assignment.objects.create(
            name="Test Opdracht",
            ministry=self.ministry_legacy,
            owner=self.colleague,
            source="wies",
        )
        assert assignment.get_primary_organization() is None

    def test_multiple_organizations_per_assignment(self):
        """Assignment can have multiple organizations with different roles."""
        org2 = Organization.objects.create(name="EZK", organization_type=OrganizationType.MINISTERIE)
        assignment = Assignment.objects.create(
            name="Test",
            ministry=self.ministry_legacy,
            owner=self.colleague,
            source="wies",
        )
        AssignmentOrganization.objects.create(
            assignment=assignment, organization=self.org, role=OrganizationRole.PRIMARY
        )
        AssignmentOrganization.objects.create(assignment=assignment, organization=org2, role=OrganizationRole.INVOLVED)
        assert assignment.organization_relations.count() == 2

    def test_assignment_organization_str(self):
        """AssignmentOrganization __str__ is descriptive."""
        assignment = Assignment.objects.create(
            name="Test Opdracht",
            ministry=self.ministry_legacy,
            owner=self.colleague,
            source="wies",
        )
        rel = AssignmentOrganization.objects.create(
            assignment=assignment,
            organization=self.org,
            role=OrganizationRole.PRIMARY,
        )
        assert "Test Opdracht" in str(rel)
        assert "BZK" in str(rel)
        assert "Primaire organisatie" in str(rel)

    def test_only_one_primary_organization_allowed(self):
        """Only one PRIMARY organization per assignment is allowed."""
        org2 = Organization.objects.create(name="EZK", organization_type=OrganizationType.MINISTERIE)
        assignment = Assignment.objects.create(
            name="Test",
            ministry=self.ministry_legacy,
            owner=self.colleague,
            source="wies",
        )
        # First PRIMARY is OK
        AssignmentOrganization.objects.create(
            assignment=assignment, organization=self.org, role=OrganizationRole.PRIMARY
        )
        # Second PRIMARY should fail at database level
        with pytest.raises(IntegrityError):
            AssignmentOrganization.objects.create(
                assignment=assignment, organization=org2, role=OrganizationRole.PRIMARY
            )
