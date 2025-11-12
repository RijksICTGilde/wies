import os
import logging

from .base import *  # noqa: F403


logger = logging.getLogger(__name__)


# GENERAL
# ----------------------------------------------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', "django-insecure-7Osdh5bY7SPLKDhMqeDjhtAwSoyJ7kGWwQ6XVAFC05P5UmQwqMl3F9emKQ37QPcu")
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]  # noqa: S104

# for authlib OIDC connection, if left out, login will not be enforced
OIDC_CLIENT_ID = os.environ.get('OIDC_CLIENT_ID', 'default-client-id')
OIDC_CLIENT_SECRET = os.environ.get('OIDC_CLIENT_SECRET', 'default-client-secret')
OIDC_DISCOVERY_URL = os.environ.get('OIDC_DISCOVERY_URL', 'https://test.example.com/.well-known/openid-configuration')

if (OIDC_CLIENT_ID == 'default-client-id' or
    OIDC_CLIENT_SECRET == 'default-client-secret' or
    OIDC_DISCOVERY_URL == 'https://test.example.com/.well-known/openid-configuration'):
    logger.warning('One of the OIDC envs is not set')
