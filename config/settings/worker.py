import os

from .base import *  # noqa: F403
from .base import DATABASES

# The worker (manage.py db_worker) is a background DB-task runner. It is NOT
# connected to inbound application traffic — its only HTTP listener is a raw
# health endpoint that bypasses Django — and it never performs OIDC login. So it
# inherits from base rather than production and deliberately omits all the
# inbound-HTTP machinery (ALLOWED_HOSTS, SSL redirect, secure cookies, HSTS,
# WhiteNoise/static) and, most importantly, the OIDC credentials that
# production.py requires at startup.

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# Worker polls the Task table every second; keep DB connections persistent.
DATABASES["default"]["CONN_MAX_AGE"] = 600
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

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
