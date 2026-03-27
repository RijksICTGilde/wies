import logging

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

oauth = OAuth()
_oidc_registered = False


def _get_oidc():
    global _oidc_registered  # noqa: PLW0603 — lazy singleton registration for OIDC client
    if not _oidc_registered:
        oauth.register(
            name="oidc",
            server_metadata_url=settings.OIDC_DISCOVERY_URL,
            client_id=settings.OIDC_CLIENT_ID,
            client_secret=settings.OIDC_CLIENT_SECRET,
            client_kwargs={"scope": "openid profile email"},
        )
        _oidc_registered = True
    return oauth.oidc


@login_not_required
def login(request):
    """Redirect directly to Keycloak for authentication"""
    redirect_uri = request.build_absolute_uri(reverse_lazy("auth"))
    return _get_oidc().authorize_redirect(request, redirect_uri)


@login_not_required
def auth(request):
    oidc_response = _get_oidc().authorize_access_token(request)
    userinfo = oidc_response["userinfo"]
    user = auth_authenticate(request, username=userinfo["sub"], email=userinfo["email"])
    if user:
        auth_login(request, user)
        logger.info("login successful, access granted")
        try:
            create_auth_event(user.email, "Login.success")
        except Exception:
            logger.exception("Failed to log auth event")
        return redirect(request.build_absolute_uri(reverse("home")))

    logger.info("login not successful, access denied")
    request.session["failed_login_email"] = userinfo["email"]
    return redirect(settings.AUTH_NO_ACCESS_URL)


@login_not_required
def logout(request):
    if request.user and request.user.is_authenticated:
        auth_logout(request)
    return redirect(reverse("login"))
