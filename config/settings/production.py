import os

from .base import *  # noqa: F403

# GENERAL
# ----------------------------------------------------------------------------------------------------------------------
DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", '')
ALLOWED_HOSTS =_allowed_hosts.split(',') if _allowed_hosts != "" else []  # otherwise list with single empty string entry

# SECURITY
# ----------------------------------------------------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "true") != 'false'  # if true somehow misspelled, fallback to ssl
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "__Secure-sessionid"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_NAME = "__Secure-csrftoken"
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# helpful when understanding internal errors with debug=False
LOGGING = {
      'version': 1,
      'disable_existing_loggers': False,
      'handlers': {
          'console': {
              'class': 'logging.StreamHandler',
          },
      },
      'root': {
          'handlers': ['console'],
          'level': 'INFO',
      },
      'loggers': {
          'django': {
              'handlers': ['console'],
              'level': 'INFO',
              'propagate': False,
          },
      },
  }