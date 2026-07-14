from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from wies.core.models import Assignment, Colleague, Placement, Service, Suborganization
from wies.core.services.placements import create_assignments_from_csv
from wies.core.services.sync import sync_all_otys_iir_records
from wies.core.services.users import create_users_from_csv

User = get_user_model()


class DataImportIntegrationTest(TestCase):
    """High-level integration tests for CSV imports and OTYS sync with merk assignment"""

    def setUp(self):
        """Create necessary groups for CSV import tests"""
        Group.objects.get_or_create(name="Beheerder")
        Group.objects.get_or_create(name="Consultant")
        Group.objects.get_or_create(name="Business Development Manager")

    def test_csv_user_import_with_brand_creates_merken(self):
        """Test: CSV with brand column assigns each user's merk (auto-created)"""
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
John,Doe,john@rijksoverheid.nl,Rijks ICT Gilde,y,n,n
Jane,Smith,jane@rijksoverheid.nl,Rijksconsultants,n,y,n
Bob,Johnson,bob@rijksoverheid.nl,Rijks ICT Gilde,n,n,y"""

        result = create_users_from_csv(None, csv_content)

        # Verify import success
        assert result["success"]
        assert result["users_created"] == 3
        assert result["suborganizations_created"] == 2  # Two unique brands
        assert "Rijks ICT Gilde" in result["created_suborganizations"]
        assert "Rijksconsultants" in result["created_suborganizations"]

        # Verify merken were created
        rig_suborg = Suborganization.objects.get(name="Rijks ICT Gilde")
        rc_suborg = Suborganization.objects.get(name="Rijksconsultants")

        # Verify users' linked colleagues have correct merk
        john = User.objects.get(email="john@rijksoverheid.nl")
        assert john.colleague.suborganization == rig_suborg

        jane = User.objects.get(email="jane@rijksoverheid.nl")
        assert jane.colleague.suborganization == rc_suborg

        bob = User.objects.get(email="bob@rijksoverheid.nl")
        assert bob.colleague.suborganization == rig_suborg

    def test_csv_user_import_without_brand_creates_users_without_merk(self):
        """Test: CSV without brand column or empty brand creates users with no merk"""
        csv_content = """first_name,last_name,email,brand
Alice,Wonder,alice@rijksoverheid.nl,
Charlie,Brown,charlie@rijksoverheid.nl,"""

        result = create_users_from_csv(None, csv_content)

        assert result["success"]
        assert result["users_created"] == 2
        assert result["suborganizations_created"] == 0

        # Verify colleagues have no merk assigned
        alice = User.objects.get(email="alice@rijksoverheid.nl")
        assert alice.colleague.suborganization is None

        charlie = User.objects.get(email="charlie@rijksoverheid.nl")
        assert charlie.colleague.suborganization is None

    def test_csv_user_import_reuses_existing_merk(self):
        """Test: Importing multiple users with same brand reuses existing merk"""
        # Pre-create the merk
        existing_suborg = Suborganization.objects.create(name="Pre-existing Brand")

        csv_content = """first_name,last_name,email,brand
User,One,user1@rijksoverheid.nl,Pre-existing Brand
User,Two,user2@rijksoverheid.nl,Pre-existing Brand
User,Three,user3@rijksoverheid.nl,Pre-existing Brand"""

        result = create_users_from_csv(None, csv_content)

        assert result["success"]
        assert result["users_created"] == 3
        assert result["suborganizations_created"] == 0  # No new merken created

        # Verify only one merk exists with that name
        assert Suborganization.objects.filter(name="Pre-existing Brand").count() == 1

        # Verify all users' linked colleagues have the same merk
        user1 = User.objects.get(email="user1@rijksoverheid.nl")
        user2 = User.objects.get(email="user2@rijksoverheid.nl")
        user3 = User.objects.get(email="user3@rijksoverheid.nl")

        assert user1.colleague.suborganization == existing_suborg
        assert user2.colleague.suborganization == existing_suborg
        assert user3.colleague.suborganization == existing_suborg

    def test_csv_user_import_duplicate_email_handling(self):
        """Test: Re-importing user with existing email skips and warns"""
        # First import
        csv_content1 = """first_name,last_name,email,brand
