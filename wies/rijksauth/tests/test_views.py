from unittest.mock import patch

from authlib.integrations.base_client import MismatchingStateError, OAuthError
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse

from wies.rijksauth.models import AuthEvent
from wies.rijksauth.views import OIDC_AUTH_RETRY_SESSION_KEY

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
                "email_verified": True,
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
                "email_verified": True,
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

        response = self.client.post(reverse("logout"))

        assert response.status_code == 302
        assert response.url == "/inloggen/"
        # Post-logout cookie is set even on the local fallback path.
        assert response.cookies["wies_post_logout"].value == "1"

        # Session should be cleared
        protected_response = self.client.get(reverse("home"))
        assert protected_response.status_code == 302
        assert protected_response.url.startswith("/inloggen/")

    def test_logout_logs_auth_event(self):
        """A logged-in user logging out records a Logout AuthEvent with their email."""
        self.client.force_login(self.colleague)

        self.client.post(reverse("logout"))

        events = AuthEvent.objects.filter(name="Logout")
        assert events.count() == 1
        assert events.first().user_email == self.colleague.email

    def test_logout_when_not_logged_in(self):
        """Test logout works gracefully when user is not logged in"""
        response = self.client.post(reverse("logout"))

        assert response.status_code == 302
        assert response.url == "/inloggen/"
        # No user was logged in, so nothing to log.
        assert not AuthEvent.objects.filter(name="Logout").exists()

    def test_logout_rejects_get(self):
        """Logout must be POST-only: a GET (e.g. a cross-site <img src> pointing
        at the logout URL) must not be able to log the user out."""
        self.client.force_login(self.colleague)

        response = self.client.get(reverse("logout"))

        assert response.status_code == 405
        # A rejected GET must not log the user out, so no Logout event either.
        assert not AuthEvent.objects.filter(name="Logout").exists()

    @patch("wies.rijksauth.views._get_oidc")
    def test_logout_redirects_to_keycloak_end_session(self, mock_get_oidc):
        """With an id_token stored, logout redirects to Keycloak's end_session endpoint."""
        mock_get_oidc.return_value.load_server_metadata.return_value = {
            "end_session_endpoint": "https://kc.example/realms/wies/protocol/openid-connect/logout",
        }
        self.client.force_login(self.colleague)
        session = self.client.session
        session["oidc_id_token"] = "fake-id-token"  # noqa: S105 (hardcoded-password) - test fixture, not a real token
        session.save()

        response = self.client.post(reverse("logout"))

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
        """With the post-logout cookie set, login passes prompt=login and keeps the cookie."""
        mock_get_oidc.return_value.authorize_redirect.return_value = HttpResponse(status=302)
        self.client.cookies["wies_post_logout"] = "1"

        response = self.client.get(reverse("login"))

        call_args = mock_get_oidc.return_value.authorize_redirect.call_args
        assert call_args.kwargs.get("prompt") == "login"
        # Cookie is NOT cleared on the login redirect, only after the full auth
        # round-trip completes, so abandoning the Keycloak flow doesn't silently
        # re-enable silent SSO on the next attempt.
        assert "wies_post_logout" not in response.cookies

    @patch("wies.rijksauth.views._get_oidc")
    def test_auth_clears_post_logout_cookie_on_success(self, mock_get_oidc):
        """After a successful auth round-trip, the post-logout cookie is cleared."""
        mock_get_oidc.return_value.authorize_access_token.return_value = {
            "id_token": "fake-id-token",
            "userinfo": {
                "sub": "test_sso_user",
                "given_name": "Test",
                "family_name": "User",
                "email": "test@rijksoverheid.nl",
                "email_verified": True,
            },
        }
        self.client.cookies["wies_post_logout"] = "1"

        response = self.client.get(reverse("auth"))

        assert response.cookies["wies_post_logout"].value == ""
        assert response.cookies["wies_post_logout"]["max-age"] == 0

    @patch("wies.rijksauth.views._get_oidc")
    def test_auth_clears_post_logout_cookie_on_no_access(self, mock_get_oidc):
        """After auth completes for a non-whitelisted user, the cookie is still cleared."""
        mock_get_oidc.return_value.authorize_access_token.return_value = {
            "id_token": "fake-id-token",
            "userinfo": {
                "sub": "unknown_user",
                "given_name": "Unknown",
                "family_name": "Person",
                "email": "unknown@rijksoverheid.nl",
            },
        }
        self.client.cookies["wies_post_logout"] = "1"

        response = self.client.get(reverse("auth"))

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


