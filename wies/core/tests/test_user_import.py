from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Permission, Group

from wies.core.models import User, Brand


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class UserImportTest(TestCase):
    """Tests for CSV user import functionality"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.import_url = reverse('user-import-csv')

        # Create test groups
        self.admin_group = Group.objects.create(name='Administrator')
        self.consultant_group = Group.objects.create(name='Consultant')
        self.bdm_group = Group.objects.create(name='BDM')

        # Create test brand
        self.existing_brand = Brand.objects.create(name='Existing Brand')

        # Create authenticated user with add_user permission
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )
        add_permission = Permission.objects.get(codename='add_user')
        self.auth_user.user_permissions.add(add_permission)

        # Create user without permissions
        self.no_perm_user = User.objects.create(
            username="nopermuser",
            email="noperm@example.com",
            first_name="No",
            last_name="Permission",
        )

    def _create_csv_file(self, content):
        """Helper to create a CSV file upload"""
        return SimpleUploadedFile(
            "users.csv",
            content.encode('utf-8'),
            content_type="text/csv"
        )

    def test_import_requires_login(self):
        """Test that import endpoint requires authentication"""
        response = self.client.get(self.import_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_import_requires_add_permission(self):
        """Test that import requires add_user permission"""
        self.client.force_login(self.no_perm_user)
        response = self.client.get(self.import_url)
        self.assertEqual(response.status_code, 403)

    def test_import_get_returns_form(self):
        """Test that GET request returns the import form"""
        self.client.force_login(self.auth_user)
        response = self.client.get(self.import_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('user-import-modal', content)
        self.assertIn('Gebruikers importeren', content)
        self.assertIn('csv_file', content)

    def test_import_requires_file_upload(self):
        """Test that import requires a file to be uploaded"""
        self.client.force_login(self.auth_user)
        response = self.client.post(self.import_url, {})

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Geen bestand geüpload', content)

    def test_import_validates_csv_file_type(self):
        """Test that import validates file is a CSV"""
        self.client.force_login(self.auth_user)
        txt_file = SimpleUploadedFile(
            "users.txt",
            b"not a csv",
            content_type="text/plain"
        )

        response = self.client.post(
            self.import_url,
            {'csv_file': txt_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Ongeldig bestandstype', content)

    def test_import_valid_csv_creates_users(self):
        """Test successful import of valid CSV with users"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Administrator,Consultant,BDM
John,Doe,john.doe@example.com,Brand A,y,n,n
Jane,Smith,jane.smith@example.com,Brand B,n,y,n"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import geslaagd', content)
        self.assertIn('2', content)  # 2 users created
        self.assertIn('Brand A', content)
        self.assertIn('Brand B', content)

        # Verify users were created
        john = User.objects.get(email='john.doe@example.com')
        self.assertEqual(john.first_name, 'John')
        self.assertEqual(john.last_name, 'Doe')
        self.assertEqual(john.brand.name, 'Brand A')
        self.assertTrue(john.groups.filter(name='Administrator').exists())
        self.assertFalse(john.groups.filter(name='Consultant').exists())

        jane = User.objects.get(email='jane.smith@example.com')
        self.assertEqual(jane.first_name, 'Jane')
        self.assertTrue(jane.groups.filter(name='Consultant').exists())
        self.assertFalse(jane.groups.filter(name='Administrator').exists())

    def test_import_reuses_existing_brands(self):
        """Test that import reuses existing brands instead of creating duplicates"""
        self.client.force_login(self.auth_user)
        csv_content = f"""first_name,last_name,email,brand,Administrator,Consultant,BDM
John,Doe,john.doe@example.com,{self.existing_brand.name},n,n,n"""
        csv_file = self._create_csv_file(csv_content)

        brand_count_before = Brand.objects.count()

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import geslaagd', content)
        self.assertEqual(Brand.objects.count(), brand_count_before)

        john = User.objects.get(email='john.doe@example.com')
        self.assertEqual(john.brand, self.existing_brand)

    def test_import_validates_missing_required_columns(self):
        """Test that import validates required columns are present"""
        self.client.force_login(self.auth_user)
        csv_content = "first_name,last_name\nJohn,Doe"
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import mislukt', content)
        self.assertIn('Missing required columns', content)
        self.assertIn('email', content)

    def test_import_validates_missing_required_fields(self):
        """Test that import validates required fields have values"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,,john@example.com
,Doe,jane@example.com"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import mislukt', content)
        self.assertIn('Row 2', content)
        self.assertIn('last_name', content)
        self.assertIn('Row 3', content)
        self.assertIn('first_name', content)

    def test_import_validates_email_format(self):
        """Test that import validates email format"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,Doe,invalid-email
