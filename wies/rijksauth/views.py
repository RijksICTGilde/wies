import functools
import logging
from urllib.parse import urlencode

from authlib.integrations.base_client import OAuthError
from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.contrib.auth import authenticate as auth_authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from .services.events import create_auth_event

logger = logging.getLogger(__name__)

# Marks that the callback already failed once, so the automatic restart of the
# flow cannot turn into a redirect loop.
OIDC_AUTH_RETRY_SESSION_KEY = "oidc_auth_retried"

# Callback errors that belong to a normal login attempt: the authentication
# session at Keycloak is gone, or the user backed out. Nothing to fix on our
# side, so they are logged at WARNING and handled in the flow. Everything else
# (invalid_client, unauthorized_client, server_error, ...) points at our client
# registration or at Keycloak itself and is logged at ERROR, which reaches
# ErrorReportingHandler and Mattermost.
OIDC_EXPECTED_CALLBACK_ERRORS = frozenset(
    {
        "temporarily_unavailable",
        "invalid_request",
        "mismatching_state",
        "access_denied",
        "login_required",
        "interaction_required",
        "consent_required",
    }
)

oauth = OAuth()


@functools.cache
def _get_oidc():
    oauth.register(
        name="oidc",
        server_metadata_url=settings.OIDC_DISCOVERY_URL,
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
        # OIDC-NLGov requires PKCE with S256 for every client, public or
        # confidential (sections 4.1 and 4.2.1):
        # https://gitdocumentatie.logius.nl/publicatie/api/oidc/
        client_kwargs={"scope": "openid profile email", "code_challenge_method": "S256"},
    )
    return oauth.oidc


@login_not_required
def login(request):
    redirect_uri = request.build_absolute_uri(reverse_lazy("auth"))
    # If the user just logged out, force Keycloak to re-prompt for credentials.
    # The upstream SSO-Rijk broker chain dead-ends at BZK's terminal logout page,
    # so Keycloak's session stays alive after logout and would otherwise silently re-auth.
    kwargs = {}
    if request.COOKIES.get(settings.OIDC_POST_LOGOUT_COOKIE_NAME):
        kwargs["prompt"] = "login"
    return _get_oidc().authorize_redirect(request, redirect_uri, **kwargs)


@login_not_required
def auth(request):
    try:
        oidc_response = _get_oidc().authorize_access_token(request)
    except OAuthError as exc:
        return _handle_callback_error(request, exc)

    request.session.pop(OIDC_AUTH_RETRY_SESSION_KEY, None)
    userinfo = oidc_response["userinfo"]
    user = auth_authenticate(
        request,
        username=userinfo["sub"],
        email=userinfo["email"],
        email_verified=userinfo.get("email_verified", False),
    )
    if user:
        auth_login(request, user)
        # Keep the id_token so logout can end the upstream Keycloak/SSO session.
        request.session[settings.OIDC_ID_TOKEN_SESSION_KEY] = oidc_response.get("id_token")
        logger.info("login successful, access granted")
        create_auth_event(user.email, "Login.success", request=request)
        response = redirect(request.build_absolute_uri(reverse("home")))
    else:
        logger.info("login not successful, access denied")
        # Stash the id_token so the logout button on the no-access page can end
        # the upstream Keycloak session (otherwise Keycloak re-logs the same user).
        request.session[settings.OIDC_ID_TOKEN_SESSION_KEY] = oidc_response.get("id_token")
        request.session["failed_login_email"] = userinfo["email"]
        response = redirect(settings.AUTH_NO_ACCESS_URL)

    # Clear the post-logout cookie only after the upstream auth round-trip completes,
    # so abandoning the Keycloak flow (e.g. opening another tab) doesn't silently
    # re-enable silent SSO on the next login attempt.
    if request.COOKIES.get(settings.OIDC_POST_LOGOUT_COOKIE_NAME):
        response.delete_cookie(settings.OIDC_POST_LOGOUT_COOKIE_NAME, path="/")
    return response


def _handle_callback_error(request, exc: OAuthError):
    """Recover from an error redirect on the OIDC callback instead of raising a 500.

    Keycloak sends `?error=...` to the redirect URI instead of a code when its
    authentication session is no longer resolvable. That happens when the user
    sits on the login page past its timeout (`temporarily_unavailable:
    authentication_expired`), and when a link on that page rebuilds the
    authorize URL from only client_id and tab_id, which drops response_type and
    the rest of the OIDC parameters (`invalid_request: Missing parameter:
    response_type`). Keycloak's locale switcher does exactly that:
    https://github.com/keycloak/keycloak/issues/16063
    """
    # Parameter names only, never their values, which carry tokens. Whether
    # `state` is among them separates an expired authentication session (Keycloak
    # restores the client context from its KC_RESTART cookie) from a request that
    # arrived without any OIDC parameters at all.
    log_args = (
        exc.error,
        exc.description,
        sorted(request.GET.keys()),
        request.headers.get("Referer", ""),
    )
    already_retried = request.session.get(OIDC_AUTH_RETRY_SESSION_KEY, False)
    request.session.pop(OIDC_AUTH_RETRY_SESSION_KEY, None)

    if exc.error not in OIDC_EXPECTED_CALLBACK_ERRORS:
        logger.error(
            "OIDC callback failed with %s (%s), query params: %s, referer: %s",
            *log_args,
            exc_info=exc,
            extra={"request": request},
        )
        # Nobody can log in until this is fixed, so do not pretend a retry helps.
        return render(request, "login_error.html", {"recoverable": False}, status=400)

    logger.warning("OIDC callback error %s (%s), query params: %s, referer: %s", *log_args)

    # access_denied means the user or the upstream IdP refused, so sending them
    # straight back into the flow would override a deliberate choice.
    if already_retried or exc.error == "access_denied":
        return render(request, "login_error.html", {"recoverable": True}, status=400)

    # The login view redirects straight to Keycloak, so restarting the flow costs
    # the user nothing but a fresh login page. Retry once, then show the page above.
    request.session[OIDC_AUTH_RETRY_SESSION_KEY] = True
    return redirect(reverse("login"))


@login_not_required
@require_POST
def logout(request):
    id_token = request.session.get(settings.OIDC_ID_TOKEN_SESSION_KEY)
    if request.user and request.user.is_authenticated:
        # Capture the email before auth_logout flushes the session and turns
        # request.user into AnonymousUser. IP/User-Agent stay on the request.
        user_email = request.user.email
        auth_logout(request)
        create_auth_event(user_email, "Logout", request=request)

    end_session_url = _build_end_session_url(request, id_token)
    response = redirect(end_session_url) if end_session_url else redirect(reverse("login"))
    # Session cookie (max_age=None): persists until the browser is closed, matching
    # BZK's own "sluit je browser" guidance. Cleared after the next completed auth round-trip.
    response.set_cookie(
        settings.OIDC_POST_LOGOUT_COOKIE_NAME,
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
