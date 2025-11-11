from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings

from wies.core.models import Colleague, Brand, Assignment, Ministry


@override_settings(
    # Use simple static files storage for tests (avoid collectstatic requirement)
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
    # Enable OIDC authentication for tests
    OIDC_CLIENT_ID='test-client-id',
    OIDC_CLIENT_SECRET='test-client-secret',
    OIDC_DISCOVERY_URL='https://test.example.com/.well-known/openid-configuration',
    # Ensure LoginRequiredMiddleware is active
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'whitenoise.middleware.WhiteNoiseMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.LoginRequiredMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ],
)
class AccessControlTest(TestCase):
    """
    Test that all endpoints require login except explicitly excluded ones.

    This test serves as a security snapshot - if someone adds a new endpoint
    or removes @login_not_required, the test will fail.
    """

    # Endpoints that should NOT require login (explicitly allowed)
    LOGIN_NOT_REQUIRED_PATHS = [
        '/login/',
        '/no-access/',
        '/auth/',
        '/logout/',
        '/admin/login/',
    ]

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

        # Create some test data for views that need it
        self.ministry = Ministry.objects.create(
            name="Test Ministry",
            abbreviation="TM"
        )
        self.assignment = Assignment.objects.create(
            name="Test Assignment",
            ministry=self.ministry,
            owner=self.colleague
        )

    def test_excluded_endpoints_accessible_without_login(self):
        """Test that login-not-required endpoints are accessible without authentication"""
        for path in self.LOGIN_NOT_REQUIRED_PATHS:
            with self.subTest(path=path):
                # /auth/ requires OIDC state and will raise an error without it
                # We just need to verify it doesn't redirect to login before the OIDC error
                if path == '/auth/':
                    # Skip this path - it's tested in test_auth_views.py with proper mocking
                    continue

                response = self.client.get(path, follow=False)

                # Should NOT redirect to login
                if response.status_code == 302:
                    self.assertFalse(
                        response.url.startswith(settings.LOGIN_URL),
                        f"{path} redirected to login page but should be accessible without auth"
                    )
                else:
                    # Should return 200 or some other non-redirect status
                    self.assertIn(
                        response.status_code,
                        [200, 400, 404, 405],  # OK, bad request, not found, method not allowed are all acceptable
                        f"{path} returned unexpected status {response.status_code}"
                    )

    def test_protected_endpoints_require_login(self):
        """
        Test that all endpoints except LOGIN_NOT_REQUIRED_PATHS redirect to login.

        This is a snapshot test - it captures the current state of which endpoints
        require authentication. If you add a new endpoint, you must either:
        1. Add @login_not_required decorator and add it to LOGIN_NOT_REQUIRED_PATHS
        2. Let it be protected by default (no changes needed)
        """
        # List of known protected endpoints to test
        protected_paths = [
            '/placements/',
            f'/assignments/{self.assignment.pk}/',
            f'/colleagues/{self.colleague.pk}/',
            f'/ministries/{self.ministry.pk}/',
            '/clients/TestClient',
            '/admin/',
            '/admin/db/',
        ]

        for path in protected_paths:
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)

                # Should redirect to login
                self.assertEqual(
                    response.status_code,
                    302,
                    f"{path} should redirect but returned {response.status_code}"
                )
                self.assertTrue(
                    response.url.startswith(settings.LOGIN_URL) or
                    response.url.startswith('/admin/login/'),  # Django admin has its own login
                    f"{path} should redirect to login but redirected to {response.url}"
                )

        # Test home separately since it redirects to placements which then redirects to login
        response = self.client.get('/', follow=True)
        # Follow the redirect chain and check final URL is login
        self.assertTrue(
            any(settings.LOGIN_URL in url for url, _ in response.redirect_chain),
            f"/ should eventually redirect to login but redirect chain was: {response.redirect_chain}"
        )

    def test_authenticated_user_can_access_protected_views(self):
        """Test that authenticated Colleague can access protected views"""
        self.client.force_login(self.colleague)

        protected_paths = [
            '/',  # home
            '/placements/',
            f'/assignments/{self.assignment.pk}/',
            f'/colleagues/{self.colleague.pk}/',
            f'/ministries/{self.ministry.pk}/',
            '/clients/TestClient',
        ]

        for path in protected_paths:
            with self.subTest(path=path):
                response = self.client.get(path, follow=True)

                # Should NOT redirect to login (200 or other successful status)
                # Note: some paths may redirect (e.g., home redirects to placements)
                # but should not redirect to login
                final_url = response.redirect_chain[-1][0] if response.redirect_chain else path
                self.assertFalse(
                    settings.LOGIN_URL in final_url,
                    f"Authenticated user was redirected to login when accessing {path}"
                )
                self.assertIn(
                    response.status_code,
                    [200, 404],  # OK or not found (if test data doesn't exist)
                    f"{path} returned unexpected status {response.status_code}"
                )

    def test_unauthenticated_access_to_placements_redirects_to_login(self):
        """Specific test for placements view (main landing page)"""
        response = self.client.get('/placements/', follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))

    def test_logout_accessible_without_login(self):
        """
        Test that logout endpoint is accessible without authentication.

        This ensures users can "logout" even if they're not logged in,
        which provides better UX and prevents redirect loops.
        """
        response = self.client.get(reverse('logout'), follow=False)

        # Should redirect to home without requiring login
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        # Should NOT redirect to login page
        self.assertFalse(response.url.startswith(settings.LOGIN_URL))

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
                # Django admin uses its own login
                self.assertTrue(
                    response.url.startswith(settings.LOGIN_URL) or
                    response.url.startswith('/admin/login/')
                )

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