Jane,Smith,also-invalid"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import mislukt', content)
        self.assertIn('invalid email format', content)

    def test_import_validates_group_values(self):
        """Test that import validates group columns have 'y' or 'n' values"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Administrator,Consultant,BDM
John,Doe,john@example.com,Brand A,yes,n,n
Jane,Smith,jane@example.com,Brand B,y,maybe,n"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import mislukt', content)
        self.assertIn('Administrator', content)
        self.assertIn('must be', content)
        self.assertIn('Consultant', content)

    def test_import_detects_duplicate_emails_in_csv(self):
        """Test that import detects duplicate emails within the CSV"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,Doe,duplicate@example.com
Jane,Smith,duplicate@example.com"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import mislukt', content)
        self.assertIn('duplicate email', content)

    def test_import_skips_existing_users(self):
        """Test that import skips users with existing email addresses"""
        self.client.force_login(self.auth_user)
        # Create existing user
        User.objects.create(
            username='existing',
            email='existing@example.com',
            first_name='Existing',
            last_name='User'
        )

        csv_content = """first_name,last_name,email
John,Doe,john@example.com
Jane,Smith,existing@example.com"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import geslaagd', content)
        self.assertIn('1', content)  # Only 1 user created
        self.assertIn('already exists', content)

        # Verify only John was created
        self.assertTrue(User.objects.filter(email='john@example.com').exists())
        self.assertEqual(User.objects.filter(email='existing@example.com').count(), 1)

    def test_import_without_optional_fields(self):
        """Test import with only required fields (no brand, no groups)"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,Doe,john@example.com"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import geslaagd', content)

        john = User.objects.get(email='john@example.com')
        self.assertIsNone(john.brand)
        self.assertEqual(john.groups.count(), 0)

    def test_import_with_multiple_groups(self):
        """Test user assigned to multiple groups"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Administrator,Consultant,BDM
John,Doe,john@example.com,Brand A,y,y,y"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import geslaagd', content)

        john = User.objects.get(email='john@example.com')
        self.assertEqual(john.groups.count(), 3)
        self.assertTrue(john.groups.filter(name='Administrator').exists())
        self.assertTrue(john.groups.filter(name='Consultant').exists())
        self.assertTrue(john.groups.filter(name='BDM').exists())

    def test_import_empty_csv(self):
        """Test import with empty CSV file"""
        self.client.force_login(self.auth_user)
        csv_content = ""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import mislukt', content)
        self.assertIn('empty', content)

    def test_import_csv_with_only_headers(self):
        """Test import with CSV that has headers but no data rows"""
        self.client.force_login(self.auth_user)
        csv_content = "first_name,last_name,email"
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import geslaagd', content)
        self.assertIn('0', content)  # 0 users created

    def test_import_validates_all_before_creating(self):
        """Test that validation happens before any users are created"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email
John,Doe,john@example.com
Jane,Smith,invalid-email"""
        csv_file = self._create_csv_file(csv_content)

        user_count_before = User.objects.count()

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import mislukt', content)
        # No users should be created if validation fails
        self.assertEqual(User.objects.count(), user_count_before)

    def test_import_handles_whitespace_in_fields(self):
        """Test that import properly trims whitespace from fields"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Administrator,Consultant,BDM
  John  ,  Doe  ,  john@example.com  ,  Brand A  , y , n , n """
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import geslaagd', content)

        john = User.objects.get(email='john@example.com')
        self.assertEqual(john.first_name, 'John')
        self.assertEqual(john.last_name, 'Doe')
        self.assertEqual(john.brand.name, 'Brand A')
