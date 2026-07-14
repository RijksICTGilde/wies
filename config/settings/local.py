import logging
import os

from .base import *  # noqa: F403

logger = logging.getLogger(__name__)


# GENERAL
# ----------------------------------------------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-7Osdh5bY7SPLKDhMqeDjhtAwSoyJ7kGWwQ6XVAFC05P5UmQwqMl3F9emKQ37QPcu"
)
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]  # noqa: S104

# for authlib OIDC connection, if left out, login will not be enforced
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "default-client-id")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "default-client-secret")
OIDC_DISCOVERY_URL = os.environ.get("OIDC_DISCOVERY_URL", "https://test.example.com/.well-known/openid-configuration")

if (
    OIDC_CLIENT_ID == "default-client-id"
    or OIDC_CLIENT_SECRET == "default-client-secret"  # noqa: S105
    or OIDC_DISCOVERY_URL == "https://test.example.com/.well-known/openid-configuration"
):
    logger.warning("One of the OIDC envs is not set")

# Auto-login: skip OIDC when SSO is unreachable (e.g. no VPN)
# uses DEV_EMAIL user if defined, otherwise first super admin
SKIP_OIDC = os.environ.get("SKIP_OIDC", "false").lower() == "true"
if SKIP_OIDC:
    MIDDLEWARE = [m for m in MIDDLEWARE if m != "django.contrib.auth.middleware.LoginRequiredMiddleware"]  # noqa: F405
    MIDDLEWARE.append("wies.rijksauth.middleware.AutoLoginMiddleware")

# ERROR MONITORING
# ----------------------------------------------------------------------------------------------------------------------
# Mirror production so the error handler can be exercised locally. Leaving these
# empty (the default) means ErrorEvent rows are still written and shown on
# /beheer/statistieken/, but nothing is posted to Mattermost.
MATTERMOST_TOKEN = os.environ.get("MATTERMOST_TOKEN", "")
MATTERMOST_WIES_OPS_CHANNEL_URL = os.environ.get("MATTERMOST_WIES_OPS_CHANNEL_URL", "")
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "http://localhost:8080").rstrip("/")

# LOGGING
# ----------------------------------------------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        # Persists unhandled 500s + task failures as ErrorEvent rows (and posts to
        # Mattermost only if MATTERMOST_* are set). Mirrors production so the
        # feature is testable in dev.
        "error_reporting": {
            "class": "wies.core.monitoring.ErrorReportingHandler",
            "level": "ERROR",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Unhandled request exceptions (500s) — Django logs these at ERROR.
        "django.request": {
            "handlers": ["console", "error_reporting"],
            "level": "ERROR",
            "propagate": False,
        },
        "wies": {
            "handlers": ["console", "error_reporting"],
            "level": "INFO",
            "propagate": False,
        },
        "wies.core.services.organizations": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
