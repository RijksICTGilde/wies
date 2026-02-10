import copy
from pathlib import Path

from django.test import TestCase

from wies.core.models import OrganizationType, OrganizationUnit
from wies.core.services.organizations import parse_xml_hierarchical, sync_organization_tree


class ParseXmlHierarchicalTest(TestCase):
    """Tests for parse_xml_hierarchical function"""

    @classmethod
    def setUpClass(cls):
        """Load test fixture once for all tests"""
        super().setUpClass()
        fixture_path = Path(__file__).parent.parent / "fixtures" / "organizations_test_fixture.xml"
        with fixture_path.open("rb") as f:
            cls.xml_content = f.read()

    def test_parse_returns_list(self):
        """Test that parsing returns a list"""
        result = parse_xml_hierarchical(self.xml_content)
        assert isinstance(result, list)
        assert len(result) == 5  # 5 root organizations in fixture

    def test_ministry_label_generation(self):
        """Test that ministry without 'Ministerie' prefix gets it added"""
        result = parse_xml_hierarchical(self.xml_content)

        # Find "Asiel en Migratie" ministry
        ministry = next(org for org in result if org["name"] == "Asiel en Migratie")

        assert ministry["label"] == "Ministerie van Asiel en Migratie"
        assert "Ministerie" in ministry["org_type_names"]

    def test_ministry_label_not_duplicated(self):
        """Test that ministry already starting with 'Ministerie' doesn't get prefix duplicated"""
        result = parse_xml_hierarchical(self.xml_content)

        # Find "Ministerie van Buitenlandse Zaken"
        ministry = next(org for org in result if org["name"] == "Ministerie van Buitenlandse Zaken")

        assert ministry["label"] == "Ministerie van Buitenlandse Zaken"
        assert not ministry["label"].startswith("Ministerie van Ministerie")

    def test_non_ministry_keeps_original_label(self):
        """Test that non-ministry organizations keep their original name as label"""
        result = parse_xml_hierarchical(self.xml_content)

        # Find agentschap
        agentschap = next(org for org in result if org["name"] == "Rijksdienst voor Identiteitsgegevens")

        assert agentschap["label"] == "Rijksdienst voor Identiteitsgegevens"
        assert agentschap["org_type_names"] == ["Agentschap"]

    def test_hierarchical_parsing(self):
        """Test that nested organizational units are parsed correctly"""
        result = parse_xml_hierarchical(self.xml_content)

        # Find ministry with hierarchy
        ministry = next(org for org in result if org["name"] == "Asiel en Migratie")

        # Check DG level
        assert len(ministry["children"]) == 1
        dg = ministry["children"][0]
        assert dg["name"] == "Directoraat-Generaal Migratie"
        assert dg["abbreviations"] == ["DGM"]

        # Check Directie level
        assert len(dg["children"]) == 1
        directie = dg["children"][0]
        assert directie["name"] == "Directie Asielzaken"

        # Check Afdeling level
        assert len(directie["children"]) == 1
        afdeling = directie["children"][0]
        assert afdeling["name"] == "Afdeling Beleid"
        assert len(afdeling["children"]) == 0  # Leaf node

    def test_related_ministry_tooi(self):
        """Test that related ministry TOOI is extracted correctly"""
        result = parse_xml_hierarchical(self.xml_content)

        # Find agentschap
        agentschap = next(org for org in result if org["name"] == "Rijksdienst voor Identiteitsgegevens")

        assert agentschap["related_ministry_tooi"] == "https://identifier.overheid.nl/tooi/id/ministerie/mnre1034"

    def test_nested_org_related_ministry_tooi(self):
        """Test that nested organizations have related ministry TOOI"""
        result = parse_xml_hierarchical(self.xml_content)

        ministry = next(org for org in result if org["name"] == "Asiel en Migratie")
        dg = ministry["children"][0]

        assert dg["related_ministry_tooi"] == "https://identifier.overheid.nl/tooi/id/ministerie/mnre1001"

    def test_abbreviations_parsing(self):
        """Test that multiple abbreviations are parsed correctly"""
        result = parse_xml_hierarchical(self.xml_content)

        ministry = next(org for org in result if org["name"] == "Asiel en Migratie")

        assert set(ministry["abbreviations"]) == {"AM", "AenM"}

    def test_missing_tooi_identifier(self):
        """Test that organizations without TOOI identifier don't crash"""
        result = parse_xml_hierarchical(self.xml_content)

        # Find adviescollege without TOOI
        adviescollege = next(org for org in result if org["name"] == "Testadviesraad")

        assert adviescollege["tooi_identifier"] is None
        assert adviescollege["system_id"] == "3001"

    def test_missing_abbreviations(self):
        """Test that organizations without abbreviations have empty list"""
        result = parse_xml_hierarchical(self.xml_content)

        org = next(org for org in result if org["name"] == "Testorganisatie Zonder Extras")

        assert org["abbreviations"] == []

    def test_missing_related_ministry(self):
        """Test that organizations without ministry relation have None"""
        result = parse_xml_hierarchical(self.xml_content)

        org = next(org for org in result if org["name"] == "Testorganisatie Zonder Extras")

        assert org["related_ministry_tooi"] == ""

    def test_filter_types_ministerie(self):
        """Test that filter_types parameter filters correctly"""
        result = parse_xml_hierarchical(self.xml_content, filter_types=["Ministerie"])

        # Should only return ministries
        assert len(result) == 2
        assert all("Ministerie" in org["org_type_names"] for org in result)

        names = {org["name"] for org in result}
        assert names == {"Asiel en Migratie", "Ministerie van Buitenlandse Zaken"}

    def test_organization_types_extraction(self):
        """Test that organization types are correctly extracted"""
        result = parse_xml_hierarchical(self.xml_content)

        # Check different types
        ministry = next(org for org in result if org["name"] == "Asiel en Migratie")
        assert ministry["org_type_names"] == ["Ministerie"]

        agentschap = next(org for org in result if org["name"] == "Rijksdienst voor Identiteitsgegevens")
        assert agentschap["org_type_names"] == ["Agentschap"]

        adviescollege = next(org for org in result if org["name"] == "Testadviesraad")
        assert adviescollege["org_type_names"] == ["Adviescollege"]

    def test_system_id_extraction(self):
        """Test that system IDs are correctly extracted"""
        result = parse_xml_hierarchical(self.xml_content)

        ministry = next(org for org in result if org["name"] == "Asiel en Migratie")
        assert ministry["system_id"] == "1001"


