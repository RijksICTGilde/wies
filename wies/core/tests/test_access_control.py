from django.conf import settings
from django.test import Client, TestCase, override_settings

from wies.core.models import User


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
        self.test_user = User.objects.create(
            username="test_user",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

    def test_endpoints_accessible_without_login(self):
        """Test that login-not-required endpoints are accessible without authentication and do not redirect to login"""

        login_not_required_paths = [
            "/djadmin/login/",
            "/geen-toegang/",
            # Endpoints where login is not required but which are tested separately
            # '/auth/',    # /auth/ requires OIDC state and will raise an error without it. This path is tested in
            #                test_auth_views.py with proper mocking.
            # '/logout/',  # /logout/ redirects to login. Tested in test_auth_view.
        ]

        for path in login_not_required_paths:
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)
                assert response.status_code == 200, f"{path} returned unexpected status {response.status_code}"

    def test_unauthenticated_access_to_placements_redirects_to_login(self):
        """Specific test for placements view (main landing page)"""
        response = self.client.get("/plaatsingen/", follow=False)

        assert response.status_code == 302
        assert response.url.startswith(settings.LOGIN_URL)

    def test_admin_views_require_authentication(self):
        """Test that admin views require authentication"""
        admin_paths = [
            "/djadmin/",
            "/djadmin/db/",
        ]

        for path in admin_paths:
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)

                assert response.status_code == 302
                assert response.url.startswith("/djadmin/login/")

    def test_superuser_can_access_admin_db(self):
        """Test that superuser can access /djadmin/db/ view"""
        superuser = User.objects.create(
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(superuser)

        response = self.client.get("/djadmin/db/")

        assert response.status_code == 200

    def test_non_superuser_cannot_access_admin_db(self):
        """Test that non-superuser cannot access /djadmin/db/ view"""
        self.client.force_login(self.test_user)

        response = self.client.get("/djadmin/db/", follow=False)

        # Should redirect (either to admin login or show access denied)
        assert response.status_code == 302
