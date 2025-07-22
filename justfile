export COMPOSE_FILE := "docker-compose.yml"

# Default command to list all available commands.
default:
  @just --list

# Setup container with fresh state
setup:
  echo "Setup application: drop db, install dependencies"
  rm -f db.sqlite3
  docker compose build
  docker compose run --rm django python manage.py migrate
  docker compose run --rm django python manage.py loaddata dummy_data.json

# Start up containers with current state.
up:
  echo "Starting up container..."
  docker compose run --rm django python manage.py migrate
  docker compose up --remove-orphans

# Rebuild db
rebuild-db:
  echo "removing db, migrations and building up again from scratch"
  rm -f db.sqlite3
  rm -r wies/projects/migrations/*
  touch wies/projects/migrations/__init__.py
  docker compose run --rm django python manage.py makemigrations

# Executes `manage.py` command.
manage *args="--help":
  docker compose run --rm django python manage.py {{args}}
