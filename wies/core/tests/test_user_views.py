from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import Permission

from wies.core.models import User, Brand


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

        # Create test brands
        self.brand_a = Brand.objects.create(name="Brand A")
        self.brand_b = Brand.objects.create(name="Brand B")

        # Create test users
        self.user1 = User.objects.create(
            username="user1",
            email="user1@example.com",
            first_name="John",
            last_name="Doe",
            brand=self.brand_a,
        )

        self.user2 = User.objects.create(
            username="user2",
            email="user2@example.com",
            first_name="Jane",
            last_name="Smith",
            brand=self.brand_b,
        )

    def test_user_list_requires_login(self):
        """Test that user list requires authentication"""
        response = self.client.get(reverse('users'), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_user_list_excludes_superusers(self):
        """Test that superusers are excluded from user list"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse('users'))

        self.assertEqual(response.status_code, 200)

        # Check response content for user emails
        content = response.content.decode()

        # Regular users should be in the list
        self.assertIn(self.user1.email, content)
        self.assertIn(self.user2.email, content)
        self.assertIn(self.auth_user.email, content)

        # Superuser should NOT be in the list
        self.assertNotIn(self.superuser.email, content)

    def test_user_list_brand_filter(self):
        """Test filtering users by brand"""
        self.client.force_login(self.auth_user)

        # Filter by brand A
        response = self.client.get(reverse('users'), {'brand': self.brand_a.id})
        content = response.content.decode()

        # user1 should be in results
        self.assertIn(self.user1.email, content)
        # user2 should not be in results
        self.assertNotIn(self.user2.email, content)

    def test_user_list_search(self):
        """Test searching users by name or email"""
        self.client.force_login(self.auth_user)

        # Search by first name
        response = self.client.get(reverse('users'), {'search': 'John'})
        content = response.content.decode()
        self.assertIn(self.user1.email, content)
        self.assertNotIn(self.user2.email, content)

        # Search by email
        response = self.client.get(reverse('users'), {'search': 'jane'})
        content = response.content.decode()
        self.assertIn(self.user2.email, content)
        self.assertNotIn(self.user1.email, content)

    def test_user_list_search_full_name(self):
        """Test searching users by full name (first and last name together)"""
        self.client.force_login(self.auth_user)

        # Search by full name "John Doe" - this should find user1 but currently doesn't
        response = self.client.get(reverse('users'), {'search': 'John Doe'})
        content = response.content.decode()
        self.assertIn(self.user1.email, content)
        self.assertNotIn(self.user2.email, content)

    def test_user_create_get_returns_form(self):
        """Test that GET to user-create returns the form modal"""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse('user-create'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('user-modal', content)
        self.assertIn('Nieuwe gebruiker', content)

    def test_user_create_success(self):
        """Test successful user creation"""
        self.client.force_login(self.auth_user)

        initial_count = User.objects.filter(is_superuser=False).count()

        response = self.client.post(reverse('user-create'), {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'brand': self.brand_a.id,
        })

        # Should redirect to users list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users'))

        # User should be created
        self.assertEqual(User.objects.filter(is_superuser=False).count(), initial_count + 1)

        # Verify user details
        new_user = User.objects.get(email='newuser@example.com')
        self.assertEqual(new_user.first_name, 'New')
        self.assertEqual(new_user.last_name, 'User')
        self.assertEqual(new_user.brand, self.brand_a)
        self.assertFalse(new_user.is_superuser)

    def test_user_create_without_brand(self):
        """Test user creation without brand (optional field)"""
        self.client.force_login(self.auth_user)

        response = self.client.post(reverse('user-create'), {
            'first_name': 'No',
            'last_name': 'Brand',
            'email': 'nobrand@example.com',
        })

        # Should redirect to users list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users'))

        new_user = User.objects.get(email='nobrand@example.com')
        self.assertIsNone(new_user.brand)

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
        self.assertIn('user-modal', content)

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
        self.assertEqual(response.url, reverse('users'))

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

        response = self.client.get(reverse('users'))
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

        response = self.client.get(reverse('users'))
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
        self.assertIn('user-modal', content)
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
            'brand': self.brand_b.id,
        })

        # Should redirect to users list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users'))

        # User should be updated
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'Updated')
        self.assertEqual(self.user1.last_name, 'Name')
        self.assertEqual(self.user1.email, 'updated@example.com')
        self.assertEqual(self.user1.brand, self.brand_b)

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
        self.assertIn('user-modal', content)
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
