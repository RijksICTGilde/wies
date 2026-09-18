from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.roles import USER_ADMIN_GROUP_NAME, setup_roles
from wies.core.tests.role_helpers import grant_assignment_admin

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

    def test_security_txt_redirects_to_ncsc_without_login(self):
        """security.txt must reach the NCSC redirect for anonymous scanners, not bounce to SSO login"""
        response = self.client.get("/.well-known/security.txt", follow=False)

        assert response.status_code == 302
        assert response.url == "https://www.ncsc.nl/.well-known/security.txt"

    def test_unauthenticated_access_to_placements_redirects_to_login(self):
        """Specific test for placements view (main landing page)"""
        response = self.client.get("/", follow=False)

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_faq_and_contact_require_authentication(self):
        """FAQ and contact pages are only visible after login; anonymous users bounce to login"""
        for path in ("/faq/", "/contact/"):
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)

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

    @override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"])
    def test_assignment_admin_cannot_access_staff_page(self):
        """Opdrachtbeheer is a functional role, not platform administration."""
        self.client.force_login(grant_assignment_admin(self.test_user))

        for path in ("/beheer/statistieken/", "/beheer/database/"):
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)

                assert response.status_code == 302
                assert response.url.startswith("/geen-toegang/")

    def test_platform_menu_entries_follow_staff_emails_not_assignment_admin(self):
        """The Statistieken/Database entries in the Beheer menu show for platform
        administration only, not for a user who holds both functional admin roles."""
        staff_dashboard = reverse("staff-dashboard")
        setup_roles()
        self.test_user.groups.add(Group.objects.get(name=USER_ADMIN_GROUP_NAME))
        grant_assignment_admin(self.test_user)
        self.client.force_login(self.test_user)
        for staff_emails, shown in (([], False), ([self.test_user.email], True)):
            with self.subTest(staff_emails=staff_emails), override_settings(STAFF_EMAILS=staff_emails):
                response = self.client.get(reverse("home"))

                assert response.status_code == 200
                assert (staff_dashboard in response.content.decode()) is shown
