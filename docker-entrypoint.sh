#!/usr/bin/env bash

echo "Waiting for database..."
python manage.py check --database default 2>/dev/null
while [ $? -ne 0 ]; do
  sleep 1
  python manage.py check --database default 2>/dev/null
done
echo "Database is ready."

python manage.py migrate
python manage.py setup
python manage.py createsuperuser --noinput
gunicorn -b 0.0.0.0:8000 config.wsgi
