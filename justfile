export COMPOSE_FILE := "docker-compose.yml"

# Vendor package versies
HTMX_VERSION := "2.0.6"
RVO_DESIGN_TOKENS_VERSION := "1.11.0"
RVO_COMPONENT_LIBRARY_VERSION := "4.11.1"

# Default command to list all available commands.
default:
  @just --list

# Setup image with fresh state
setup:
  echo "Setup application for local development: install dependencies, setup fresh db"
  uv sync  # to enable exploration in dependencies
  npm ci  # for enable exploration in static assets
  cp overwrite_index.css node_modules/@nl-rvo/assets/index.css  # mimick build
  if [ ! -f .env ]; then cp .env.local.example .env; fi
  docker compose down -v
  docker compose build
  docker compose run --rm django python manage.py migrate
  docker compose run --rm django python manage.py setup
  docker compose run --rm django python manage.py loaddata base_dummy_data
  docker compose run --rm django python manage.py assign_random_labels_to_colleagues
  docker compose run --rm django python manage.py createsuperuser --noinput
  docker compose run --rm django python manage.py add_developer_user

# Generate full dummy data: sync organizations + create dummy colleagues/assignments/placements
load-full-data:
  docker compose run --rm django python manage.py load_full_data

# Start up container
up:
  docker compose up

# Stop and remove containers
down:
  docker compose down

up-jrc:
  docker compose run -v /Users/$USER/jinja-roos-components:/app/jinja-roos-components --service-ports django sh -c "uv pip install -e ./jinja-roos-components && python manage.py runserver 0.0.0.0:8000"

setup-production:
  docker build --target web -t wies .
  docker build --target worker -t wies-worker .
  docker network create wies-network 2>/dev/null || true

# to check if container runs properly. not directly used in production
up-production-postgres:
  docker run --rm --env-file .env -p 5432:5432 --network wies-network --name postgres postgres:17

# make sure to run up-production-postgres first
# to check if container runs properly. not directly used in production
up-production-django:
  docker run --rm  --env-file .env -e DJANGO_SETTINGS_MODULE=config.settings.local -p 8000:8000 --network wies-network wies

# make sure to run up-production-postgres first
# to check if container runs properly. not directly used in production
up-production-worker:
  docker run --rm --env-file .env --network wies-network wies-worker

# Rebuild db
rebuild-db:
  echo "removing db, migrations and building up again from scratch"
  docker compose run --rm django python manage.py dropdb --noinput
  rm -r wies/core/migrations/*
  touch wies/core/migrations/__init__.py
  docker compose run --rm django python manage.py makemigrations

# Executes `manage.py` command.
manage *args="--help":
  docker compose run --rm django python manage.py {{args}}

# Run tests. Usage: just test, just test django, just test js
test target="all":
  #!/usr/bin/env sh
  if [ "{{target}}" = "django" ] || [ "{{target}}" = "all" ]; then
    just test-django
  fi
  if [ "{{target}}" = "js" ] || [ "{{target}}" = "all" ]; then
    just test-js
  fi

# Run Django tests
test-django:
  docker compose run --rm django uv run pytest

# Run JavaScript tests
test-js:
  node --test "js_tests/**/*.test.js"

# Run linting checks
lint:
  uv run ruff check .
  uv run ruff format --check .

# Auto-fix linting issues and format code
format:
  uv run ruff check --fix .
  uv run ruff format .

# Run all pre-commit hooks
pre-commit:
  uv run pre-commit run --all-files

# Install pre-commit hooks
pre-commit-install:
  uv run pre-commit install

# Download vendor packages (externe dependencies lokaal)
update-vendor:
  @echo "Downloading vendor packages..."
  @mkdir -p wies/core/static/vendor/htmx
  @mkdir -p wies/core/static/vendor/rvo
  curl -sL "https://unpkg.com/htmx.org@{{HTMX_VERSION}}/dist/htmx.min.js" \
    -o wies/core/static/vendor/htmx/htmx.min.js
  curl -sL "https://cdn.jsdelivr.net/npm/@nl-rvo/design-tokens@{{RVO_DESIGN_TOKENS_VERSION}}/dist/index.css" \
    -o wies/core/static/vendor/rvo/design-tokens.css
  curl -sL "https://cdn.jsdelivr.net/npm/@nl-rvo/component-library-css@{{RVO_COMPONENT_LIBRARY_VERSION}}/dist/index.css" \
    -o wies/core/static/vendor/rvo/component-library.css
  @echo "Done! Vendor packages updated:"
  @echo "  - htmx.min.js ({{HTMX_VERSION}})"
  @echo "  - design-tokens.css ({{RVO_DESIGN_TOKENS_VERSION}})"
  @echo "  - component-library.css ({{RVO_COMPONENT_LIBRARY_VERSION}})"
