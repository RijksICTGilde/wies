from unittest.mock import patch

from django.conf import settings
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import User


@override_settings(
    # Use simple static files storage for tests
    # Because tests are not running with debug True, you would otherise need to run
    # collectstatic before running the test
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
    ALLOWED_EMAIL_DOMAINS=["@rijksoverheid.nl", "@minbzk.nl"],
)
class AuthViewsTest(TestCase):
    """Integration tests for authentication flow views"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.colleague = User.objects.create(
            username="test_sso_user",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

    @patch("wies.core.views.oauth.oidc.authorize_access_token")
    def test_auth_endpoint_success_whitelisted_user(self, mock_authorize):
        """Test successful SSO login for whitelisted Colleague"""
        # Mock OIDC response for whitelisted user
        mock_authorize.return_value = {
            "userinfo": {
                "sub": "test_sso_user",
                "given_name": "Test",
                "family_name": "User",
                "email": "test@example.com",
            }
        }

        response = self.client.get(reverse("auth"))

        # Should redirect to home
        assert response.status_code == 302
        assert response.url == f"http://testserver{reverse('home')}"

        # Should create session
        assert "_auth_user_id" in self.client.session

    @patch("wies.core.views.oauth.oidc.authorize_access_token")
    def test_auth_endpoint_failure_non_whitelisted_user(self, mock_authorize):
        """Test SSO login for non-whitelisted user redirects to no-access"""
        # Mock OIDC response for non-whitelisted user
        mock_authorize.return_value = {
            "userinfo": {
                "sub": "unknown_user",
                "given_name": "Unknown",
                "family_name": "Person",
                "email": "unknown@example.com",
            }
        }

        response = self.client.get(reverse("auth"))

        # Should redirect to no-access page
        assert response.status_code == 302
        assert response.url == "/geen-toegang/"

        # Should NOT create session
        assert "_auth_user_id" not in self.client.session

    @patch("wies.core.views.oauth.oidc.authorize_access_token")
    def test_auth_endpoint_session_creation(self, mock_authorize):
        """Test that successful auth creates proper session"""
        mock_authorize.return_value = {
            "userinfo": {
                "sub": "test_sso_user",
                "given_name": "Test",
                "family_name": "User",
                "email": "test@example.com",
            }
        }

        # Verify no session before auth
        assert "_auth_user_id" not in self.client.session

        self.client.get(reverse("auth"))

        # Verify session exists after auth
        assert "_auth_user_id" in self.client.session
        assert int(self.client.session["_auth_user_id"]) == self.colleague.pk

    def test_logout_clears_session(self):
        """Test that logout clears the session"""
        # Login the user first
        self.client.force_login(self.colleague)
        assert "_auth_user_id" in self.client.session

        # Logout
        response = self.client.get(reverse("logout"))

        # Should redirect to home/login
        assert response.status_code == 302
        assert response.url == "/inloggen/"

        # Session should be cleared (new session will be created but without user)
        # Accessing a protected page should now redirect to login
        protected_response = self.client.get(reverse("placements"))
        assert protected_response.status_code == 302
        assert protected_response.url.startswith("/inloggen/")

    def test_logout_when_not_logged_in(self):
        """Test logout works gracefully when user is not logged in"""
        response = self.client.get(reverse("logout"))

        # Should redirect to home without error (no login requirement)
        assert response.status_code == 302
        assert response.url == "/inloggen/"

    @patch("wies.core.views.oauth.oidc.authorize_redirect")
    def test_login_redirects_directly_to_keycloak(self, mock_authorize_redirect):
        """Test login directly redirects to Keycloak (no intermediate page)"""

        # Return a proper HttpResponse instead of MagicMock
        mock_authorize_redirect.return_value = HttpResponse(status=302)

        self.client.get(reverse("login"))

        # Should call OIDC authorization
        mock_authorize_redirect.assert_called_once()

        # Verify redirect_uri parameter includes auth callback
        call_args = mock_authorize_redirect.call_args
        redirect_uri = call_args[0][1]  # Second positional argument
        assert "/auth/" in redirect_uri

    @patch("wies.core.views.oauth.oidc.authorize_access_token")
    def test_failed_login_stores_email_in_session(self, mock_authorize):
        """Test that failed login stores email in session for no_access page"""
        mock_authorize.return_value = {
            "userinfo": {
                "sub": "unknown_user",
                "given_name": "Unknown",
                "family_name": "Person",
                "email": "unknown@external.com",
            }
        }

        self.client.get(reverse("auth"))

        # Email should be stored in session
        assert self.client.session.get("failed_login_email") == "unknown@external.com"

    def test_no_access_page_with_non_odi_email(self):
        """Test no_access page shows correct message for non-ODI email"""
        # Set up session with non-ODI email
        session = self.client.session
        session["failed_login_email"] = "user@external.com"
        session.save()

        response = self.client.get("/geen-toegang/")

        assert response.status_code == 200
        self.assertContains(response, "user@external.com")
        self.assertContains(response, "ODI / BZK e-mailadres")
        # Should show the "wrong account" scenario
        self.assertContains(response, "opdrachtgever")

    def test_no_access_page_with_odi_email(self):
        """Test no_access page shows correct message for ODI email without access"""
        # Set up session with ODI email
        session = self.client.session
        session["failed_login_email"] = "user@rijksoverheid.nl"
        session.save()

        response = self.client.get("/geen-toegang/")

        assert response.status_code == 200
        self.assertContains(response, "user@rijksoverheid.nl")
        # Should show the "request access" scenario
        self.assertContains(response, "nog geen toegang")
        self.assertContains(response, "wies-odi@rijksoverheid.nl")

    def test_no_access_page_clears_email_from_session(self):
        """Test that viewing no_access page clears email from session"""
        session = self.client.session
        session["failed_login_email"] = "user@external.com"
        session.save()

        self.client.get("/geen-toegang/")

        # Email should be cleared from session after viewing
        assert self.client.session.get("failed_login_email") is None

    def test_no_access_page_without_email(self):
        """Test no_access page works without email in session"""
        response = self.client.get("/geen-toegang/")

        assert response.status_code == 200
        # Should show generic message without specific email
        self.assertContains(response, "ODI / BZK e-mailadres")

    def test_allowed_email_domains_setting(self):
        """Test that ALLOWED_EMAIL_DOMAINS setting contains expected domains"""
        assert "@rijksoverheid.nl" in settings.ALLOWED_EMAIL_DOMAINS
        assert "@minbzk.nl" in settings.ALLOWED_EMAIL_DOMAINS
