import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import DATABASES

# GENERAL
# ----------------------------------------------------------------------------------------------------------------------
DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = (
    _allowed_hosts.split(",") if _allowed_hosts != "" else []
)  # otherwise list with single empty string entry

# SECURITY
# ----------------------------------------------------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# One trusted proxy hop: the ODCN-managed ingress.
TRUSTED_PROXY_HOPS = 1
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "true").lower() != "false"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "__Secure-sessionid"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_NAME = "__Secure-csrftoken"
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# STATIC FILES
# ----------------------------------------------------------------------------------------------------------------------
# Hash filenames + gzip. Requires `collectstatic` to have produced a manifest.
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# WhiteNoise serves static files. Insert it directly after SecurityMiddleware
# per the WhiteNoise docs — kept out of the base MIDDLEWARE list so
# tests/local don't need to filter it out.
# F405 (defined-from-star-import): MIDDLEWARE comes from `from .base import *`
# above; ruff can't see it. Safe to skip — this file is the only place
# where the star-imported names are mutated.
_WHITENOISE = "whitenoise.middleware.WhiteNoiseMiddleware"
_AFTER_SECURITY = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1  # noqa: F405
MIDDLEWARE.insert(_AFTER_SECURITY, _WHITENOISE)  # noqa: F405

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        # Persists unhandled 500s + background task failures as ErrorEvent rows
        # and posts a Mattermost notification. See wies/core/monitoring/.
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
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Unhandled request exceptions (500s). Django logs these at ERROR with
        # exc_info + the request attached; 404s/403s are below ERROR so they are
        # not captured.
        "django.request": {
            "handlers": ["console", "error_reporting"],
            "level": "ERROR",
            "propagate": False,
        },
        # App-level errors, including db_worker task failures.
        "wies": {
            "handlers": ["console", "error_reporting"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# DATABASE
# ----------------------------------------------------------------------------------------------------------------------
# Enable persistent connections in production (gunicorn workers, managed Postgres)
DATABASES["default"]["CONN_MAX_AGE"] = 600
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# for authlib OIDC connection
OIDC_CLIENT_ID = os.environ["OIDC_CLIENT_ID"]
OIDC_CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
OIDC_DISCOVERY_URL = os.environ["OIDC_DISCOVERY_URL"]
# Signature validation rests on the JWKS authlib fetches from this URL. Over http://
# (or a MITM-able endpoint) all OIDC validation is worthless, so fail fast at startup.
if not OIDC_DISCOVERY_URL.startswith("https://"):
    msg = "OIDC_DISCOVERY_URL must use https:// in production"
    raise ImproperlyConfigured(msg)
