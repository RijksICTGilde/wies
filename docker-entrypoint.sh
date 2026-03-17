#!/usr/bin/env bash
set -e

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
# do not exist if superuser already exists
python manage.py createsuperuser --noinput || true
python manage.py ensure_initial_user
gunicorn -b 0.0.0.0:8000 -w 3 --no-control-socket config.wsgi
