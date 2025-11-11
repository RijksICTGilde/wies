from django.test import TestCase, Client, override_settings
from django.conf import settings

from wies.core.models import Colleague, Brand


@override_settings(
    # Use simple static files storage for tests
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class AccessControlTest(TestCase):
    """
    Test that endpoints require login or excluded ones dont.
    """    

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.brand = Brand.objects.create(name="Test Brand")
        self.colleague = Colleague.objects.create(
            username="test_user",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            brand=self.brand
        )

    def test_endpoints_accessible_without_login(self):
        """Test that login-not-required endpoints are accessible without authentication and do not redirect to login"""

        LOGIN_NOT_REQUIRED_PATHS = [
            '/login/',
            '/admin/login/',
            '/no-access/',
            # '/auth/',  # /auth/ requires OIDC state and will raise an error without it. this path is tested in test_auth_views.py with proper mocking
            # '/logout/',  # logout redirects to login. tested in test_auth_view in detail
        ]

        for path in LOGIN_NOT_REQUIRED_PATHS:
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)
                self.assertEqual(response.status_code, 200, f"{path} returned unexpected status {response.status_code}")

    def test_unauthenticated_access_to_placements_redirects_to_login(self):
        """Specific test for placements view (main landing page)"""
        response = self.client.get('/placements/', follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))

    def test_admin_views_require_authentication(self):
        """Test that admin views require authentication"""
        admin_paths = [
            '/admin/',
            '/admin/db/',
        ]

        for path in admin_paths:
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)

                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith('/admin/login/'))

    def test_superuser_can_access_admin_db(self):
        """Test that superuser can access /admin/db/ view"""
        superuser = Colleague.objects.create(
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            brand=self.brand,
            is_superuser=True,
            is_staff=True
        )
        self.client.force_login(superuser)

        response = self.client.get('/admin/db/')

        self.assertEqual(response.status_code, 200)

    def test_non_superuser_cannot_access_admin_db(self):
        """Test that non-superuser cannot access /admin/db/ view"""
        self.client.force_login(self.colleague)

        response = self.client.get('/admin/db/', follow=False)

        # Should redirect (either to admin login or show access denied)
        self.assertEqual(response.status_code, 302)