Original,Name,duplicate@rijksoverheid.nl,Brand A"""

        result1 = create_users_from_csv(None, csv_content1)
        assert result1["success"]
        assert result1["users_created"] == 1

        # Second import with same email
        csv_content2 = """first_name,last_name,email,brand
Different,Name,duplicate@rijksoverheid.nl,Brand B"""

        result2 = create_users_from_csv(None, csv_content2)
        assert result2["success"]
        assert result2["users_created"] == 0
        assert "duplicate@rijksoverheid.nl" in result2["errors"][0]

        # Verify original user unchanged
        user = User.objects.get(email="duplicate@rijksoverheid.nl")
        assert user.first_name == "Original"
        assert user.last_name == "Name"

    def test_csv_assignment_import_with_brand_assigns_merk(self):
        """Test: CSV placement import with brand columns assigns merk to new colleagues"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,client_1_url,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Test Description,Owner Name,owner@rijksoverheid.nl,,01-01-2025,31-12-2025,Python,John Doe,john@rijksoverheid.nl,Rijks ICT Gilde,Rijks ICT Gilde"""

        result = create_assignments_from_csv(None, csv_content)

        assert result["success"]
        assert result["colleagues_created"] > 0

        # Verify Rijks ICT Gilde merk was created
        rig_suborg = Suborganization.objects.get(name="Rijks ICT Gilde")

        # Verify colleagues have the merk
        john = Colleague.objects.get(email="john@rijksoverheid.nl")
        assert john.suborganization == rig_suborg

        owner = Colleague.objects.get(email="owner@rijksoverheid.nl")
        assert owner.suborganization == rig_suborg

    def test_csv_placement_import_without_brand_no_merk(self):
        """Test: CSV placement import without brand columns or empty brands creates colleagues with no merk"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,client_1_url,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Test Description,Owner Name,owner@test.com,,01-01-2025,31-12-2025,Python,John Doe,john@test.com,,"""

        result = create_assignments_from_csv(None, csv_content)

        assert result["success"]
        assert result["colleagues_created"] > 0

        # Verify colleagues have no merk
        john = Colleague.objects.get(email="john@test.com")
        assert john.suborganization is None

        owner = Colleague.objects.get(email="owner@test.com")
        assert owner.suborganization is None

    def test_csv_placement_import_multiple_brands(self):
        """Test: CSV placement import with different brands for owners vs colleagues"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,client_1_url,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Assignment 1,Test,Owner A,ownera@test.com,,01-01-2025,31-12-2025,Python,John Doe,john@test.com,Rijks ICT Gilde,Rijksconsultants
Assignment 2,Test,Owner B,ownerb@test.com,,01-01-2025,31-12-2025,Java,Jane Smith,jane@test.com,I-Interim Rijk,Rijks ICT Gilde"""

        result = create_assignments_from_csv(None, csv_content)

        assert result["success"]
        assert result["colleagues_created"] == 4  # 2 owners + 2 placement colleagues

        # Verify brand merken were created
        rig_suborg = Suborganization.objects.get(name="Rijks ICT Gilde")
        rc_suborg = Suborganization.objects.get(name="Rijksconsultants")
        iir_suborg = Suborganization.objects.get(name="I-Interim Rijk")

        # Verify first row: owner has RIG, colleague has RC
        john = Colleague.objects.get(email="john@test.com")
        assert john.suborganization == rc_suborg

        owner_a = Colleague.objects.get(email="ownera@test.com")
        assert owner_a.suborganization == rig_suborg

        # Verify second row: owner has IIR, colleague has RIG
        jane = Colleague.objects.get(email="jane@test.com")
        assert jane.suborganization == rig_suborg

        owner_b = Colleague.objects.get(email="ownerb@test.com")
        assert owner_b.suborganization == iir_suborg

    def test_csv_assignment_import_existing_colleague_keeps_merk(self):
        """Test: Re-importing placement for an existing colleague leaves their merk untouched"""
        rig_suborg = Suborganization.objects.create(name="Rijks ICT Gilde")

        colleague = Colleague.objects.create(
            name="Existing Colleague", email="existing@rijksoverheid.nl", source="wies", suborganization=rig_suborg
        )

        # Import placement with existing colleague (brand only applies to new colleagues)
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,client_1_url,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
New Assignment,Description,,,,01-01-2025,31-12-2025,Django,Existing Colleague,existing@rijksoverheid.com"""

        result = create_assignments_from_csv(None, csv_content)

        assert result["success"]

        colleague.refresh_from_db()
        assert colleague.suborganization == rig_suborg

    @patch("wies.core.services.sync.OTYSAPI")
    def test_otys_sync_assigns_i_interim_rijk_merk(self, mock_otys_api):
        """Test: OTYS sync assigns the I-Interim Rijk merk to synced colleagues"""
        # Mock OTYS API responses
        mock_api_instance = Mock()
        mock_otys_api.return_value.__enter__.return_value = mock_api_instance

        mock_api_instance.get_candidate_list.return_value = {
            "listOutput": [
                {
                    "uid": "12345",
                    "Person": {"firstName": "Jane", "lastName": "Doe", "infix": "", "emailPrimary": "jane@otys.com"},
                },
                {
                    "uid": "67890",
                    "Person": {
                        "firstName": "John",
                        "lastName": "Smith",
                        "infix": "van",
                        "emailPrimary": "john@otys.com",
                    },
                },
            ]
        }

        mock_api_instance.get_vacancy_list.return_value = {"listOutput": []}

        # Run sync
        with patch("wies.core.services.sync.settings") as mock_settings:
            mock_settings.OTYS_API_KEY = "test_key"
            mock_settings.OTYS_URL = "https://test.otys.com"
            result = sync_all_otys_iir_records()

        assert result["candidates_synced"] == 2

        # Verify I-Interim Rijk merk was created
        iir_suborg = Suborganization.objects.get(name="I-Interim Rijk")

        # Verify both colleagues have the merk
        jane = Colleague.objects.get(source_id="12345", source="otys_iir")
        assert jane.suborganization == iir_suborg
        assert jane.name == "Jane Doe"

        john = Colleague.objects.get(source_id="67890", source="otys_iir")
        assert john.suborganization == iir_suborg
        assert john.name == "John van Smith"

    @patch("wies.core.services.sync.OTYSAPI")
    def test_otys_sync_idempotency_keeps_single_merk(self, mock_otys_api):
        """Test: Re-syncing OTYS data keeps the I-Interim Rijk merk (no duplicate merken)"""
        iir_suborg = Suborganization.objects.create(name="I-Interim Rijk")

        colleague = Colleague.objects.create(
            name="Existing OTYS User", source_id="99999", source="otys_iir", email="existing@otys.com", suborganization=iir_suborg
        )

        # Mock OTYS API to return the same colleague
        mock_api_instance = Mock()
        mock_otys_api.return_value.__enter__.return_value = mock_api_instance

        mock_api_instance.get_candidate_list.return_value = {
            "listOutput": [
                {
                    "uid": "99999",
                    "Person": {
                        "firstName": "Existing OTYS",
                        "lastName": "User",
                        "infix": "",
                        "emailPrimary": "existing@otys.com",
                    },
                }
            ]
        }

        mock_api_instance.get_vacancy_list.return_value = {"listOutput": []}

        # Run sync again
        with patch("wies.core.services.sync.settings") as mock_settings:
            mock_settings.OTYS_API_KEY = "test_key"
            mock_settings.OTYS_URL = "https://test.otys.com"
            result = sync_all_otys_iir_records()

        assert result["candidates_synced"] == 1

        # Verify colleague still has the same merk and only one merk row exists
        colleague.refresh_from_db()
        assert colleague.suborganization == iir_suborg
        assert Suborganization.objects.filter(name="I-Interim Rijk").count() == 1

    def test_full_import_workflow_csv_to_ui_visibility(self):
        """Test: Complete workflow from CSV import to data visibility"""
        # Import users with a brand → merk
        csv_content = """first_name,last_name,email,brand
