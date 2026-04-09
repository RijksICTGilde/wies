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
                user = User.objects.filter(email=dev_email).first()
            if not user:
                user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if user:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                logger.info("Auto-login: logged in as %s", user)
        return self.get_response(request)
