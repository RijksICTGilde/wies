import functools
import logging
from urllib.parse import urlencode

from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.contrib.auth import authenticate as auth_authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy

from .services.events import create_auth_event

logger = logging.getLogger(__name__)

OIDC_ID_TOKEN_SESSION_KEY = "oidc_id_token"  # noqa: S105 (hardcoded-password) — session key name, not a secret

POST_LOGOUT_COOKIE_NAME = "wies_post_logout"

oauth = OAuth()


@functools.cache
def _get_oidc():
    oauth.register(
        name="oidc",
        server_metadata_url=settings.OIDC_DISCOVERY_URL,
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
        client_kwargs={"scope": "openid profile email"},
    )
    return oauth.oidc


@login_not_required
def login(request):
    redirect_uri = request.build_absolute_uri(reverse_lazy("auth"))
    # If the user just logged out, force Keycloak to re-prompt for credentials.
    # The upstream SSO-Rijk broker chain dead-ends at BZK's terminal logout page,
    # so Keycloak's session stays alive after logout and would otherwise silently re-auth.
    kwargs = {}
    post_logout = request.COOKIES.get(POST_LOGOUT_COOKIE_NAME)
    if post_logout:
        kwargs["prompt"] = "login"
    response = _get_oidc().authorize_redirect(request, redirect_uri, **kwargs)
    if post_logout:
        response.delete_cookie(POST_LOGOUT_COOKIE_NAME, path="/")
    return response


@login_not_required
def auth(request):
    oidc_response = _get_oidc().authorize_access_token(request)
    userinfo = oidc_response["userinfo"]
    user = auth_authenticate(request, username=userinfo["sub"], email=userinfo["email"])
    if user:
        auth_login(request, user)
        # Keep the id_token so logout can end the upstream Keycloak/SSO session.
        request.session[OIDC_ID_TOKEN_SESSION_KEY] = oidc_response.get("id_token")
        logger.info("login successful, access granted")
        create_auth_event(user.email, "Login.success")
        return redirect(request.build_absolute_uri(reverse("home")))

    logger.info("login not successful, access denied")
    # Stash the id_token so the logout button on the no-access page can end
    # the upstream Keycloak session (otherwise Keycloak re-logs the same user).
    request.session[OIDC_ID_TOKEN_SESSION_KEY] = oidc_response.get("id_token")
    request.session["failed_login_email"] = userinfo["email"]
    return redirect(settings.AUTH_NO_ACCESS_URL)


@login_not_required
def logout(request):
    id_token = request.session.get(OIDC_ID_TOKEN_SESSION_KEY)
    if request.user and request.user.is_authenticated:
        auth_logout(request)

    end_session_url = _build_end_session_url(request, id_token)
    response = redirect(end_session_url) if end_session_url else redirect(reverse("login"))
    # Session cookie (max_age=None): persists until the browser is closed, matching
    # BZK's own "sluit je browser" guidance. Cleared explicitly on the next login.
    response.set_cookie(
        POST_LOGOUT_COOKIE_NAME,
        "1",
        max_age=None,
        path="/",
        httponly=True,
        samesite="Lax",
        secure=request.is_secure(),
    )
    return response


def _build_end_session_url(request, id_token: str | None) -> str | None:
    """Return the Keycloak end_session URL that also terminates SSO-Rijk, or None."""
    if not id_token:
        return None
    try:
        metadata = _get_oidc().load_server_metadata()
    except Exception:  # noqa: BLE001 - any discovery failure means local logout only
        logger.warning("OIDC discovery failed, skipping upstream logout", exc_info=True)
        return None
    end_session_endpoint = metadata.get("end_session_endpoint")
    if not end_session_endpoint:
        return None
    params = urlencode(
        {
            "id_token_hint": id_token,
            "post_logout_redirect_uri": request.build_absolute_uri(reverse("login")),
        }
    )
    return f"{end_session_endpoint}?{params}"
