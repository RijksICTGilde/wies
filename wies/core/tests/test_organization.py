"""Tests for OrganizationUnit model and related functionality."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.test import TestCase

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationType,
    OrganizationUnit,
    OrganizationUnitRole,
    User,
)


class OrganizationUnitModelTest(TestCase):
    """Tests for the OrganizationUnit model."""

    def test_create_root_organization(self):
        """Ministerie without parent can be created."""
        org = OrganizationUnit.objects.create(
            name="Ministerie van BZK",
            abbreviations=["BZK"],
            organization_type=OrganizationType.MINISTERIE,
        )
        assert org.parent is None
        assert org.get_root() == org

    def test_create_child_organization(self):
        """Directoraat-Generaal under Ministerie is correctly linked."""
        ministry = OrganizationUnit.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        dg = OrganizationUnit.objects.create(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        assert dg.parent == ministry
        assert dg in ministry.children.all()

    def test_circular_reference_rejected(self):
        """Circular reference is rejected."""
        org1 = OrganizationUnit.objects.create(name="Org1", organization_type=OrganizationType.DIRECTIE)
        org2 = OrganizationUnit.objects.create(name="Org2", organization_type=OrganizationType.AFDELING, parent=org1)
        org1.parent = org2
        with pytest.raises(ValidationError):
            org1.full_clean()

    def test_hierarchy_validation_dg_under_ministry(self):
        """Directoraat-Generaal can only be placed under Ministerie."""
        ministry = OrganizationUnit.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        dg = OrganizationUnit(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        # Should not raise - DG under ministry is valid
        dg.full_clean()

    def test_hierarchy_validation_dg_under_afdeling_rejected(self):
        """Directoraat-Generaal cannot be placed under Afdeling."""
        afdeling = OrganizationUnit.objects.create(name="Afdeling X", organization_type=OrganizationType.AFDELING)
        dg = OrganizationUnit(
            name="DG Y",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=afdeling,
        )
        with pytest.raises(ValidationError):
            dg.full_clean()

    def test_root_type_cannot_have_parent(self):
        """Root types (ministerie, gemeente, etc.) cannot have a parent."""
        ministry1 = OrganizationUnit.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        ministry2 = OrganizationUnit(
            name="EZK",
            organization_type=OrganizationType.MINISTERIE,
            parent=ministry1,
        )
        with pytest.raises(ValidationError):
            ministry2.full_clean()

    def test_get_full_path(self):
        """get_full_path() returns correct breadcrumb."""
        ministry = OrganizationUnit.objects.create(
            name="BZK", abbreviations=["BZK"], organization_type=OrganizationType.MINISTERIE
        )
        dg = OrganizationUnit.objects.create(
            name="DGDOO",
            abbreviations=["DGDOO"],
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        directie = OrganizationUnit.objects.create(
            name="Directie DO",
            organization_type=OrganizationType.DIRECTIE,
            parent=dg,
        )
        assert directie.get_full_path() == "BZK > DGDOO > Directie DO"

    def test_rename_preserves_history(self):
        """rename() preserves old name in previous_names."""
        org = OrganizationUnit.objects.create(name="Digitale Overheid", organization_type=OrganizationType.DIRECTIE)
        org.rename("Publieke Dienstverlening")
        org.refresh_from_db()
        assert org.name == "Publieke Dienstverlening"
        assert len(org.previous_names) == 1
        assert org.previous_names[0]["name"] == "Digitale Overheid"

    def test_oin_validation_invalid(self):
        """OIN must be exactly 20 digits - invalid rejected."""
        org = OrganizationUnit(
            name="Test",
            organization_type=OrganizationType.MINISTERIE,
            oin_number="123",
        )
        with pytest.raises(ValidationError):
            org.full_clean()

    def test_oin_validation_valid(self):
        """OIN with exactly 20 digits is accepted."""
        org = OrganizationUnit(
            name="Test",
            organization_type=OrganizationType.MINISTERIE,
            oin_number="00000001234567890123",
        )
        org.full_clean()  # Should not raise

    def test_predecessor_successor_chain(self):
        """Test merger scenario: Weesp -> Amsterdam."""
        amsterdam = OrganizationUnit.objects.create(name="Amsterdam", organization_type=OrganizationType.GEMEENTE)
        weesp = OrganizationUnit.objects.create(
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
        land_van_cuijk = OrganizationUnit.objects.create(
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
            OrganizationUnit.objects.create(
                name=name,
                organization_type=OrganizationType.GEMEENTE,
                successor=land_van_cuijk,
                is_active=False,
            )

        assert land_van_cuijk.predecessors.count() == 5
        assert len(land_van_cuijk.get_all_predecessors()) == 5

    def test_get_ancestors(self):
        """get_ancestors() returns all ancestors in order."""
        ministry = OrganizationUnit.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        dg = OrganizationUnit.objects.create(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        directie = OrganizationUnit.objects.create(
            name="Directie DO",
            organization_type=OrganizationType.DIRECTIE,
            parent=dg,
        )
        afdeling = OrganizationUnit.objects.create(
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
        ministry = OrganizationUnit.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        dg = OrganizationUnit.objects.create(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=ministry,
        )
        directie = OrganizationUnit.objects.create(
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
        org = OrganizationUnit.objects.create(
            name="Ministerie van BZK",
            abbreviations=["BZK"],
            organization_type=OrganizationType.MINISTERIE,
        )
        assert str(org) == "Ministerie van BZK (BZK)"

    def test_str_without_abbreviation(self):
        """__str__ shows only name when no abbreviation."""
        org = OrganizationUnit.objects.create(
            name="Directie Digitale Overheid",
            organization_type=OrganizationType.DIRECTIE,
        )
        assert str(org) == "Directie Digitale Overheid"


class OrganizationUnitQuerySetTest(TestCase):
    """Tests for OrganizationUnitQuerySet methods."""

    def setUp(self):
        """Create test organization hierarchy."""
        # Clear any fixture data for isolated tests
        OrganizationUnit.objects.all().delete()

        self.ministry = OrganizationUnit.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)
        self.dg = OrganizationUnit.objects.create(
            name="DGDOO",
            organization_type=OrganizationType.DIRECTORAAT_GENERAAL,
            parent=self.ministry,
        )
        self.directie = OrganizationUnit.objects.create(
            name="Directie DO",
            organization_type=OrganizationType.DIRECTIE,
            parent=self.dg,
        )
        self.inactive_org = OrganizationUnit.objects.create(
            name="Oude Directie",
            organization_type=OrganizationType.DIRECTIE,
            is_active=False,
        )

    def test_default_includes_inactive(self):
        """Default queryset includes inactive organizations (only filters deleted)."""
        all_orgs = OrganizationUnit.objects.all()
        assert all_orgs.count() == 4
        assert self.inactive_org in all_orgs

    def test_active_excludes_inactive(self):
        """active() queryset excludes inactive organizations."""
        active_orgs = OrganizationUnit.objects.active()
        assert active_orgs.count() == 3
        assert self.inactive_org not in active_orgs

    def test_roots_filter(self):
        """roots() filters to organizations without parent."""
        roots = OrganizationUnit.objects.roots()
        assert roots.count() == 2  # ministry + inactive_org (both are roots)
        assert self.ministry in roots

    def test_of_type_filter(self):
        """of_type() filters by organization type."""
        ministries = OrganizationUnit.objects.of_type(OrganizationType.MINISTERIE)
        assert ministries.count() == 1
        assert self.ministry in ministries

    def test_of_type_multiple_types(self):
        """of_type() accepts multiple types."""
        orgs = OrganizationUnit.objects.of_type(OrganizationType.MINISTERIE, OrganizationType.DIRECTIE)
        assert orgs.count() == 3  # ministry + directie + inactive_org

    def test_with_descendants(self):
        """with_descendants() returns all IDs including descendants."""
        all_ids = OrganizationUnit.objects.with_descendants([self.ministry.id])
        assert len(all_ids) == 3
        assert self.ministry.id in all_ids
        assert self.dg.id in all_ids
        assert self.directie.id in all_ids


class AssignmentOrganizationUnitTest(TestCase):
    """Tests for AssignmentOrganizationUnit through model."""

    def setUp(self):
        """Create test data."""
        self.user = User.objects.create_user(username="test", email="test@example.com", password="test")
        self.colleague = Colleague.objects.create(
            name="Test Colleague",
            email="colleague@example.com",
            source="wies",
        )
        self.org = OrganizationUnit.objects.create(name="BZK", organization_type=OrganizationType.MINISTERIE)

    def test_assignment_primary_organization(self):
        """get_primary_organization() returns PRIMARY relation."""
        assignment = Assignment.objects.create(
            name="Test Opdracht",
            owner=self.colleague,
            source="wies",
        )
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment,
            organization=self.org,
            role=OrganizationUnitRole.PRIMARY,
        )
        assert assignment.get_primary_organization() == self.org

    def test_assignment_no_primary_organization(self):
        """get_primary_organization() returns None when no PRIMARY relation."""
        assignment = Assignment.objects.create(
            name="Test Opdracht",
            owner=self.colleague,
            source="wies",
        )
        assert assignment.get_primary_organization() is None

    def test_multiple_organizations_per_assignment(self):
        """Assignment can have multiple organizations with different roles."""
        org2 = OrganizationUnit.objects.create(name="EZK", organization_type=OrganizationType.MINISTERIE)
        assignment = Assignment.objects.create(
            name="Test",
            owner=self.colleague,
            source="wies",
        )
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=self.org, role=OrganizationUnitRole.PRIMARY
        )
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=org2, role=OrganizationUnitRole.INVOLVED
        )
        assert assignment.organization_relations.count() == 2

    def test_assignment_organization_str(self):
        """AssignmentOrganizationUnit __str__ is descriptive."""
        assignment = Assignment.objects.create(
            name="Test Opdracht",
            owner=self.colleague,
            source="wies",
        )
        rel = AssignmentOrganizationUnit.objects.create(
            assignment=assignment,
            organization=self.org,
            role=OrganizationUnitRole.PRIMARY,
        )
        assert "Test Opdracht" in str(rel)
        assert "BZK" in str(rel)
        assert "Primaire organisatie" in str(rel)

    def test_only_one_primary_organization_allowed(self):
        """Only one PRIMARY organization per assignment is allowed."""
        org2 = OrganizationUnit.objects.create(name="EZK", organization_type=OrganizationType.MINISTERIE)
        assignment = Assignment.objects.create(
            name="Test",
            owner=self.colleague,
            source="wies",
        )
        # First PRIMARY is OK
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment, organization=self.org, role=OrganizationUnitRole.PRIMARY
        )
        # Second PRIMARY should fail at database level
        with pytest.raises(IntegrityError):
            AssignmentOrganizationUnit.objects.create(
                assignment=assignment, organization=org2, role=OrganizationUnitRole.PRIMARY
            )


class SoftDeleteTest(TestCase):
    """Tests for soft delete functionality."""

    def test_soft_delete_sets_deleted_at(self):
        """delete() sets deleted_at instead of removing record."""
        org = OrganizationUnit.objects.create(name="Test", organization_type=OrganizationType.GEMEENTE)
        org.delete()

        # Should not be in default queryset
        assert OrganizationUnit.objects.filter(pk=org.pk).count() == 0

        # Should be in objects.with_deleted() queryset
        deleted_org = OrganizationUnit.objects.with_deleted().get(pk=org.pk)
        assert deleted_org.deleted_at is not None

    def test_restore_clears_deleted_at(self):
        """restore() clears deleted_at."""
        org = OrganizationUnit.objects.create(name="Test", organization_type=OrganizationType.GEMEENTE)
        org.delete()
        assert OrganizationUnit.objects.filter(pk=org.pk).count() == 0

        # Restore
        deleted_org = OrganizationUnit.objects.with_deleted().get(pk=org.pk)
        deleted_org.restore()

        # Should be back in default queryset
        assert OrganizationUnit.objects.filter(pk=org.pk).count() == 1
        restored_org = OrganizationUnit.objects.get(pk=org.pk)
        assert restored_org.deleted_at is None

    def test_cannot_delete_org_with_tooi(self):
        """Organizations with TOOI identifier cannot be deleted."""
        org = OrganizationUnit.objects.create(
            name="Test Ministry",
            organization_type=OrganizationType.MINISTERIE,
            tooi_identifier="https://identifier.overheid.nl/tooi/id/test",
        )
        with pytest.raises(models.ProtectedError) as exc_info:
            org.delete()
        assert "TOOI" in str(exc_info.value)

    def test_cannot_delete_org_with_children(self):
        """Organizations with children cannot be deleted."""
        parent = OrganizationUnit.objects.create(name="Parent", organization_type=OrganizationType.MINISTERIE)
        OrganizationUnit.objects.create(
            name="Child", organization_type=OrganizationType.DIRECTORAAT_GENERAAL, parent=parent
        )

        with pytest.raises(models.ProtectedError) as exc_info:
            parent.delete()
        assert "onderliggende" in str(exc_info.value)

    def test_hard_delete_removes_record(self):
        """hard_delete() actually removes from database."""
        org = OrganizationUnit.objects.create(name="Test", organization_type=OrganizationType.GEMEENTE)
        pk = org.pk
        org.hard_delete()

        assert OrganizationUnit.objects.with_deleted().filter(pk=pk).count() == 0

    def test_default_manager_excludes_deleted(self):
        """objects manager excludes soft-deleted records."""
        org1 = OrganizationUnit.objects.create(name="Active", organization_type=OrganizationType.GEMEENTE)
        org2 = OrganizationUnit.objects.create(name="To Delete", organization_type=OrganizationType.GEMEENTE)
        org2.delete()

        # Default manager only sees active
        assert list(OrganizationUnit.objects.all()) == [org1]

        # objects.with_deleted() sees both
        assert OrganizationUnit.objects.with_deleted().count() == 2
