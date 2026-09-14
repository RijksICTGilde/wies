import logging
import os

from django.contrib.auth import get_user_model, login

logger = logging.getLogger(__name__)

User = get_user_model()


class AutoLoginMiddleware:
    """Auto-login as developer user for local development without VPN/SSO."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            dev_email = os.environ.get("INITIAL_USER_EMAIL", "")
            user = None
            if dev_email:
                user = User.objects.filter(email__iexact=dev_email).first()
            if not user:
                user = User.objects.first()
            if user:
                login(request, user, backend="wies.rijksauth.auth_backend.AuthBackend")
                logger.info("Auto-login: logged in as %s", user)
        return self.get_response(request)


STAFF_OVERRIDE_SESSION_KEY = "wies_staff_override"


class StaffOverrideMiddleware:
    """Carries the session's staff switch onto the user, where is_staff_member
    reads it. Local only; registered after the auto-login."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            user.wies_staff_override = request.session.get(STAFF_OVERRIDE_SESSION_KEY)
        return self.get_response(request)
