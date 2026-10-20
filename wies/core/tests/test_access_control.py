from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.roles import ROLE_USER_ADMIN, setup_roles
from wies.core.tests.role_helpers import grant_business_manager
from wies.core.views import CURRENT_AUDIT_REPORT

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

    def test_audit_report_is_readable_without_login(self):
        """The one exception to the rule above: the DigiToegankelijk register links here.

        The report itself is a static file, so the view only redirects; what
        matters is that an anonymous visitor is sent to the report and not to login.
        """
        response = self.client.get(reverse("toegankelijkheid-onderzoek"), follow=False)

        assert response.status_code == 302
        assert response.url == static(CURRENT_AUDIT_REPORT)
        assert not response.url.startswith(reverse("login"))

    def test_audit_report_file_exists(self):
        """The redirect target must resolve, or the register's link 404s silently."""
        assert finders.find(CURRENT_AUDIT_REPORT) is not None, (
            f"{CURRENT_AUDIT_REPORT} is missing from the static files"
        )

    def test_accessibility_page_itself_still_requires_login(self):
        """Only the report is public; the page that links to it is not."""
        response = self.client.get(reverse("toegankelijkheid"), follow=False)

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
    def test_a_bdm_cannot_access_staff_page(self):
        """Business Manager is a functional role, not the Applicatiebeheerder."""
        self.client.force_login(grant_business_manager(self.test_user))

        for path in ("/beheer/statistieken/", "/beheer/database/"):
            with self.subTest(path=path):
                response = self.client.get(path, follow=False)

                assert response.status_code == 302
                assert response.url.startswith("/geen-toegang/")

    def test_beheer_menu_entries_follow_staff_emails_not_a_functional_role(self):
        """The Statistieken/Database entries in the Beheer menu show for application
        administration only, not for a user who holds both functional admin roles."""
        staff_dashboard = reverse("staff-dashboard")
        setup_roles()
        self.test_user.groups.add(Group.objects.get(name=ROLE_USER_ADMIN))
        grant_business_manager(self.test_user)
        self.client.force_login(self.test_user)
        for staff_emails, shown in (([], False), ([self.test_user.email], True)):
            with self.subTest(staff_emails=staff_emails), override_settings(STAFF_EMAILS=staff_emails):
                response = self.client.get(reverse("home"))

                assert response.status_code == 200
                assert (staff_dashboard in response.content.decode()) is shown
