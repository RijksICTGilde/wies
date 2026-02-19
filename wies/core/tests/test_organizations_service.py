import copy
from pathlib import Path

from django.test import TestCase

from wies.core.models import Event, OrganizationType, OrganizationUnit
from wies.core.services.organizations import parse_xml_hierarchical, sync_organization_tree, sync_organizations


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
        # 5 original + 1 future eindDatum + 2 same name different types + 2 inactive (6001, 8001) = 10 root orgs
        # (AIVD excluded completely)
        assert len(result) == 10

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

    def test_inactive_org_has_is_active_false(self):
        """Test that organizations with eindDatum in the past are returned with is_active=False"""
        result = parse_xml_hierarchical(self.xml_content)

        # "Voormalige Testorganisatie" has eindDatum=2020-12-31
        voormalige = [org for org in result if org["name"] == "Voormalige Testorganisatie"]
        assert len(voormalige) == 1, "Inactive org should be included in results"
        assert voormalige[0]["is_active"] is False

    def test_keeps_organizations_with_einddatum_in_future(self):
        """Test that organizations with eindDatum in the future have is_active=True"""
        result = parse_xml_hierarchical(self.xml_content)

        # "Toekomstige Testorganisatie" has eindDatum=2099-12-31, should be active
        toekomstig = [org for org in result if org["name"] == "Toekomstige Testorganisatie"]
        assert len(toekomstig) == 1
        assert toekomstig[0]["is_active"] is True

    def test_keeps_organizations_without_einddatum(self):
        """Test that organizations without eindDatum have is_active=True"""
        result = parse_xml_hierarchical(self.xml_content)

        # "Asiel en Migratie" has no eindDatum, should be active
        ministry = [org for org in result if org["name"] == "Asiel en Migratie"]
        assert len(ministry) == 1
        assert ministry[0]["is_active"] is True

    def test_filters_excluded_organizations(self):
        """Test that organizations with excluded names (intelligence services) are filtered out"""
        result = parse_xml_hierarchical(self.xml_content)

        names = [org["name"] for org in result]
        assert "Algemene Inlichtingen- en Veiligheidsdienst" not in names

    def test_filters_children_of_excluded_organizations(self):
        """Test that children of excluded organizations are also filtered out"""
        result = parse_xml_hierarchical(self.xml_content)

        def all_names(orgs):
            names = set()
            for org in orgs:
                names.add(org["name"])
                names.update(all_names(org.get("children", [])))
            return names

        all_org_names = all_names(result)
        assert "directie Inlichtingen" not in all_org_names

    def test_inactive_parent_propagates_to_children(self):
        """Test that inactive parent organizations propagate is_active=False to children"""
        result = parse_xml_hierarchical(self.xml_content)

        # "Voormalig Directoraat" has eindDatum in past
        voormalig_dir = [org for org in result if org["name"] == "Voormalig Directoraat"]
        assert len(voormalig_dir) == 1
        assert voormalig_dir[0]["is_active"] is False

        # Child should also be inactive
        children = voormalig_dir[0]["children"]
        assert len(children) == 1
        assert children[0]["name"] == "Afdeling onder voormalig directoraat"
        assert children[0]["is_active"] is False


