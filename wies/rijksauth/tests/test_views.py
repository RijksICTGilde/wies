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
            "id_token": "fake-id-token",
            "userinfo": {
                "sub": "test_sso_user",
                "given_name": "Test",
                "family_name": "User",
                "email": "test@rijksoverheid.nl",
            },
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
            "id_token": "fake-id-token",
            "userinfo": {
                "sub": "unknown_user",
                "given_name": "Unknown",
                "family_name": "Person",
                "email": "unknown@rijksoverheid.nl",
            },
        }

        response = self.client.get(reverse("auth"))

        # Should redirect to no-access page
        assert response.status_code == 302
        assert response.url == "/geen-toegang/"

        # Should NOT create session
        assert "_auth_user_id" not in self.client.session

        # Should stash the id_token so the no-access logout button can end Keycloak's session
        assert self.client.session.get("oidc_id_token") == "fake-id-token"

    @patch("wies.rijksauth.views._get_oidc")
    def test_auth_endpoint_session_creation(self, mock_get_oidc):
        """Test that successful auth creates proper session"""
        mock_get_oidc.return_value.authorize_access_token.return_value = {
            "id_token": "fake-id-token",
            "userinfo": {
                "sub": "test_sso_user",
                "given_name": "Test",
                "family_name": "User",
                "email": "test@rijksoverheid.nl",
            },
        }

        # Verify no session before auth
        assert "_auth_user_id" not in self.client.session

        self.client.get(reverse("auth"))

        # Verify session exists after auth
        assert "_auth_user_id" in self.client.session
        assert int(self.client.session["_auth_user_id"]) == self.colleague.pk

    def test_logout_clears_session(self):
        """Without an id_token in the session, logout falls back to the local login page."""
        self.client.force_login(self.colleague)
        assert "_auth_user_id" in self.client.session

        response = self.client.get(reverse("logout"))

        assert response.status_code == 302
        assert response.url == "/inloggen/"
        # Post-logout cookie is set even on the local fallback path.
        assert response.cookies["wies_post_logout"].value == "1"

        # Session should be cleared
        protected_response = self.client.get(reverse("home"))
        assert protected_response.status_code == 302
        assert protected_response.url.startswith("/inloggen/")

    def test_logout_when_not_logged_in(self):
        """Test logout works gracefully when user is not logged in"""
        response = self.client.get(reverse("logout"))

        assert response.status_code == 302
        assert response.url == "/inloggen/"

    @patch("wies.rijksauth.views._get_oidc")
    def test_logout_redirects_to_keycloak_end_session(self, mock_get_oidc):
        """With an id_token stored, logout redirects to Keycloak's end_session endpoint."""
        mock_get_oidc.return_value.load_server_metadata.return_value = {
            "end_session_endpoint": "https://kc.example/realms/wies/protocol/openid-connect/logout",
        }
        self.client.force_login(self.colleague)
        session = self.client.session
        session["oidc_id_token"] = "fake-id-token"  # noqa: S105 (hardcoded-password) — test fixture, not a real token
        session.save()

        response = self.client.get(reverse("logout"))

        assert response.status_code == 302
        assert response.url.startswith("https://kc.example/realms/wies/protocol/openid-connect/logout?")
        assert "id_token_hint=fake-id-token" in response.url
        assert "post_logout_redirect_uri=" in response.url
        assert "%2Finloggen%2F" in response.url
        # Local session is cleared
        assert "_auth_user_id" not in self.client.session
        # Post-logout cookie is set so the next login forces credential re-entry.
        assert response.cookies["wies_post_logout"].value == "1"
        assert response.cookies["wies_post_logout"]["samesite"] == "Lax"

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

        # Without the post-logout cookie, silent SSO is preserved.
        assert "prompt" not in call_args.kwargs

    @patch("wies.rijksauth.views._get_oidc")
    def test_login_after_logout_forces_reauth(self, mock_get_oidc):
        """With the post-logout cookie set, login passes prompt=login and clears the cookie."""
        mock_get_oidc.return_value.authorize_redirect.return_value = HttpResponse(status=302)
        self.client.cookies["wies_post_logout"] = "1"

        response = self.client.get(reverse("login"))

        call_args = mock_get_oidc.return_value.authorize_redirect.call_args
        assert call_args.kwargs.get("prompt") == "login"
        # Cookie is cleared on the response (Set-Cookie with empty value + expired date).
        assert response.cookies["wies_post_logout"].value == ""
        assert response.cookies["wies_post_logout"]["max-age"] == 0

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
