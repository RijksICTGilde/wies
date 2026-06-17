from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class AccessControlTest(TestCase):
    """
    Test that endpoints require login or excluded ones dont.
    """

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.test_user = User.objects.create_user(
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )

    def test_endpoints_accessible_without_login(self):
        """Test that login-not-required endpoints are accessible without authentication and do not redirect to login"""

        login_not_required_paths = [
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
        response = self.client.get("/", follow=False)

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_staff_page_requires_authentication(self):
        """Test that staff subpages redirect unauthenticated users"""
        for path in ("/beheer/statistieken/", "/beheer/database/"):
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)

                assert response.status_code == 302

    @override_settings(STAFF_EMAILS=["admin@rijksoverheid.nl"])
    def test_staff_email_can_access_staff_page(self):
        """Test that a user whose email is in STAFF_EMAILS can access staff subpages"""
        staff_user = User.objects.create_user(
            email="admin@rijksoverheid.nl",
            first_name="Admin",
            last_name="User",
        )
        self.client.force_login(staff_user)

        for path in ("/beheer/statistieken/", "/beheer/database/"):
            with self.subTest(path=path):
                response = self.client.get(path)

                assert response.status_code == 200

    @override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"])
    def test_non_staff_email_cannot_access_staff_page(self):
        """Test that a user whose email is not in STAFF_EMAILS is redirected away from staff subpages"""
        self.client.force_login(self.test_user)

        for path in ("/beheer/statistieken/", "/beheer/database/"):
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)

                assert response.status_code == 302
                assert response.url.startswith("/geen-toegang/")
