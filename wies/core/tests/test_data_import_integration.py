from pathlib import Path
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from wies.core.models import User, Colleague, LabelCategory, Label, Assignment, Service, Placement
from wies.core.services.users import create_users_from_csv
from wies.core.services.placements import create_placements_from_csv
from wies.core.services.sync import sync_all_otys_iir_records


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class DataImportIntegrationTest(TestCase):
    """High-level integration tests for CSV imports and OTYS sync with label assignment"""

    def setUp(self):
        """Create necessary groups for CSV import tests"""
        from django.contrib.auth.models import Group
        Group.objects.get_or_create(name='Beheerder')
        Group.objects.get_or_create(name='Consultant')
        Group.objects.get_or_create(name='Business Development Manager')

    def test_csv_user_import_with_brand_creates_labels(self):
        """Test: CSV with brand column creates users with labels in Merk category"""
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
John,Doe,john@example.com,Rijks ICT Gilde,y,n,n
Jane,Smith,jane@example.com,Rijksconsultants,n,y,n
Bob,Johnson,bob@example.com,Rijks ICT Gilde,n,n,y"""

        result = create_users_from_csv(csv_content)

        # Verify import success
        self.assertTrue(result['success'])
        self.assertEqual(result['users_created'], 3)
        self.assertEqual(result['labels_created'], 2)  # Two unique brands
        self.assertIn('Rijks ICT Gilde', result['created_labels'])
        self.assertIn('Rijksconsultants', result['created_labels'])

        # Verify Merk category was created
        merken_category = LabelCategory.objects.get(name='Merk')

        # Verify labels were created in Merk category
        rig_label = Label.objects.get(name='Rijks ICT Gilde', category=merken_category)
        rc_label = Label.objects.get(name='Rijksconsultants', category=merken_category)

        # Verify users have correct labels
        john = User.objects.get(email='john@example.com')
        self.assertIn(rig_label, john.labels.all())

        jane = User.objects.get(email='jane@example.com')
        self.assertIn(rc_label, jane.labels.all())

        bob = User.objects.get(email='bob@example.com')
        self.assertIn(rig_label, bob.labels.all())

    def test_csv_user_import_without_brand_creates_users_without_labels(self):
        """Test: CSV without brand column or empty brand creates users with no labels"""
        csv_content = """first_name,last_name,email,brand
Alice,Wonder,alice@example.com,
Charlie,Brown,charlie@example.com,"""

        result = create_users_from_csv(csv_content)

        self.assertTrue(result['success'])
        self.assertEqual(result['users_created'], 2)
        self.assertEqual(result['labels_created'], 0)

        # Verify users have no labels
        alice = User.objects.get(email='alice@example.com')
        self.assertEqual(alice.labels.count(), 0)

        charlie = User.objects.get(email='charlie@example.com')
        self.assertEqual(charlie.labels.count(), 0)

    def test_csv_user_import_reuses_existing_labels(self):
        """Test: Importing multiple users with same brand reuses existing label"""
        # Pre-create the category and label (use get_or_create to avoid conflicts)
        merken_category, _ = LabelCategory.objects.get_or_create(
            name='Merk',
            defaults={'color': '#0066CC'}
        )
        existing_label = Label.objects.create(name='Pre-existing Brand', category=merken_category)

        csv_content = """first_name,last_name,email,brand
User,One,user1@example.com,Pre-existing Brand
User,Two,user2@example.com,Pre-existing Brand
User,Three,user3@example.com,Pre-existing Brand"""

        result = create_users_from_csv(csv_content)

        self.assertTrue(result['success'])
        self.assertEqual(result['users_created'], 3)
        self.assertEqual(result['labels_created'], 0)  # No new labels created

        # Verify only one label exists with that name
        labels_count = Label.objects.filter(name='Pre-existing Brand').count()
        self.assertEqual(labels_count, 1)

        # Verify all users have the same label
        user1 = User.objects.get(email='user1@example.com')
        user2 = User.objects.get(email='user2@example.com')
        user3 = User.objects.get(email='user3@example.com')

        self.assertIn(existing_label, user1.labels.all())
        self.assertIn(existing_label, user2.labels.all())
        self.assertIn(existing_label, user3.labels.all())

    def test_csv_user_import_duplicate_email_handling(self):
        """Test: Re-importing user with existing email skips and warns"""
        # First import
        csv_content1 = """first_name,last_name,email,brand