class SyncOrganizationTreeTest(TestCase):
    """Tests for sync_organization_tree function"""

    @classmethod
    def setUpClass(cls):
        """Load test fixture once for all tests"""
        super().setUpClass()
        fixture_path = Path(__file__).parent.parent / "fixtures" / "organizations_test_fixture.xml"
        with fixture_path.open("rb") as f:
            xml_content = f.read()
        cls.parsed_orgs = parse_xml_hierarchical(xml_content)

    def setUp(self):
        """Clear database before each test"""
        OrganizationUnit.objects.all().delete()
        OrganizationType.objects.all().delete()

    # Core Sync Operations

    def test_creates_new_organization(self):
        """Test that new organization is created with all fields"""
        # Get first ministry from fixture - copy to avoid mutation
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie").copy()
        # Remove children to test just the top level org
        ministry_data.pop("children", [])

        result = sync_organization_tree(ministry_data, parent=None, dry_run=False)

        assert result.created == 1
        assert result.updated == 0
        assert result.unchanged == 0

        # Verify DB record
        org = OrganizationUnit.objects.get(tooi_identifier=ministry_data["tooi_identifier"])
        assert org.name == "Asiel en Migratie"
        assert org.label == "Ministerie van Asiel en Migratie"
        assert set(org.abbreviations) == {"AM", "AenM"}
        assert org.tooi_identifier == "https://identifier.overheid.nl/tooi/id/ministerie/mnre1001"
        assert org.system_id == "1001"
        assert org.parent is None
        assert list(org.organization_types.values_list("name", flat=True)) == ["Ministerie"]

    def test_updates_existing_organization(self):
        """Test that existing organization is updated when attributes change"""
        # Create initial organization
        org = OrganizationUnit.objects.create(
            name="Test Org",
            label="Old Label",
            tooi_identifier="https://identifier.overheid.nl/tooi/id/ministerie/mnre1001",
            abbreviations=["OLD"],
        )

        # Sync with updated data
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie").copy()
        # Remove children to test just the top level
        ministry_data.pop("children", [])
        result = sync_organization_tree(ministry_data, parent=None, dry_run=False)

        assert result.created == 0
        assert result.updated == 1
        assert result.unchanged == 0

        # Verify changes
        org.refresh_from_db()
        assert org.name == "Asiel en Migratie"
        assert org.label == "Ministerie van Asiel en Migratie"
        assert set(org.abbreviations) == {"AM", "AenM"}

    def test_unchanged_organization(self):
        """Test that identical data doesn't trigger update"""
        # Get ministry data
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie").copy()
        # Remove children to test just the top level
        ministry_data.pop("children", [])

        # First sync
        sync_organization_tree(ministry_data.copy(), parent=None, dry_run=False)

        # Second sync with same data
        result = sync_organization_tree(ministry_data.copy(), parent=None, dry_run=False)

        assert result.created == 0
        assert result.updated == 0
        assert result.unchanged == 1

    # TOOI Matching Logic

    def test_match_by_tooi_identifier(self):
        """Test that primary lookup matches by TOOI identifier"""
        # Create org with TOOI
        existing = OrganizationUnit.objects.create(
            name="Different Name",  # Different name shouldn't matter
            tooi_identifier="https://identifier.overheid.nl/tooi/id/ministerie/mnre1001",
        )

        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie").copy()
        # Remove children to test just the top level
        ministry_data.pop("children", [])
        result = sync_organization_tree(ministry_data, parent=None, dry_run=False)

        # Should update existing, not create new
        assert result.created == 0
        assert result.updated == 1
        assert OrganizationUnit.objects.count() == 1

        # Name should be updated
        existing.refresh_from_db()
        assert existing.name == "Asiel en Migratie"

    def test_match_by_name_and_parent_without_tooi(self):
        """Test fallback matching: nested orgs without TOOI matched by name + parent"""
        # Create parent ministry WITHOUT children first
        parent = OrganizationUnit.objects.create(
            name="Asiel en Migratie",
            tooi_identifier="https://identifier.overheid.nl/tooi/id/ministerie/mnre1001",
        )

        # Create nested org without TOOI and without abbreviations
        existing_dg = OrganizationUnit.objects.create(
            name="Directoraat-Generaal Migratie",
            parent=parent,
            tooi_identifier=None,
            abbreviations=[],
        )

        # Now sync the full tree - should match existing DG by name+parent and update it
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie")
        sync_organization_tree(copy.deepcopy(ministry_data), parent=None, dry_run=False)

        # Should not create duplicate DG
        dg_count = OrganizationUnit.objects.filter(name="Directoraat-Generaal Migratie").count()
        assert dg_count == 1

        # Should have updated the existing DG
        existing_dg.refresh_from_db()
        assert existing_dg.abbreviations == ["DGM"]

    def test_adds_tooi_to_existing_org_matched_by_name_and_parent(self):
        """Test that TOOI is added when matching by name+parent to org without TOOI"""
        # Create parent
        parent = OrganizationUnit.objects.create(
            name="Asiel en Migratie",
            tooi_identifier="https://identifier.overheid.nl/tooi/id/ministerie/mnre1001",
        )

        # Create child WITHOUT TOOI
        existing = OrganizationUnit.objects.create(
            name="Directoraat-Generaal Migratie",
            parent=parent,
            tooi_identifier="",  # No TOOI yet
            abbreviations=[],
        )

        # Sync with data that HAS TOOI
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie")
        sync_organization_tree(copy.deepcopy(ministry_data), parent=None, dry_run=False)

        # Should update existing org and add TOOI (not create duplicate)
        dg_count = OrganizationUnit.objects.filter(name="Directoraat-Generaal Migratie").count()
        assert dg_count == 1

        # Should have added TOOI and updated abbreviations
        existing.refresh_from_db()
        assert existing.tooi_identifier == "https://identifier.overheid.nl/tooi/id/oorg/oorg1002"
        assert existing.abbreviations == ["DGM"]

    def test_rejects_match_when_db_has_tooi_but_incoming_doesnt(self):
        """Test TOOI conflict: DB org has TOOI, incoming org doesn't, match is rejected"""
        # Create parent
        parent = OrganizationUnit.objects.create(
            name="Test Parent",
            tooi_identifier="https://identifier.overheid.nl/tooi/id/ministerie/mnre9999",
        )

        # Create child WITH TOOI
        existing_with_tooi = OrganizationUnit.objects.create(
            name="Test Child",
            parent=parent,
            tooi_identifier="https://identifier.overheid.nl/tooi/id/different/tooi123",
            abbreviations=["OLD"],
        )

        # Try to sync same-named org without TOOI
        org_data = {
            "name": "Test Child",
            "label": "Test Child",
            "abbreviations": ["NEW"],
            "org_type_names": ["Test"],
            "tooi_identifier": None,  # No TOOI in incoming data
            "system_id": "999",
            "source_url": "http://test.nl",
            "related_ministry_tooi": "",
            "children": [],
        }

        sync_organization_tree(org_data, parent=parent, dry_run=False)

        # Should create NEW child instead of updating existing (due to TOOI conflict)
        child_count = OrganizationUnit.objects.filter(name="Test Child", parent=parent).count()
        assert child_count == 2  # One with TOOI, one without

        # Original should be unchanged
        existing_with_tooi.refresh_from_db()
        assert existing_with_tooi.tooi_identifier == "https://identifier.overheid.nl/tooi/id/different/tooi123"
        assert existing_with_tooi.abbreviations == ["OLD"]

        # New one should have no TOOI but have new abbreviations
        new_without_tooi = OrganizationUnit.objects.get(name="Test Child", tooi_identifier=None, parent=parent)
        assert new_without_tooi.abbreviations == ["NEW"]

    # Organization Types

    def test_creates_organization_types(self):
        """Test that new organization types are created"""
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie").copy()
        ministry_data.pop("children", [])
        sync_organization_tree(ministry_data, parent=None, dry_run=False)

        # Check type was created
        org_type = OrganizationType.objects.get(name="Ministerie")
        assert org_type.label == "Ministerie"

        # Check relationship
        org = OrganizationUnit.objects.get(name="Asiel en Migratie")
        assert org.organization_types.count() == 1
        assert org.organization_types.first() == org_type

    def test_reuses_existing_organization_types(self):
        """Test that existing organization types are reused, not duplicated"""
        # Pre-create type
        existing_type = OrganizationType.objects.create(name="Ministerie", label="Ministerie")

        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie").copy()
        ministry_data.pop("children", [])
        sync_organization_tree(ministry_data, parent=None, dry_run=False)

        # Should still only have 1 type
        assert OrganizationType.objects.count() == 1
        assert OrganizationType.objects.first() == existing_type

    # Hierarchical Processing

    def test_syncs_nested_organizations(self):
        """Test that parent-child relationships are created correctly"""
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie")
        sync_organization_tree(copy.deepcopy(ministry_data), parent=None, dry_run=False)

        # Check hierarchy
        ministry = OrganizationUnit.objects.get(name="Asiel en Migratie")
        assert ministry.parent is None

        dg = OrganizationUnit.objects.get(name="Directoraat-Generaal Migratie")
        assert dg.parent == ministry

        directie = OrganizationUnit.objects.get(name="Directie Asielzaken")
        assert directie.parent == dg

        afdeling = OrganizationUnit.objects.get(name="Afdeling Beleid")
        assert afdeling.parent == directie

    def test_recursive_sync_accumulates_results(self):
        """Test that result counts accumulate correctly across tree"""
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie")
        result = sync_organization_tree(copy.deepcopy(ministry_data), parent=None, dry_run=False)

        # Should create ministry + DG + Directie + Afdeling = 4
        assert result.created == 4
        assert result.updated == 0
        assert result.unchanged == 0

    # Dry Run Mode

    def test_dry_run_does_not_save(self):
        """Test that dry_run mode doesn't persist changes"""
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie")
        result = sync_organization_tree(copy.deepcopy(ministry_data), parent=None, dry_run=True)

        # Results should report what WOULD happen
        assert result.created == 4

        # But nothing saved to DB
        assert OrganizationUnit.objects.count() == 0
        assert OrganizationType.objects.count() == 0

    # Edge Cases

    def test_handles_missing_optional_fields(self):
        """Test that organizations with missing optional fields don't crash"""
        org_data = next(org for org in self.parsed_orgs if org["name"] == "Testorganisatie Zonder Extras").copy()
        result = sync_organization_tree(org_data, parent=None, dry_run=False)

        assert result.created == 1

        org = OrganizationUnit.objects.get(name="Testorganisatie Zonder Extras")
        assert org.abbreviations == []
        assert org.related_ministry_tooi == ""
        # This org DOES have a TOOI in the fixture
        assert org.tooi_identifier == "https://identifier.overheid.nl/tooi/id/oorg/oorg4001"

    def test_handles_tooi_modification(self):
        """Test that changing TOOI on existing org creates new record"""
        # Create org with old TOOI
        org = OrganizationUnit.objects.create(
            name="Test Ministry",
            tooi_identifier="https://identifier.overheid.nl/tooi/id/ministerie/mnre9999",
        )

        # Get ministry data with different TOOI
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie").copy()
        ministry_data.pop("children", [])

        # Since TOOI is different, it will create a new org rather than update
        result = sync_organization_tree(ministry_data, parent=None, dry_run=False)

        assert result.created == 1
        assert OrganizationUnit.objects.count() == 2

        # Original org unchanged
        org.refresh_from_db()
        assert org.tooi_identifier == "https://identifier.overheid.nl/tooi/id/ministerie/mnre9999"

        # New org created with correct TOOI
        new_org = OrganizationUnit.objects.get(name="Asiel en Migratie")
        assert new_org.tooi_identifier == "https://identifier.overheid.nl/tooi/id/ministerie/mnre1001"
