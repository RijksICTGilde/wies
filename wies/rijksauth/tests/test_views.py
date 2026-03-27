from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class AuthViewsTest(TestCase):
    """Integration tests for authentication flow views"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.colleague = User.objects.create_user(
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )

    @patch("wies.rijksauth.views._get_oidc")
    def test_auth_endpoint_success_whitelisted_user(self, mock_get_oidc):
        """Test successful SSO login for whitelisted Colleague"""
        mock_get_oidc.return_value.authorize_access_token.return_value = {
            "userinfo": {
                "sub": "test_sso_user",
                "given_name": "Test",
                "family_name": "User",
                "email": "test@rijksoverheid.nl",
            }
        }

        response = self.client.get(reverse("auth"))

        # Should redirect to home
        assert response.status_code == 302
        assert response.url == f"http://testserver{reverse('home')}"

        # Should create session
        assert "_auth_user_id" in self.client.session

    @patch("wies.rijksauth.views._get_oidc")
    def test_auth_endpoint_failure_non_whitelisted_user(self, mock_get_oidc):
        """Test SSO login for non-whitelisted user redirects to no-access"""
        mock_get_oidc.return_value.authorize_access_token.return_value = {
            "userinfo": {
                "sub": "unknown_user",
                "given_name": "Unknown",
                "family_name": "Person",
                "email": "unknown@rijksoverheid.nl",
            }
        }

        response = self.client.get(reverse("auth"))

        # Should redirect to no-access page
        assert response.status_code == 302
        assert response.url == "/geen-toegang/"

        # Should NOT create session
        assert "_auth_user_id" not in self.client.session

    @patch("wies.rijksauth.views._get_oidc")
    def test_auth_endpoint_session_creation(self, mock_get_oidc):
        """Test that successful auth creates proper session"""
        mock_get_oidc.return_value.authorize_access_token.return_value = {
            "userinfo": {
                "sub": "test_sso_user",
                "given_name": "Test",
                "family_name": "User",
                "email": "test@rijksoverheid.nl",
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
        protected_response = self.client.get(reverse("home"))
        assert protected_response.status_code == 302
        assert protected_response.url.startswith("/inloggen/")

    def test_logout_when_not_logged_in(self):
        """Test logout works gracefully when user is not logged in"""
        response = self.client.get(reverse("logout"))

        # Should redirect to home without error (no login requirement)
        assert response.status_code == 302
        assert response.url == "/inloggen/"

    @patch("wies.rijksauth.views._get_oidc")
    def test_login_redirects_directly_to_keycloak(self, mock_get_oidc):
        """Test login directly redirects to Keycloak (no intermediate page)"""
        mock_get_oidc.return_value.authorize_redirect.return_value = HttpResponse(status=302)

        self.client.get(reverse("login"))

        # Should call OIDC authorization
        mock_get_oidc.return_value.authorize_redirect.assert_called_once()

        # Verify redirect_uri parameter includes auth callback
        call_args = mock_get_oidc.return_value.authorize_redirect.call_args
        redirect_uri = call_args[0][1]  # Second positional argument
        assert "/auth/" in redirect_uri

    @patch("wies.rijksauth.views._get_oidc")
    def test_failed_login_stores_email_in_session(self, mock_get_oidc):
        """Test that failed login stores email in session for no_access page"""
        mock_get_oidc.return_value.authorize_access_token.return_value = {
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