class OidcCallbackErrorTest(TestCase):
    """Keycloak redirects `?error=...` to the callback when its authentication session
    is gone. That must restart the login flow, not surface as a 500."""

    def setUp(self):
        self.client = Client()

    @staticmethod
    def _fail_with(mock_get_oidc, error, description=""):
        mock_get_oidc.return_value.authorize_access_token.side_effect = OAuthError(
            error=error,
            description=description,
        )

    @patch("wies.rijksauth.views._get_oidc")
    def test_expired_authentication_session_restarts_flow(self, mock_get_oidc):
        """The user sat on the Keycloak login page past its timeout."""
        self._fail_with(mock_get_oidc, "temporarily_unavailable", "authentication_expired")

        response = self.client.get(reverse("auth"))

        assert response.status_code == 302
        assert response.url == reverse("login")
        assert self.client.session[OIDC_AUTH_RETRY_SESSION_KEY] is True

    @patch("wies.rijksauth.views._get_oidc")
    def test_missing_response_type_restarts_flow(self, mock_get_oidc):
        """A login-page link re-entered the authorize endpoint without response_type."""
        self._fail_with(mock_get_oidc, "invalid_request", "Missing parameter: response_type")

        response = self.client.get(reverse("auth"))

        assert response.status_code == 302
        assert response.url == reverse("login")

    @patch("wies.rijksauth.views._get_oidc")
    def test_mismatching_state_restarts_flow(self, mock_get_oidc):
        """A state gone from the session (blocked cookies, stale tab) is recoverable too."""
        mock_get_oidc.return_value.authorize_access_token.side_effect = MismatchingStateError()

        response = self.client.get(reverse("auth"))

        assert response.status_code == 302
        assert response.url == reverse("login")

    @patch("wies.rijksauth.views._get_oidc")
    def test_second_consecutive_failure_shows_error_page(self, mock_get_oidc):
        """login redirects straight back to Keycloak, so retrying forever would loop."""
        self._fail_with(mock_get_oidc, "temporarily_unavailable", "authentication_expired")

        self.client.get(reverse("auth"))
        response = self.client.get(reverse("auth"))

        assert response.status_code == 400
        assert "Inloggen is niet gelukt" in response.content.decode()
        # Marker is cleared, so a later attempt gets its one retry again.
        assert OIDC_AUTH_RETRY_SESSION_KEY not in self.client.session

    @patch("wies.rijksauth.views._get_oidc")
    def test_access_denied_is_not_retried(self, mock_get_oidc):
        """The user or the upstream IdP refused, so do not send them back in."""
        self._fail_with(mock_get_oidc, "access_denied", "user cancelled")

        response = self.client.get(reverse("auth"))

        assert response.status_code == 400
        assert OIDC_AUTH_RETRY_SESSION_KEY not in self.client.session

    @patch("wies.rijksauth.views._get_oidc")
    def test_successful_login_clears_retry_marker(self, mock_get_oidc):
        User.objects.create_user(email="test@rijksoverheid.nl", first_name="Test", last_name="User")
        self._fail_with(mock_get_oidc, "temporarily_unavailable", "authentication_expired")
        self.client.get(reverse("auth"))
        assert self.client.session[OIDC_AUTH_RETRY_SESSION_KEY] is True

        mock_get_oidc.return_value.authorize_access_token.side_effect = None
        mock_get_oidc.return_value.authorize_access_token.return_value = {
            "id_token": "fake-id-token",
            "userinfo": {
                "sub": "test_sso_user",
                "email": "test@rijksoverheid.nl",
                "email_verified": True,
            },
        }

        response = self.client.get(reverse("auth"))

        assert response.url == f"http://testserver{reverse('home')}"
        assert OIDC_AUTH_RETRY_SESSION_KEY not in self.client.session

    @patch("wies.rijksauth.views._get_oidc")
    def test_callback_error_logs_parameter_names_but_not_values(self, mock_get_oidc):
        """Which parameters arrived is the diagnostic signal; their values carry tokens."""
        self._fail_with(mock_get_oidc, "invalid_request", "Missing parameter: response_type")

        with self.assertLogs("wies.rijksauth.views", level="WARNING") as logs:
            self.client.get(reverse("auth"), {"error": "invalid_request", "state": "secret-state-value"})

        [message] = logs.output
        assert "invalid_request" in message
        assert "'state'" in message
        assert "secret-state-value" not in message

    @patch("wies.rijksauth.views._get_oidc")
    def test_expected_errors_stay_below_error_level(self, mock_get_oidc):
        """WARNING keeps flow noise out of ErrorReportingHandler, which fires on ERROR."""
        self._fail_with(mock_get_oidc, "temporarily_unavailable", "authentication_expired")

        with self.assertLogs("wies.rijksauth.views", level="WARNING") as logs:
            self.client.get(reverse("auth"))

        assert [record.levelname for record in logs.records] == ["WARNING"]

    @patch("wies.rijksauth.views._get_oidc")
    def test_unexpected_error_is_logged_at_error_level(self, mock_get_oidc):
        """A broken client registration must reach the error reporting handler."""
        self._fail_with(mock_get_oidc, "invalid_client", "Invalid client credentials")

        with self.assertLogs("wies.rijksauth.views", level="ERROR") as logs:
            response = self.client.get(reverse("auth"))

        [record] = logs.records
        assert record.levelname == "ERROR"
        assert record.exc_info is not None
        assert record.request.path == reverse("auth")
        assert response.status_code == 400

    @patch("wies.rijksauth.views._get_oidc")
    def test_unexpected_error_is_not_retried(self, mock_get_oidc):
        """Restarting the flow cannot fix a misconfiguration, so do not suggest it."""
        self._fail_with(mock_get_oidc, "server_error", "upstream exploded")

        with self.assertLogs("wies.rijksauth.views", level="ERROR"):
            response = self.client.get(reverse("auth"))

        assert response.status_code == 400
        assert OIDC_AUTH_RETRY_SESSION_KEY not in self.client.session
        body = response.content.decode()
        assert "Er is een storing in de koppeling met de inlogdienst" in body
        assert "inlogsessie is verlopen" not in body
        # Never a dead end: the user can always start the flow again themselves.
        assert "Probeer het inloggen opnieuw" in body

    @patch("wies.rijksauth.views._get_oidc")
    def test_failure_without_an_oauth_error_code_also_gets_the_explanation_page(self, mock_get_oidc):
        """The token exchange can break on the network, on JWT validation or on a bug of
        ours. Those carry no OAuth error code and must not reach the user as a bare 500."""
        mock_get_oidc.return_value.authorize_access_token.side_effect = ValueError("boom")

        with self.assertLogs("wies.rijksauth.views", level="ERROR") as logs:
            response = self.client.get(reverse("auth"))

        assert response.status_code == 400
        assert "Er is een storing in de koppeling met de inlogdienst" in response.content.decode()
        assert OIDC_AUTH_RETRY_SESSION_KEY not in self.client.session
        # Recovering for the user must not hide the bug: still reported, with its traceback.
        [record] = logs.records
        assert record.exc_info is not None
        assert record.request.path == reverse("auth")
        assert "ValueError" in record.getMessage()
