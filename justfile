export COMPOSE_FILE := "docker-compose.yml"

# Default command to list all available commands.
default:
  @just --list

# Setup container with fresh state
setup:
  docker compose build
  echo "Setup application: drop db, install dependencies"
  docker compose run --rm django python manage.py dropdb --noinput
  docker compose run --rm django python manage.py migrate
  docker compose run --rm django python manage.py loaddata dummy_data.json
  docker-compose run --rm django python manage.py createsuperuser --noinput

# Start up containers with current state.
up:
  echo "Starting up container..."
  docker compose run --rm django python manage.py migrate
  docker compose up --remove-orphans

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
