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
            dev_email = os.environ.get("DEV_EMAIL", "")
            user = None
            if dev_email:
                user = User.objects.filter(email=dev_email).first()
            if not user:
                user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if user:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                logger.info("Auto-login: logged in as %s", user)
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers not covered by Django's SecurityMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Using geolocation, microphone or camera is completely blocked
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content-Security-Policy
        #
        # Current implementation uses 'unsafe-inline' for scripts and styles.
        # This is a pragmatic choice that still provides protection against loading
        # resources from untrusted external domains.
        #
        # TODO: Refactor to strict nonce-based CSP which requires:
        # - Moving inline event handlers (onclick/onsubmit) to external JS files
        # - Moving inline style attributes to CSS classes
        # - Adding nonce attributes to all <script> and <style> tags
        # - Generating unique nonce per request in this middleware
        #
        # See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        return response