class SyncOrganizationTreeTest(TestCase):
    """Tests for sync_organization_tree function"""

    @classmethod
    def setUpClass(cls):
        """Load test fixture once for all tests"""
        super().setUpClass()
        fixture_path = Path(__file__).parent.parent / "fixtures" / "organizations_test_fixture.xml"
        with fixture_path.open("rb") as f:
            cls.xml_content = f.read()
        cls.parsed_orgs = parse_xml_hierarchical(cls.xml_content)

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

    def test_unchanged_organization_without_tooi_or_parent(self):
        """Test that root orgs without TOOI can be matched by name on re-sync"""
        # Create an organization without TOOI and without parent
        org_data = {
            "name": "Test Organization Without TOOI",
            "label": "Test Organization Without TOOI",
            "abbreviations": ["TEST"],
            "org_type_names": ["Test"],
            "tooi_identifier": None,  # No TOOI
            "system_id": "999",
            "source_url": "http://test.nl",
            "related_ministry_tooi": "",
            "children": [],
            "is_active": True,
        }

        # First sync - creates the org
        result1 = sync_organization_tree(org_data.copy(), parent=None, dry_run=False)
        assert result1.created == 1
        assert result1.updated == 0
        assert result1.unchanged == 0

        # Verify org was created
        assert OrganizationUnit.objects.filter(name="Test Organization Without TOOI").count() == 1

        # Second sync with identical data - should match by name and be unchanged
        result2 = sync_organization_tree(org_data.copy(), parent=None, dry_run=False)

        # Should match the existing org, not create a duplicate
        assert result2.created == 0, f"Expected created=0 but got created={result2.created}"
        assert result2.updated == 0, f"Expected updated=0 but got updated={result2.updated}"
        assert result2.unchanged == 1, f"Expected unchanged=1 but got unchanged={result2.unchanged}"

        # Verify still only one org exists
        assert OrganizationUnit.objects.filter(name="Test Organization Without TOOI").count() == 1

    def test_unchanged_organization_with_types(self):
        """Test that ManyToMany comparison doesn't trigger false updates

        This tests for a subtle bug: when comparing ManyToMany relationships,
        we need to compare by PK sets, not by object lists, because:
        1. List order might differ between queryset results
        2. Object identity comparison might not work reliably
        """
        # Get ministry data with organization types
        ministry_data = next(org for org in self.parsed_orgs if org["name"] == "Asiel en Migratie").copy()
        # Remove children to test just the top level
        ministry_data.pop("children", [])

        # First sync - creates org with organization_types
        result1 = sync_organization_tree(ministry_data.copy(), parent=None, dry_run=False)
        assert result1.created == 1
        assert result1.updated == 0
        assert result1.unchanged == 0

        # Verify org has organization types
        org = OrganizationUnit.objects.get(name="Asiel en Migratie")
        assert org.organization_types.count() == 1

        # Second sync with identical data - should be unchanged
        result2 = sync_organization_tree(ministry_data.copy(), parent=None, dry_run=False)

        # This should detect no changes since the organization_types are identical
        assert result2.created == 0
        assert result2.updated == 0, f"Expected updated=0 but got updated={result2.updated}"
        assert result2.unchanged == 1, f"Expected unchanged=1 but got unchanged={result2.unchanged}"

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
            "is_active": True,
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

    def test_creates_separate_orgs_when_same_name_different_types(self):
        """Test that organizations with same name but different types create separate records"""
        # Get the two test orgs with same name "Testorganisatie Meerdere Types" but different types
        orgs_with_same_name = [org for org in self.parsed_orgs if org["name"] == "Testorganisatie Meerdere Types"]
        assert len(orgs_with_same_name) == 2, "Fixture should have 2 orgs with same name"

        # Sync first org (type: Agentschap)
        org1 = orgs_with_same_name[0].copy()
        org1.pop("children", [])
        result1 = sync_organization_tree(org1, parent=None, dry_run=False)

        assert result1.created == 1
        assert OrganizationUnit.objects.count() == 1

        # Sync second org with same name but different type (type: Adviescollege)
        org2 = orgs_with_same_name[1].copy()
        org2.pop("children", [])
        result2 = sync_organization_tree(org2, parent=None, dry_run=False)

        # Should create a new org, not update the existing one
        assert result2.created == 1
        assert result2.updated == 0
        assert OrganizationUnit.objects.count() == 2

        # Verify both orgs exist with different types
        orgs = OrganizationUnit.objects.filter(name="Testorganisatie Meerdere Types")
        assert orgs.count() == 2

        org_types = {tuple(sorted(org.organization_types.values_list("name", flat=True))) for org in orgs}
        assert ("Agentschap",) in org_types
        assert ("Adviescollege",) in org_types

    def test_matches_org_with_same_name_and_types(self):
        """Test that organizations with same name and same types match correctly"""
        # Get one of the test orgs
        org_data = next(org for org in self.parsed_orgs if org["name"] == "Testorganisatie Meerdere Types").copy()
        org_data.pop("children", [])

        # Sync first time - creates org
        result1 = sync_organization_tree(org_data, parent=None, dry_run=False)
        assert result1.created == 1
        assert OrganizationUnit.objects.count() == 1

        # Sync second time with same data - should match and be unchanged
        result2 = sync_organization_tree(org_data, parent=None, dry_run=False)
        assert result2.created == 0
        assert result2.updated == 0
        assert result2.unchanged == 1
        assert OrganizationUnit.objects.count() == 1  # Still only 1 org

    def test_prevents_duplicate_on_repeated_sync_with_type_conflicts(self):
        """Test that A→B→A sync pattern doesn't create 3rd duplicate (regression test for .first() bug)"""
        # Get the two test orgs with same name "Testorganisatie Meerdere Types" but different types
        orgs_with_same_name = [org for org in self.parsed_orgs if org["name"] == "Testorganisatie Meerdere Types"]
        assert len(orgs_with_same_name) == 2

        org_agentschap = orgs_with_same_name[0].copy()  # Type: Agentschap
        org_adviescollege = orgs_with_same_name[1].copy()  # Type: Adviescollege
        org_agentschap.pop("children", [])
        org_adviescollege.pop("children", [])

        # Sync A: creates first org with type Agentschap
        result1 = sync_organization_tree(org_agentschap, parent=None, dry_run=False)
        assert result1.created == 1
        assert OrganizationUnit.objects.count() == 1

        # Sync B: creates second org with type Adviescollege (different type)
        result2 = sync_organization_tree(org_adviescollege, parent=None, dry_run=False)
        assert result2.created == 1
        assert OrganizationUnit.objects.count() == 2

        # Sync A AGAIN: should match first org, NOT create third duplicate
        # This is the critical regression test - old .first() logic would create a 3rd org here
        result3 = sync_organization_tree(org_agentschap, parent=None, dry_run=False)
        assert result3.created == 0, "Should not create duplicate when matching type already exists"
        assert result3.unchanged == 1
        assert OrganizationUnit.objects.count() == 2, "Should still have only 2 orgs, not 3"

        # Verify both orgs still exist with correct types
        agentschap_org = OrganizationUnit.objects.get(
            name="Testorganisatie Meerdere Types", organization_types__name="Agentschap"
        )
        adviescollege_org = OrganizationUnit.objects.get(
            name="Testorganisatie Meerdere Types", organization_types__name="Adviescollege"
        )
        assert agentschap_org.id != adviescollege_org.id

    def test_does_not_merge_orgs_with_different_tooi(self):
        """Test that two orgs with same name but different TOOIs are not merged"""
        # Create existing org with one TOOI
        existing = OrganizationUnit.objects.create(
            name="Adviescollege toetsing regeldruk",
            tooi_identifier="https://identifier.overheid.nl/tooi/id/oorg/oorg12362",
            source_url="https://organisaties.overheid.nl/29819769/Adviescollege_toetsing_regeldruk/",
        )

        # Sync an org with same name but different TOOI
        org_data = {
            "name": "Adviescollege toetsing regeldruk",
            "system_id": "28200254",
            "label": "Adviescollege toetsing regeldruk",
            "org_type_names": ["Adviescollege"],
            "tooi_identifier": "https://identifier.overheid.nl/tooi/id/oorg/oorg10225",
            "abbreviations": [],
            "source_url": "https://organisaties.overheid.nl/28200254/Adviescollege_toetsing_regeldruk/",
            "children": [],
            "related_ministry_tooi": "",
            "is_active": True,
        }

        result = sync_organization_tree(copy.deepcopy(org_data), parent=None, dry_run=False, seen_ids=set())

        assert result.created == 1, "Should create a new org, not update the existing one"
        assert OrganizationUnit.objects.count() == 2

        # Existing org should be unchanged
        existing.refresh_from_db()
        assert existing.tooi_identifier == "https://identifier.overheid.nl/tooi/id/oorg/oorg12362"

    # is_active handling

    def test_updates_existing_org_to_inactive(self):
        """Test that existing org with eindDatum in past gets is_active=False"""
        org = OrganizationUnit.objects.create(
            name="Voormalige Testorganisatie",
            tooi_identifier="https://identifier.overheid.nl/tooi/id/oorg/oorg6001",
            is_active=True,
        )

        parsed = parse_xml_hierarchical(self.xml_content)
        voormalige = next(o for o in parsed if o["name"] == "Voormalige Testorganisatie")
        sync_organization_tree(copy.deepcopy(voormalige), parent=None, dry_run=False, seen_ids=set())

        org.refresh_from_db()
        assert org.is_active is False

    def test_does_not_create_new_inactive_org(self):
        """Test that new org with is_active=False is NOT created"""
        parsed = parse_xml_hierarchical(self.xml_content)
        voormalige = next(o for o in parsed if o["name"] == "Voormalige Testorganisatie")

        result = sync_organization_tree(copy.deepcopy(voormalige), parent=None, dry_run=False, seen_ids=set())

        assert result.created == 0
        assert OrganizationUnit.objects.filter(name="Voormalige Testorganisatie").count() == 0

    def test_seen_ids_populated(self):
        """Test that seen_ids set is populated during sync"""
        ministry = next(o for o in self.parsed_orgs if o["name"] == "Asiel en Migratie")
        seen_ids: set[int] = set()

        sync_organization_tree(copy.deepcopy(ministry), parent=None, dry_run=False, seen_ids=seen_ids)

        # ministry + DG + directie + afdeling = 4
        assert len(seen_ids) == 4

    def test_seen_ids_not_populated_for_skipped_inactive(self):
        """Test that skipped inactive orgs don't add to seen_ids"""
        parsed = parse_xml_hierarchical(self.xml_content)
        voormalige = next(o for o in parsed if o["name"] == "Voormalige Testorganisatie")
        seen_ids: set[int] = set()

        sync_organization_tree(copy.deepcopy(voormalige), parent=None, dry_run=False, seen_ids=seen_ids)

        assert len(seen_ids) == 0


