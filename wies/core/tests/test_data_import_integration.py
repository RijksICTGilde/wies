from unittest.mock import Mock, patch

from django.contrib.auth.models import Group
from django.test import TestCase

from wies.core.models import Colleague, Label, LabelCategory, User
from wies.core.services.placements import create_assignments_from_csv
from wies.core.services.sync import sync_all_otys_iir_records
from wies.core.services.users import create_users_from_csv


class DataImportIntegrationTest(TestCase):
    """High-level integration tests for CSV imports and OTYS sync with label assignment"""

    def setUp(self):
        """Create necessary groups for CSV import tests"""
        Group.objects.get_or_create(name="Beheerder")
        Group.objects.get_or_create(name="Consultant")
        Group.objects.get_or_create(name="Business Development Manager")

    def test_csv_user_import_with_brand_creates_labels(self):
        """Test: CSV with brand column creates users with labels in Merk category"""
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
John,Doe,john@rijksoverheid.nl,Rijks ICT Gilde,y,n,n
Jane,Smith,jane@rijksoverheid.nl,Rijksconsultants,n,y,n
Bob,Johnson,bob@rijksoverheid.nl,Rijks ICT Gilde,n,n,y"""

        result = create_users_from_csv(None, csv_content)

        # Verify import success
        assert result["success"]
        assert result["users_created"] == 3
        assert result["labels_created"] == 2  # Two unique brands
        assert "Rijks ICT Gilde" in result["created_labels"]
        assert "Rijksconsultants" in result["created_labels"]

        # Verify Merk category was created
        merken_category = LabelCategory.objects.get(name="Merk")

        # Verify labels were created in Merk category
        rig_label = Label.objects.get(name="Rijks ICT Gilde", category=merken_category)
        rc_label = Label.objects.get(name="Rijksconsultants", category=merken_category)

        # Verify users have correct labels
        john = User.objects.get(email="john@rijksoverheid.nl")
        assert rig_label in john.labels.all()

        jane = User.objects.get(email="jane@rijksoverheid.nl")
        assert rc_label in jane.labels.all()

        bob = User.objects.get(email="bob@rijksoverheid.nl")
        assert rig_label in bob.labels.all()

    def test_csv_user_import_without_brand_creates_users_without_labels(self):
        """Test: CSV without brand column or empty brand creates users with no labels"""
        csv_content = """first_name,last_name,email,brand
Alice,Wonder,alice@rijksoverheid.nl,
Charlie,Brown,charlie@rijksoverheid.nl,"""

        result = create_users_from_csv(None, csv_content)

        assert result["success"]
        assert result["users_created"] == 2
        assert result["labels_created"] == 0

        # Verify users have no labels
        alice = User.objects.get(email="alice@rijksoverheid.nl")
        assert alice.labels.count() == 0

        charlie = User.objects.get(email="charlie@rijksoverheid.nl")
        assert charlie.labels.count() == 0

    def test_csv_user_import_reuses_existing_labels(self):
        """Test: Importing multiple users with same brand reuses existing label"""
        # Pre-create the category and label (use get_or_create to avoid conflicts)
        merken_category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        existing_label = Label.objects.create(name="Pre-existing Brand", category=merken_category)

        csv_content = """first_name,last_name,email,brand
