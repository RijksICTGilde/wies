#!/usr/bin/env bash
set -e

echo "Waiting for database..."
until python manage.py check --database default 2>/dev/null; do
  sleep 1
done
echo "Database is ready."

python manage.py migrate
python manage.py setup
python manage.py createsuperuser --noinput
gunicorn -b 0.0.0.0:8000 -w 2 config.wsgi
