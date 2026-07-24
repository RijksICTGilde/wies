from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from authlib.oauth2.rfc7636 import create_s256_code_challenge
from django.test import TestCase
from django.urls import reverse

from wies.rijksauth import views

SERVER_METADATA = {
    "issuer": "https://keycloak.example/realms/wies",
    "authorization_endpoint": "https://keycloak.example/realms/wies/protocol/openid-connect/auth",
}


class OidcPkceTests(TestCase):
    """OIDC-NLGov requires PKCE with S256 for every client, public or confidential
    (sections 4.1 and 4.2.1)."""

    def test_login_redirect_uses_pkce_s256(self):
        oidc = views._get_oidc()  # noqa: SLF001 (private member access) - the registered client has no public accessor
        with patch.object(oidc, "load_server_metadata", return_value=SERVER_METADATA):
            response = self.client.get(reverse("login"))

        assert response.status_code == 302
        params = parse_qs(urlparse(response["Location"]).query)
        assert params["code_challenge_method"] == ["S256"]
        assert params["code_challenge"][0]

    def test_login_stores_a_code_verifier_matching_the_challenge(self):
        """Without the verifier surviving in the session, /auth cannot complete the exchange."""
        oidc = views._get_oidc()  # noqa: SLF001 (private member access) - the registered client has no public accessor
        with patch.object(oidc, "load_server_metadata", return_value=SERVER_METADATA):
            response = self.client.get(reverse("login"))

        params = parse_qs(urlparse(response["Location"]).query)
        state_data = self.client.session[f"_state_oidc_{params['state'][0]}"]["data"]
        assert create_s256_code_challenge(state_data["code_verifier"]) == params["code_challenge"][0]