Test,User,testuser@rijksoverheid.nl,Test Brand"""

        result = create_users_from_csv(None, csv_content)
        assert result["success"]

        # Verify merk was created
        test_suborg = Suborganization.objects.get(name="Test Brand")

        # Verify user's linked colleague has the merk
        user = User.objects.get(email="testuser@rijksoverheid.nl")
        assert user.colleague.suborganization == test_suborg

        # Verify merk appears in queryset (simulating UI display via colleague)
        users_with_suborg = User.objects.filter(colleague__suborganization=test_suborg)
        assert user in users_with_suborg

    def test_csv_two_rows_same_skill_different_colleagues_create_two_services(self):
        """Test: Two CSV rows with the same skill and different colleagues create two Services."""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
JusticeLink,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Architect,Anuj Gupta,anuj@x.com
JusticeLink,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Architect,Jurre Heesbeen,jurre@x.com"""

        result = create_assignments_from_csv(None, csv_content)

        assert result["success"]
        assert result["assignments_created"] == 1
        assert result["services_created"] == 2
        assert result["placements_created"] == 2

        assignment = Assignment.objects.get(name="JusticeLink")
        services = Service.objects.filter(assignment=assignment, source="wies")
        assert services.count() == 2
        for service in services:
            assert service.placements.count() == 1

    def test_csv_reupload_idempotent(self):
        """Test: Re-uploading the same CSV creates no duplicate Services or Placements."""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
