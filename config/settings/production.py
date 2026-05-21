import os

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
