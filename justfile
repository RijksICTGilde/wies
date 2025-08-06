export COMPOSE_FILE := "docker-compose.yml"

# Default command to list all available commands.
default:
  @just --list

# Setup image with fresh state
setup:
  echo "Setup application for local development: install dependencies, setup fresh db"
  uv sync  # to enable exploration in dependencies
  docker compose build
  docker compose run --rm django python manage.py dropdb --noinput
  docker compose run --rm django python manage.py migrate
  docker-compose run --rm django python manage.py createsuperuser --noinput
  docker compose run --rm django python manage.py loaddata dummy_data.json
  docker compose run --rm django python manage.py loaddata exact_dummy_data.json

# Start up container
up:
  docker compose up

# setup-production:
#  docker build . -t wies
#   # optionally: remove db-sqlite file

# up-production:
#   echo "Starting up container..."
# docker run --rm \
# --env DJANGO_SETTINGS_MODULE=config.settings.production \
# --env DJANGO_SECURE_SSL_REDIRECT=false \
# --env DJANGO_SUPERUSER_USERNAME=admin \
# --env DJANGO_SUPERUSER_PASSWORD=admin \
# --env DJANGO_SUPERUSER_EMAIL="" \
# --env DJANGO_SECRET_KEY=xxxxxxx \
# --env WRITABLE_FOLDER=/app/db \
# --env DJANGO_ALLOWED_HOSTS=localhost,0.0.0.0,127.0.0.1 \
# -p 8000:8000 \
# -v ./db:/app/db \
# wies

# Rebuild db
rebuild-db:
  echo "removing db, migrations and building up again from scratch"
  docker compose run --rm django python manage.py dropdb --noinput
  rm -r wies/projects/migrations/*
  touch wies/projects/migrations/__init__.py
  docker compose run --rm django python manage.py makemigrations

# Executes `manage.py` command.
manage *args="--help":
  docker compose run --rm django python manage.py {{args}}