JusticeLink,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Architect,Anuj Gupta,anuj@x.com
JusticeLink,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Architect,Jurre Heesbeen,jurre@x.com"""

        first = create_assignments_from_csv(None, csv_content)
        assert first["success"]
        assert first["services_created"] == 2
        assert first["placements_created"] == 2

        second = create_assignments_from_csv(None, csv_content)
        assert second["success"]
        assert second["services_created"] == 0
        assert second["placements_created"] == 0
        assert second["assignments_created"] == 0

        assignment = Assignment.objects.get(name="JusticeLink")
        assert Service.objects.filter(assignment=assignment, source="wies").count() == 2
        assert Placement.objects.filter(service__assignment=assignment, source="wies").count() == 2

    def test_csv_vacancy_row_dedupes_by_skill(self):
        """Test: A placed row + a vacancy row (empty email) for the same skill create two Services."""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
JusticeLink,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Architect,Anuj Gupta,anuj@x.com
JusticeLink,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Architect,,"""

        result = create_assignments_from_csv(None, csv_content)

        assert result["success"]
        assert result["services_created"] == 2
        assert result["placements_created"] == 1

        assignment = Assignment.objects.get(name="JusticeLink")
        services = Service.objects.filter(assignment=assignment, source="wies")
        assert services.count() == 2

        # The vacancy service has zero placements.
        vacancy_services = [s for s in services if s.placements.count() == 0]
        placed_services = [s for s in services if s.placements.count() == 1]
        assert len(vacancy_services) == 1
        assert len(placed_services) == 1

        # Re-uploading must not create a second vacancy for the same skill.
        result2 = create_assignments_from_csv(None, csv_content)
        assert result2["success"]
        assert result2["services_created"] == 0
        assert result2["placements_created"] == 0
        assert Service.objects.filter(assignment=assignment, source="wies").count() == 2

    def test_csv_sourced_services_have_at_most_one_placement(self):
        """Regression invariant: every CSV-sourced Service has at most one Placement."""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
JusticeLink,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Architect,Anuj Gupta,anuj@x.com
JusticeLink,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Architect,Jurre Heesbeen,jurre@x.com
OtherProject,Desc,Owner,owner@x.com,01-01-2025,31-12-2028,Python,Dev One,dev1@x.com"""

        result = create_assignments_from_csv(None, csv_content)
        assert result["success"]

        for svc in Service.objects.filter(source="wies"):
            assert svc.placements.count() <= 1, f"Service {svc.id} has {svc.placements.count()} placements"