Original,Name,duplicate@example.com,Brand A"""

        result1 = create_users_from_csv(csv_content1)
        self.assertTrue(result1['success'])
        self.assertEqual(result1['users_created'], 1)

        # Second import with same email
        csv_content2 = """first_name,last_name,email,brand
Different,Name,duplicate@example.com,Brand B"""

        result2 = create_users_from_csv(csv_content2)
        self.assertTrue(result2['success'])
        self.assertEqual(result2['users_created'], 0)
        self.assertIn("duplicate@example.com", result2['errors'][0])

        # Verify original user unchanged
        user = User.objects.get(email='duplicate@example.com')
        self.assertEqual(user.first_name, 'Original')
        self.assertEqual(user.last_name, 'Name')

    def test_csv_placement_import_assigns_rijks_ict_gilde_label(self):
        """Test: CSV placement import assigns Rijks ICT Gilde label to new colleagues"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Test Description,Owner Name,owner@test.com,Test Org,,01-01-2025,31-12-2025,Python,John Doe,john@test.com"""

        result = create_placements_from_csv(csv_content)

        self.assertTrue(result['success'])
        self.assertGreater(result['colleagues_created'], 0)

        # Verify Merk category exists
        merken_category = LabelCategory.objects.get(name='Merk')

        # Verify Rijks ICT Gilde label was created
        rig_label = Label.objects.get(name='Rijks ICT Gilde', category=merken_category)

        # Verify colleagues have the label
        john = Colleague.objects.get(email='john@test.com')
        self.assertIn(rig_label, john.labels.all())

        owner = Colleague.objects.get(email='owner@test.com')
        self.assertIn(rig_label, owner.labels.all())

    def test_csv_placement_import_existing_colleague_no_duplicate_label(self):
        """Test: Re-importing placement for existing colleague doesn't duplicate label"""
        # Pre-create colleague with label (use get_or_create to avoid conflicts)
        merken_category, _ = LabelCategory.objects.get_or_create(
            name='Merk',
            defaults={'color': '#0066CC'}
        )
        rig_label, _ = Label.objects.get_or_create(
            name='Rijks ICT Gilde',
            category=merken_category
        )

        colleague = Colleague.objects.create(
            name='Existing Colleague',
            email='existing@test.com',
            source='wies'
        )
        colleague.labels.add(rig_label)

        # Import placement with existing colleague
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
New Assignment,Description,,,Test Org,,01-01-2025,31-12-2025,Django,Existing Colleague,existing@test.com"""

        result = create_placements_from_csv(csv_content)

        self.assertTrue(result['success'])

        # Verify colleague still has only one label instance
        colleague.refresh_from_db()
        self.assertEqual(colleague.labels.count(), 1)
        self.assertIn(rig_label, colleague.labels.all())

    @patch('wies.core.services.sync.OTYSAPI')
    def test_otys_sync_assigns_i_interim_rijk_label(self, mock_otys_api):
        """Test: OTYS sync assigns I-Interim Rijk label to synced colleagues"""
        # Mock OTYS API responses
        mock_api_instance = Mock()
        mock_otys_api.return_value.__enter__.return_value = mock_api_instance

        mock_api_instance.get_candidate_list.return_value = {
            'listOutput': [
                {
                    'uid': '12345',
                    'Person': {
                        'firstName': 'Jane',
                        'lastName': 'Doe',
                        'infix': '',
                        'emailPrimary': 'jane@otys.com'
                    }
                },
                {
                    'uid': '67890',
                    'Person': {
                        'firstName': 'John',
                        'lastName': 'Smith',
                        'infix': 'van',
                        'emailPrimary': 'john@otys.com'
                    }
                }
            ]
        }

        mock_api_instance.get_vacancy_list.return_value = {'listOutput': []}

        # Run sync
        with patch.dict('os.environ', {'OTYS_API_KEY': 'test_key', 'OTYS_URL': 'https://test.otys.com'}):
            result = sync_all_otys_iir_records()

        self.assertEqual(result['candidates_synced'], 2)

        # Verify Merk category and I-Interim Rijk label were created
        merken_category = LabelCategory.objects.get(name='Merk')
        iir_label = Label.objects.get(name='I-Interim Rijk', category=merken_category)

        # Verify both colleagues have the label
        jane = Colleague.objects.get(source_id='12345', source='otys_iir')
        self.assertIn(iir_label, jane.labels.all())
        self.assertEqual(jane.name, 'Jane Doe')

        john = Colleague.objects.get(source_id='67890', source='otys_iir')
        self.assertIn(iir_label, john.labels.all())
        self.assertEqual(john.name, 'John van Smith')

    @patch('wies.core.services.sync.OTYSAPI')
    def test_otys_sync_idempotency_no_duplicate_labels(self, mock_otys_api):
        """Test: Re-syncing OTYS data doesn't duplicate I-Interim Rijk label"""
        # Pre-create colleague with label (use get_or_create to avoid conflicts)
        merken_category, _ = LabelCategory.objects.get_or_create(
            name='Merk',
            defaults={'color': '#0066CC'}
        )
        iir_label, _ = Label.objects.get_or_create(
            name='I-Interim Rijk',
            category=merken_category
        )

        colleague = Colleague.objects.create(
            name='Existing OTYS User',
            source_id='99999',
            source='otys_iir',
            email='existing@otys.com'
        )
        colleague.labels.add(iir_label)

        # Mock OTYS API to return the same colleague
        mock_api_instance = Mock()
        mock_otys_api.return_value.__enter__.return_value = mock_api_instance

        mock_api_instance.get_candidate_list.return_value = {
            'listOutput': [
                {
                    'uid': '99999',
                    'Person': {
                        'firstName': 'Existing OTYS',
                        'lastName': 'User',
                        'infix': '',
                        'emailPrimary': 'existing@otys.com'
                    }
                }
            ]
        }

        mock_api_instance.get_vacancy_list.return_value = {'listOutput': []}

        # Run sync again
        with patch.dict('os.environ', {'OTYS_API_KEY': 'test_key', 'OTYS_URL': 'https://test.otys.com'}):
            result = sync_all_otys_iir_records()

        self.assertEqual(result['candidates_synced'], 1)

        # Verify colleague still has only one label instance
        colleague.refresh_from_db()
        self.assertEqual(colleague.labels.count(), 1)
        self.assertIn(iir_label, colleague.labels.all())

    def test_csv_and_otys_labels_coexist(self):
        """Test: Colleagues from different sources can have multiple labels"""
        # Create labels (use get_or_create to avoid conflicts)
        merken_category, _ = LabelCategory.objects.get_or_create(
            name='Merk',
            defaults={'color': '#0066CC'}
        )
        rig_label, _ = Label.objects.get_or_create(
            name='Rijks ICT Gilde',
            category=merken_category
        )
        iir_label, _ = Label.objects.get_or_create(
            name='I-Interim Rijk',
            category=merken_category
        )

        # Create colleague with both labels
        colleague = Colleague.objects.create(
            name='Multi-Label Colleague',
            email='multi@test.com',
            source='wies'
        )
        colleague.labels.add(rig_label, iir_label)

        # Verify both labels are assigned
        self.assertEqual(colleague.labels.count(), 2)
        self.assertIn(rig_label, colleague.labels.all())
        self.assertIn(iir_label, colleague.labels.all())

    def test_full_import_workflow_csv_to_ui_visibility(self):
        """Test: Complete workflow from CSV import to data visibility"""
        # Import users with labels
        csv_content = """first_name,last_name,email,brand
Test,User,testuser@example.com,Test Brand"""

        result = create_users_from_csv(csv_content)
        self.assertTrue(result['success'])

        # Verify label was created in correct category
        merken_category = LabelCategory.objects.get(name='Merk')
        test_label = Label.objects.get(name='Test Brand', category=merken_category)

        # Verify user has label
        user = User.objects.get(email='testuser@example.com')
        self.assertIn(test_label, user.labels.all())

        # Verify label appears in queryset (simulating UI display)
        users_with_label = User.objects.filter(labels=test_label)
        self.assertIn(user, users_with_label)