User,One,user1@rijksoverheid.nl,Pre-existing Brand
User,Two,user2@rijksoverheid.nl,Pre-existing Brand
User,Three,user3@rijksoverheid.nl,Pre-existing Brand"""

        result = create_users_from_csv(None, csv_content)

        assert result["success"]
        assert result["users_created"] == 3
        assert result["labels_created"] == 0  # No new labels created

        # Verify only one label exists with that name
        labels_count = Label.objects.filter(name="Pre-existing Brand").count()
        assert labels_count == 1

        # Verify all users have the same label
        user1 = User.objects.get(email="user1@rijksoverheid.nl")
        user2 = User.objects.get(email="user2@rijksoverheid.nl")
        user3 = User.objects.get(email="user3@rijksoverheid.nl")

        assert existing_label in user1.labels.all()
        assert existing_label in user2.labels.all()
        assert existing_label in user3.labels.all()

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

    def test_csv_assignment_import_with_brand_assigns_label(self):
        """Test: CSV placement import with brand columns assigns brand labels to new colleagues"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_tooi,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Test Description,Owner Name,owner@rijksoverheid.nl,,01-01-2025,31-12-2025,Python,John Doe,john@rijksoverheid.nl,Rijks ICT Gilde,Rijks ICT Gilde"""

        result = create_assignments_from_csv(csv_content)

        assert result["success"]
        assert result["colleagues_created"] > 0

        # Verify Merk category exists
        merken_category = LabelCategory.objects.get(name="Merk")

        # Verify Rijks ICT Gilde label was created
        rig_label = Label.objects.get(name="Rijks ICT Gilde", category=merken_category)

        # Verify colleagues have the label
        john = Colleague.objects.get(email="john@rijksoverheid.nl")
        assert rig_label in john.labels.all()

        owner = Colleague.objects.get(email="owner@rijksoverheid.nl")
        assert rig_label in owner.labels.all()

    def test_csv_placement_import_without_brand_no_label(self):
        """Test: CSV placement import without brand columns or empty brands creates colleagues with no labels"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_tooi,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Test Description,Owner Name,owner@test.com,,01-01-2025,31-12-2025,Python,John Doe,john@test.com,,"""

        result = create_assignments_from_csv(csv_content)

        assert result["success"]
        assert result["colleagues_created"] > 0

        # Verify colleagues have no labels
        john = Colleague.objects.get(email="john@test.com")
        assert john.labels.count() == 0

        owner = Colleague.objects.get(email="owner@test.com")
        assert owner.labels.count() == 0

    def test_csv_placement_import_multiple_brands(self):
        """Test: CSV placement import with different brands for owners vs colleagues"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_tooi,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Assignment 1,Test,Owner A,ownera@test.com,,01-01-2025,31-12-2025,Python,John Doe,john@test.com,Rijks ICT Gilde,Rijksconsultants
Assignment 2,Test,Owner B,ownerb@test.com,,01-01-2025,31-12-2025,Java,Jane Smith,jane@test.com,I-Interim Rijk,Rijks ICT Gilde"""

        result = create_assignments_from_csv(csv_content)

        assert result["success"]
        assert result["colleagues_created"] == 4  # 2 owners + 2 placement colleagues

        # Verify Merk category exists
        merken_category = LabelCategory.objects.get(name="Merk")

        # Verify brand labels were created
        rig_label = Label.objects.get(name="Rijks ICT Gilde", category=merken_category)
        rc_label = Label.objects.get(name="Rijksconsultants", category=merken_category)
        iir_label = Label.objects.get(name="I-Interim Rijk", category=merken_category)

        # Verify first row: owner has RIG, colleague has RC
        john = Colleague.objects.get(email="john@test.com")
        assert rc_label in john.labels.all()
        assert rig_label not in john.labels.all()

        owner_a = Colleague.objects.get(email="ownera@test.com")
        assert rig_label in owner_a.labels.all()
        assert rc_label not in owner_a.labels.all()

        # Verify second row: owner has IIR, colleague has RIG
        jane = Colleague.objects.get(email="jane@test.com")
        assert rig_label in jane.labels.all()
        assert iir_label not in jane.labels.all()

        owner_b = Colleague.objects.get(email="ownerb@test.com")
        assert iir_label in owner_b.labels.all()
        assert rig_label not in owner_b.labels.all()

    def test_csv_assignment_import_existing_colleague_no_duplicate_label(self):
        """Test: Re-importing placement for existing colleague doesn't duplicate label"""
        # Pre-create colleague with label (use get_or_create to avoid conflicts)
        merken_category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        rig_label, _ = Label.objects.get_or_create(name="Rijks ICT Gilde", category=merken_category)

        colleague = Colleague.objects.create(
            name="Existing Colleague", email="existing@rijksoverheid.nl", source="wies"
        )
        colleague.labels.add(rig_label)

        # Import placement with existing colleague and same brand
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_tooi,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
New Assignment,Description,,,,01-01-2025,31-12-2025,Django,Existing Colleague,existing@rijksoverheid.com"""

        result = create_assignments_from_csv(csv_content)

        assert result["success"]

        # Verify colleague still has only one label instance (no duplicate)
        colleague.refresh_from_db()
        assert colleague.labels.count() == 1
        assert rig_label in colleague.labels.all()

    @patch("wies.core.services.sync.OTYSAPI")
    def test_otys_sync_assigns_i_interim_rijk_label(self, mock_otys_api):
        """Test: OTYS sync assigns I-Interim Rijk label to synced colleagues"""
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

        # Verify Merk category and I-Interim Rijk label were created
        merken_category = LabelCategory.objects.get(name="Merk")
        iir_label = Label.objects.get(name="I-Interim Rijk", category=merken_category)

        # Verify both colleagues have the label
        jane = Colleague.objects.get(source_id="12345", source="otys_iir")
        assert iir_label in jane.labels.all()
        assert jane.name == "Jane Doe"

        john = Colleague.objects.get(source_id="67890", source="otys_iir")
        assert iir_label in john.labels.all()
        assert john.name == "John van Smith"

    @patch("wies.core.services.sync.OTYSAPI")
    def test_otys_sync_idempotency_no_duplicate_labels(self, mock_otys_api):
        """Test: Re-syncing OTYS data doesn't duplicate I-Interim Rijk label"""
        # Pre-create colleague with label (use get_or_create to avoid conflicts)
        merken_category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        iir_label, _ = Label.objects.get_or_create(name="I-Interim Rijk", category=merken_category)

        colleague = Colleague.objects.create(
            name="Existing OTYS User", source_id="99999", source="otys_iir", email="existing@otys.com"
        )
        colleague.labels.add(iir_label)

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

        # Verify colleague still has only one label instance
        colleague.refresh_from_db()
        assert colleague.labels.count() == 1
        assert iir_label in colleague.labels.all()

    def test_csv_and_otys_labels_coexist(self):
        """Test: Colleagues from different sources can have multiple labels"""
        # Create labels (use get_or_create to avoid conflicts)
        merken_category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        rig_label, _ = Label.objects.get_or_create(name="Rijks ICT Gilde", category=merken_category)
        iir_label, _ = Label.objects.get_or_create(name="I-Interim Rijk", category=merken_category)

        # Create colleague with both labels
        colleague = Colleague.objects.create(
            name="Multi-Label Colleague", email="multi@rijksoverheid.nl", source="wies"
        )
        colleague.labels.add(rig_label, iir_label)

        # Verify both labels are assigned
        assert colleague.labels.count() == 2
        assert rig_label in colleague.labels.all()
        assert iir_label in colleague.labels.all()

    def test_full_import_workflow_csv_to_ui_visibility(self):
        """Test: Complete workflow from CSV import to data visibility"""
        # Import users with labels
        csv_content = """first_name,last_name,email,brand
Test,User,testuser@rijksoverheid.nl,Test Brand"""

        result = create_users_from_csv(None, csv_content)
        assert result["success"]

        # Verify label was created in correct category
        merken_category = LabelCategory.objects.get(name="Merk")
        test_label = Label.objects.get(name="Test Brand", category=merken_category)

        # Verify user has label
        user = User.objects.get(email="testuser@rijksoverheid.nl")
        assert test_label in user.labels.all()

        # Verify label appears in queryset (simulating UI display)
        users_with_label = User.objects.filter(labels=test_label)
        assert user in users_with_label
