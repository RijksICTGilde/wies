#!/usr/bin/env bash
set -e

# Default to production settings so a container started without an explicit
# DJANGO_SETTINGS_MODULE cannot fall back to the local/dev settings (DEBUG on,
# insecure dev SECRET_KEY, default DB password). The web image already bakes
# this in via ENV; this is a second layer. Local dev is unaffected: compose
# builds the dev target, which runs runserver and never invokes this entrypoint.
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

echo "Waiting for database..."
MAX_RETRIES=30
RETRY_COUNT=0

# make sure it exists early if DJANGO_SETTINGS_MODULE is not set
python -c "
import django, os
django.setup()"

until python -c "
from django.db import connection
connection.ensure_connection()
" 2>/dev/null; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: Database not available after ${MAX_RETRIES}s, exiting."
    exit 1
  fi
  sleep 1
done
echo "Database is ready."

python manage.py migrate
python manage.py setup
python manage.py ensure_initial_user
gunicorn -b 0.0.0.0:8000 -w 3 --no-control-socket config.wsgi
