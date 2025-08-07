import os

from .base import *  # noqa: F403

# GENERAL
# ----------------------------------------------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', "django-insecure-7Osdh5bY7SPLKDhMqeDjhtAwSoyJ7kGWwQ6XVAFC05P5UmQwqMl3F9emKQ37QPcu")
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]  # noqa: S104
