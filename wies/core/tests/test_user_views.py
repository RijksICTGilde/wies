from django.test import TestCase, Client, override_settings
from django.urls import reverse

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
