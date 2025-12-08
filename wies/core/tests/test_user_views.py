from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import Permission, Group
from django.core.files.uploadedfile import SimpleUploadedFile


from wies.core.models import User, LabelCategory, Label


@override_settings(
    # Use simple static files storage for tests
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class UserViewsTest(TestCase):
    """Tests for user list, creation, and deletion views"""

    def setUp(self):
        """Create test data"""
        self.client = Client()

        # Create a regular user for authentication
        self.auth_user = User.objects.create(
            username="auth_user",
            email="auth@example.com",
            first_name="Auth",
            last_name="User",
        )

        # Grant all user permissions to auth_user for existing tests
        view_permission = Permission.objects.get(codename='view_user')
        add_permission = Permission.objects.get(codename='add_user')
        change_permission = Permission.objects.get(codename='change_user')
        delete_permission = Permission.objects.get(codename='delete_user')
        self.auth_user.user_permissions.add(view_permission, add_permission, change_permission, delete_permission)

        # Create a superuser (should be excluded from list)
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123",
            first_name="Admin",
            last_name="User",
        )

        # Create test labels
        self.category, _ = LabelCategory.objects.get_or_create(name='Merk', defaults={'color': '#0066CC'})
        self.label_a = Label.objects.create(name="Brand A", category=self.category)
        self.label_b = Label.objects.create(name="Brand B", category=self.category)

        # Create test groups for form testing
        self.admin_group = Group.objects.create(name="Beheerder")
        self.consultant_group = Group.objects.create(name="Consultant")
        self.bdm_group = Group.objects.create(name="Business Development Manager")

        # Create test users
        self.user1 = User.objects.create(
            username="user1",
            email="user1@example.com",
            first_name="John",
            last_name="Doe",
        )
        self.user1.labels.add(self.label_a)

        self.user2 = User.objects.create(
            username="user2",
            email="user2@example.com",
            first_name="Jane",
            last_name="Smith",
        )
        self.user2.labels.add(self.label_b)

    def test_user_list_requires_login(self):
        """Test that user list requires authentication"""
        response = self.client.get(reverse('admin-users'), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_user_list_excludes_superusers(self):
        """Test that superusers are excluded from user list"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse('admin-users'))

        self.assertEqual(response.status_code, 200)

        # Check response content for user emails
        content = response.content.decode()

        # Regular users should be in the list
        self.assertIn(self.user1.get_full_name(), content)
        self.assertIn(self.user2.get_full_name(), content)
        self.assertIn(self.auth_user.get_full_name(), content)

        # Superuser should NOT be in the list
        self.assertNotIn(self.superuser.get_full_name(), content)

    def test_user_list_label_filter(self):
        """Test filtering users by label"""
        self.client.force_login(self.auth_user)

        # Filter by label A
        response = self.client.get(reverse('admin-users'), {'label': self.label_a.id})
        content = response.content.decode()

        # user1 should be in results
        self.assertIn(self.user1.get_full_name(), content)
        # user2 should not be in results
        self.assertNotIn(self.user2.get_full_name(), content)

    def test_user_list_search(self):
        """Test searching users by name or email"""
        self.client.force_login(self.auth_user)

        # Search by first name
        response = self.client.get(reverse('admin-users'), {'search': 'John'})
        content = response.content.decode()
        self.assertIn(self.user1.get_full_name(), content)
        self.assertNotIn(self.user2.get_full_name(), content)

        # Search by email
        response = self.client.get(reverse('admin-users'), {'search': 'jane'})
        content = response.content.decode()
        self.assertIn(self.user2.get_full_name(), content)
        self.assertNotIn(self.user1.get_full_name(), content)

    def test_user_list_search_full_name(self):
        """Test searching users by full name (first and last name together)"""
        self.client.force_login(self.auth_user)

        # Search by full name "John Doe" - this should find user1 but currently doesn't
        response = self.client.get(reverse('admin-users'), {'search': 'John Doe'})
        content = response.content.decode()
        self.assertIn(self.user1.get_full_name(), content)
        self.assertNotIn(self.user2.get_full_name(), content)

    def test_user_create_get_returns_form(self):
        """Test that GET to user-create returns the form modal"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse('user-create'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('modal-content', content)
        self.assertIn('Nieuwe gebruiker', content)

    def test_user_create_success(self):
        """Test successful user creation"""
        self.client.force_login(self.auth_user)

        initial_count = User.objects.filter(is_superuser=False).count()

        response = self.client.post(reverse('user-create'), {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'category_Merk': self.label_a.id,
        })

        # Should redirect to users list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admin-users'))

        # User should be created
        self.assertEqual(User.objects.filter(is_superuser=False).count(), initial_count + 1)

        # Verify user details
        new_user = User.objects.get(email='newuser@example.com')
        self.assertEqual(new_user.first_name, 'New')
        self.assertEqual(new_user.last_name, 'User')
        self.assertTrue(new_user.labels.filter(id=self.label_a.id).exists())
        self.assertFalse(new_user.is_superuser)

    def test_user_create_without_labels(self):
        """Test user creation without labels (optional field)"""
        self.client.force_login(self.auth_user)

        response = self.client.post(reverse('user-create'), {
            'first_name': 'No',
            'last_name': 'Labels',
            'email': 'nolabels@example.com',
        })

        # Should redirect to users list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admin-users'))

        new_user = User.objects.get(email='nolabels@example.com')
        self.assertEqual(new_user.labels.count(), 0)

    def test_user_create_validation_errors(self):
        """Test user creation with validation errors"""
        self.client.force_login(self.auth_user)

        # Missing required field
        response = self.client.post(reverse('user-create'), {
            'first_name': 'Missing',
            # Missing last_name and email
        })

        # Should return 200 with form errors (re-rendered modal)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Modal should be shown with errors
        self.assertIn('modal-content', content)

    def test_user_create_duplicate_email(self):
        """Test that a new user cannot be created with an existing email"""
        self.client.force_login(self.auth_user)

        # Try to create a user with an email that already exists
        response = self.client.post(reverse('user-create'), {
            'first_name': 'Duplicate',
            'last_name': 'User',
            'email': 'user1@example.com',  # This email already exists (user1)
        })

        # Should return 200 with form errors (re-rendered modal)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Modal should be shown with errors
        self.assertIn('modal-content', content)
        # Should contain error message about duplicate email
        self.assertIn('email', content.lower())

        # User should not be created
        self.assertEqual(User.objects.filter(email='user1@example.com').count(), 1)

    def test_user_create_requires_login(self):
        """Test that user creation requires authentication"""
        response = self.client.post(reverse('user-create'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_user_delete_success(self):
        """Test successful user deletion"""
        self.client.force_login(self.auth_user)

        initial_count = User.objects.count()
        user_id = self.user1.id

        response = self.client.post(reverse('user-delete', args=[user_id]))

        # Should redirect to users list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admin-users'))

        # User should be deleted
        self.assertEqual(User.objects.count(), initial_count - 1)
        self.assertFalse(User.objects.filter(id=user_id).exists())

    def test_user_delete_prevents_superuser_deletion(self):
        """Test that superusers cannot be deleted via this endpoint"""
        self.client.force_login(self.auth_user)

        response = self.client.post(reverse('user-delete', args=[self.superuser.id]))

        # Should return 404 (get_object_or_404 with is_superuser=False)
        self.assertEqual(response.status_code, 404)

        # Superuser should still exist
        self.assertTrue(User.objects.filter(id=self.superuser.id).exists())

    def test_user_delete_nonexistent_user(self):
        """Test deletion of non-existent user returns 404"""
        self.client.force_login(self.auth_user)

        response = self.client.post(reverse('user-delete', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_user_delete_requires_login(self):
        """Test that user deletion requires authentication"""
        response = self.client.post(reverse('user-delete', args=[self.user1.id]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    # Permission tests
    def test_user_list_requires_view_permission(self):
        """Test that user list returns 403 without view_user permission"""
        # Create user without view_user permission
        user_no_perms = User.objects.create(
            username="no_perms",
            email="noperms@example.com",
            first_name="No",
            last_name="Perms",
        )
        self.client.force_login(user_no_perms)

        response = self.client.get(reverse('admin-users'))
        self.assertEqual(response.status_code, 403)

    def test_user_list_allows_with_view_permission(self):
        """Test that user list works with view_user permission"""
        user_with_perms = User.objects.create(
            username="with_perms",
            email="withperms@example.com",
            first_name="With",
            last_name="Perms",
        )
        view_permission = Permission.objects.get(codename='view_user')
        user_with_perms.user_permissions.add(view_permission)
        self.client.force_login(user_with_perms)

        response = self.client.get(reverse('admin-users'))
        self.assertEqual(response.status_code, 200)

    def test_user_create_requires_add_permission(self):
        """Test that user creation returns 403 without add_user permission"""
        # Create user with only view permission
        user_view_only = User.objects.create(
            username="view_only",
            email="viewonly@example.com",
            first_name="View",
            last_name="Only",
        )
        view_permission = Permission.objects.get(codename='view_user')
        user_view_only.user_permissions.add(view_permission)
        self.client.force_login(user_view_only)

        # Try to create user
        response = self.client.post(reverse('user-create'), {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
        })
        self.assertEqual(response.status_code, 403)

        # User should not be created
        self.assertFalse(User.objects.filter(email='newuser@example.com').exists())

    def test_user_create_get_requires_add_permission(self):
        """Test that getting the user creation form returns 403 without add_user permission"""
        user_no_add = User.objects.create(
            username="no_add",
            email="noadd@example.com",
            first_name="No",
            last_name="Add",
        )
        self.client.force_login(user_no_add)

        response = self.client.get(reverse('user-create'))
        self.assertEqual(response.status_code, 403)

    def test_user_delete_requires_delete_permission(self):
        """Test that user deletion returns 403 without delete_user permission"""
        # Create user with only view permission
        user_view_only = User.objects.create(
            username="view_only2",
            email="viewonly2@example.com",
            first_name="View",
            last_name="Only2",
        )
        view_permission = Permission.objects.get(codename='view_user')
        user_view_only.user_permissions.add(view_permission)
        self.client.force_login(user_view_only)

        initial_count = User.objects.count()

        # Try to delete user
        response = self.client.post(reverse('user-delete', args=[self.user1.id]))
        self.assertEqual(response.status_code, 403)

        # User should not be deleted
        self.assertEqual(User.objects.count(), initial_count)
        self.assertTrue(User.objects.filter(id=self.user1.id).exists())

    def test_user_edit_get_returns_form_with_data(self):
        """Test that GET to user-edit returns the form modal with user data"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse('user-edit', args=[self.user1.id]))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('modal-content', content)
        self.assertIn('Gebruiker bewerken', content)
        # Check that form is pre-populated
        self.assertIn(self.user1.first_name, content)
        self.assertIn(self.user1.last_name, content)
        self.assertIn(self.user1.email, content)

    def test_user_edit_success(self):
        """Test successful user editing"""
        self.client.force_login(self.auth_user)

        response = self.client.post(reverse('user-edit', args=[self.user1.id]), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
        })

        # Should redirect to users list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admin-users'))

        # User should be updated
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'Updated')
        self.assertEqual(self.user1.last_name, 'Name')
        self.assertEqual(self.user1.email, 'updated@example.com')

    def test_user_edit_validation_errors(self):
        """Test user editing with validation errors"""
        self.client.force_login(self.auth_user)

        # Missing required field
        response = self.client.post(reverse('user-edit', args=[self.user1.id]), {
            'first_name': 'Updated',
            # Missing last_name and email
        })

        # Should return 200 with form errors (re-rendered modal)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Modal should be shown with errors
        self.assertIn('modal-content', content)
        self.assertIn('Gebruiker bewerken', content)

        # User should not be updated
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'John')

    def test_user_edit_prevents_superuser_editing(self):
        """Test that superusers cannot be edited via this endpoint"""
        self.client.force_login(self.auth_user)

        response = self.client.post(reverse('user-edit', args=[self.superuser.id]), {
            'first_name': 'Hacked',
            'last_name': 'Admin',
            'email': 'hacked@example.com',
        })

        # Should return 404 (get_object_or_404 with is_superuser=False)
        self.assertEqual(response.status_code, 404)

        # Superuser should not be modified
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.first_name, 'Admin')

    def test_user_edit_nonexistent_user(self):
        """Test editing of non-existent user returns 404"""
        self.client.force_login(self.auth_user)

        response = self.client.get(reverse('user-edit', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_user_edit_requires_login(self):
        """Test that user editing requires authentication"""
        response = self.client.post(reverse('user-edit', args=[self.user1.id]), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_user_edit_requires_change_permission(self):
        """Test that user editing returns 403 without change_user permission"""
        # Create user with only view permission
        user_view_only = User.objects.create(
            username="view_only3",
            email="viewonly3@example.com",
            first_name="View",
            last_name="Only3",
        )
        view_permission = Permission.objects.get(codename='view_user')
        user_view_only.user_permissions.add(view_permission)
        self.client.force_login(user_view_only)

        # Try to edit user
        response = self.client.post(reverse('user-edit', args=[self.user1.id]), {
            'first_name': 'Unauthorized',
            'last_name': 'Edit',
            'email': 'unauthorized@example.com',
        })
        self.assertEqual(response.status_code, 403)

        # User should not be updated
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'John')

    def test_user_edit_get_requires_change_permission(self):
        """Test that getting the user edit form returns 403 without change_user permission"""
        user_no_change = User.objects.create(
            username="no_change",
            email="nochange@example.com",
            first_name="No",
            last_name="Change",
        )
        self.client.force_login(user_no_change)

        response = self.client.get(reverse('user-edit', args=[self.user1.id]))
        self.assertEqual(response.status_code, 403)

    def test_user_create_uses_rvo_styling(self):
        """Test that user create/edit views use RVO design system styling"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse('user-create'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Simple integration test - verify RVO classes are present
        self.assertIn('rvo-label', content)
        self.assertIn('utrecht-form-field', content)


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
        self.admin_group = Group.objects.create(name='Beheerder')
        self.consultant_group = Group.objects.create(name='Consultant')
        self.bdm_group = Group.objects.create(name='Business Development Manager')

        # Create test label
        category, _ = LabelCategory.objects.get_or_create(name='Merk', defaults={'color': '#0066CC'})
        self.existing_label = Label.objects.create(name='Existing Brand', category=category)

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
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
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
        # Verify label was assigned (Brand A should be created as label)
        self.assertTrue(john.labels.filter(name='Brand A').exists())
        self.assertTrue(john.groups.filter(name='Beheerder').exists())
        self.assertFalse(john.groups.filter(name='Consultant').exists())

        jane = User.objects.get(email='jane.smith@example.com')
        self.assertEqual(jane.first_name, 'Jane')
        self.assertTrue(jane.groups.filter(name='Consultant').exists())
        self.assertFalse(jane.groups.filter(name='Beheerder').exists())

    def test_import_reuses_existing_labels(self):
        """Test that import reuses existing labels instead of creating duplicates"""
        self.client.force_login(self.auth_user)
        csv_content = f"""first_name,last_name,email,brand,Administrator,Consultant,BDM
John,Doe,john.doe@example.com,{self.existing_label.name},n,n,n"""
        csv_file = self._create_csv_file(csv_content)

        label_count_before = Label.objects.count()

        response = self.client.post(
            self.import_url,
            {'csv_file': csv_file}
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Import geslaagd', content)
        self.assertEqual(Label.objects.count(), label_count_before)

        john = User.objects.get(email='john.doe@example.com')
        self.assertTrue(john.labels.filter(id=self.existing_label.id).exists())

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
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
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
        self.assertIn('Beheerder', content)
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
        self.assertEqual(john.labels.count(), 0)
        self.assertEqual(john.groups.count(), 0)

    def test_import_with_multiple_groups(self):
        """Test user assigned to multiple groups"""
        self.client.force_login(self.auth_user)
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
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
        self.assertTrue(john.groups.filter(name='Beheerder').exists())
        self.assertTrue(john.groups.filter(name='Consultant').exists())
        self.assertTrue(john.groups.filter(name='Business Development Manager').exists())

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
        csv_content = """first_name,last_name,email,brand,Beheerder,Consultant,BDM
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
        self.assertTrue(john.labels.filter(name='Brand A').exists())
