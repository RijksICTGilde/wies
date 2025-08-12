import os

from .base import *  # noqa: F403

# GENERAL
# ----------------------------------------------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', "django-insecure-7Osdh5bY7SPLKDhMqeDjhtAwSoyJ7kGWwQ6XVAFC05P5UmQwqMl3F9emKQ37QPcu")
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]  # noqa: S104

# for authlib OIDC connection
OIDC_CLIENT_ID = os.environ.get('OIDC_CLIENT_ID', '')
OIDC_CLIENT_SECRET = os.environ.get('OIDC_CLIENT_SECRET', '')
OIDC_DISCOVERY_URL = os.environ.get('OIDC_DISCOVERY_URL', '')
