"""
Test settings for running pytest.

Key differences from local:
- DEBUG = False (like production)
- Faster password hasher
- In-memory SQLite database
- No OIDC warnings
"""

from .base import *  # noqa: F403

# GENERAL
# ----------------------------------------------------------------------------------------------------------------------
DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105
ALLOWED_HOSTS = ["localhost", "testserver"]

# Disable OIDC for tests
OIDC_CLIENT_ID = None
OIDC_CLIENT_SECRET = None
OIDC_DISCOVERY_URL = None

# PASSWORDS
# ----------------------------------------------------------------------------------------------------------------------
# Use fast password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# DATABASE
# ----------------------------------------------------------------------------------------------------------------------
# Use in-memory SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# CACHES
# ----------------------------------------------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

# EMAIL
# ----------------------------------------------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# STATIC FILES
# ----------------------------------------------------------------------------------------------------------------------
# Disable WhiteNoise middleware and storage to avoid warnings about missing staticfiles directory
MIDDLEWARE = [m for m in MIDDLEWARE if m != "whitenoise.middleware.WhiteNoiseMiddleware"]  # noqa: F405
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# LOGGING
# ----------------------------------------------------------------------------------------------------------------------
# Reduce logging noise during tests
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
        "level": "WARNING",
    },
}