class SyncOrganizationsDeactivationTest(TestCase):
    """Tests for deactivation of unseen external orgs after sync."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixture_path = Path(__file__).parent.parent / "fixtures" / "organizations_test_fixture.xml"
        with fixture_path.open("rb") as f:
            cls.xml_content = f.read()

    def setUp(self):
        OrganizationUnit.objects.all().delete()
        OrganizationType.objects.all().delete()

    def test_deactivates_unseen_external_orgs(self):
        """Test that external orgs not in XML are deactivated after sync"""
        ghost = OrganizationUnit.objects.create(
            name="Ghost Org",
            source_url="https://organisaties.overheid.nl/99999/Ghost_Org/",
            is_active=True,
        )

        result = sync_organizations(xml_content=self.xml_content, dry_run=False)

        ghost.refresh_from_db()
        assert ghost.is_active is False
        assert result.deactivated >= 1

    def test_does_not_deactivate_manual_orgs(self):
        """Test that manually added orgs (no source_url) are NOT deactivated"""
        manual = OrganizationUnit.objects.create(
            name="Manual Org",
            source_url="",
            is_active=True,
        )

        sync_organizations(xml_content=self.xml_content, dry_run=False)

        manual.refresh_from_db()
        assert manual.is_active is True

    def test_does_not_deactivate_on_dry_run(self):
        """Test that dry run doesn't deactivate orgs"""
        ghost = OrganizationUnit.objects.create(
            name="Ghost Org",
            source_url="https://organisaties.overheid.nl/99999/Ghost_Org/",
            is_active=True,
        )

        sync_organizations(xml_content=self.xml_content, dry_run=True)

        ghost.refresh_from_db()
        assert ghost.is_active is True


