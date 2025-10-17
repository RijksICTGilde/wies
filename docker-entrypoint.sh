#!/usr/bin/env bash

echo "foo"
python manage.py migrate
python manage.py setup
gunicorn -b 0.0.0.0:8000 config.wsgi