class SyncEventLoggingTest(TestCase):
    """Tests for event logging during organization sync."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixture_path = Path(__file__).parent.parent / "fixtures" / "organizations_test_fixture.xml"
        with fixture_path.open("rb") as f:
            cls.xml_content = f.read()

    def setUp(self):
        OrganizationUnit.objects.all().delete()
        OrganizationType.objects.all().delete()
        Event.objects.all().delete()

    def test_create_event_logged(self):
        """Test that creating a new org logs an OrgSync.create event"""
        parsed = parse_xml_hierarchical(self.xml_content)
        ministry = next(o for o in parsed if o["name"] == "Asiel en Migratie")

        sync_organization_tree(copy.deepcopy(ministry), parent=None, dry_run=False, seen_ids=set())

        create_events = Event.objects.filter(name="OrgSync.create")
        assert create_events.count() >= 1
        event = create_events.first()
        assert event.user_email == ""
        assert "org_id" in event.context
        assert "name" in event.context

    def test_update_event_logged(self):
        """Test that updating an existing org logs an OrgSync.update event with changes"""
        org = OrganizationUnit.objects.create(
            name="Old Name",
            tooi_identifier="https://identifier.overheid.nl/tooi/id/ministerie/mnre1001",
            is_active=True,
        )

        parsed = parse_xml_hierarchical(self.xml_content)
        ministry = next(o for o in parsed if o["name"] == "Asiel en Migratie")

        sync_organization_tree(copy.deepcopy(ministry), parent=None, dry_run=False, seen_ids=set())

        update_events = Event.objects.filter(name="OrgSync.update")
        assert update_events.count() == 1
        event = update_events.first()
        assert event.context["org_id"] == org.id
        assert "name" in event.context["changes"]
        assert event.context["changes"]["name"]["old"] == "Old Name"
        assert event.context["changes"]["name"]["new"] == "Asiel en Migratie"

    def test_deactivate_event_logged(self):
        """Test that deactivating unseen orgs logs OrgSync.deactivate events"""
        ghost = OrganizationUnit.objects.create(
            name="Ghost Org",
            source_url="https://organisaties.overheid.nl/99999/Ghost_Org/",
            is_active=True,
        )

        sync_organizations(xml_content=self.xml_content, dry_run=False)

        deactivate_events = Event.objects.filter(name="OrgSync.deactivate")
        assert deactivate_events.count() >= 1
        ghost_event = deactivate_events.filter(context__org_id=ghost.id).first()
        assert ghost_event is not None
        assert ghost_event.context["name"] == "Ghost Org"
        assert ghost_event.context["reason"] == "not_seen_in_sync"

    def test_no_events_on_dry_run(self):
        """Test that dry run does not create any sync events"""
        OrganizationUnit.objects.create(
            name="Ghost Org",
            source_url="https://organisaties.overheid.nl/99999/Ghost_Org/",
            is_active=True,
        )

        sync_organizations(xml_content=self.xml_content, dry_run=True)

        sync_events = Event.objects.filter(name__startswith="OrgSync.")
        assert sync_events.count() == 0

    def test_no_event_when_unchanged(self):
        """Test that no update event is logged when org data hasn't changed"""
        parsed = parse_xml_hierarchical(self.xml_content)
        ministry = next(o for o in parsed if o["name"] == "Asiel en Migratie")

        # First sync creates the org
        sync_organization_tree(copy.deepcopy(ministry), parent=None, dry_run=False, seen_ids=set())
        Event.objects.all().delete()

        # Second sync with same data should not log update
        sync_organization_tree(copy.deepcopy(ministry), parent=None, dry_run=False, seen_ids=set())

        update_events = Event.objects.filter(name="OrgSync.update")
        assert update_events.count() == 0
