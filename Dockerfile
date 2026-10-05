FROM ghcr.io/astral-sh/uv:0.8.0 AS uv
FROM docker.io/python:3.14-slim-trixie AS python


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# pip is unused (uv installs into /opt/venv)
RUN python -m pip uninstall --yes pip

#-----------------------------------------------------------------------------------------------------------------------
# Python build stage
#-----------------------------------------------------------------------------------------------------------------------
FROM python AS python-build

ENV UV_CACHE_DIR=/opt/uv-cache/
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV VIRTUAL_ENV=/opt/venv

# Production images exclude all dependency groups so dev/test tooling stays out
# of the runtime image. Local dev / in-container test runs pass INSTALL_DEV=true
# (see docker-compose.yml) to add the dev group.
ARG INSTALL_DEV=false
RUN --mount=from=uv,source=/uv,target=/bin/uv \
  --mount=type=cache,target=/opt/uv-cache/ \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  uv sync --active --frozen --no-default-groups \
    $([ "$INSTALL_DEV" = "true" ] && echo "--group dev")


#-----------------------------------------------------------------------------------------------------------------------
# Django run stage
#-----------------------------------------------------------------------------------------------------------------------
FROM python AS django-run

# Create app user; /app is created by WORKDIR as root
RUN groupadd --gid 1000 app \
  && useradd --gid app --uid 1000 --shell /bin/bash --home-dir /app app \
  && chown app:app /app

# copy results from build stages
COPY --from=python-build --chown=app:app /opt/venv /opt/venv

# Copy by name, most stable first, so a change in the app leaves the layers above it cached
COPY --chown=app:app manage.py docker-entrypoint.sh ./
COPY --chown=app:app config ./config
COPY --chown=app:app wies ./wies

# Run collectstatic against production settings so the manifest is
# baked into the image. Runtime env vars aren't set at build time, so
# pass harmless placeholders; the running container supplies the real
# values.
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY=build-time-placeholder \
    OIDC_CLIENT_ID=build-time-placeholder \
    OIDC_CLIENT_SECRET=build-time-placeholder \
    OIDC_DISCOVERY_URL=https://build-time-placeholder \
    python manage.py collectstatic --noinput

# Bake the CI-provided version (immutable image tag) into the image so the
# running app can report which build it is. Falls back to "onbekend" when
# not supplied.
ARG APP_VERSION=onbekend
ENV APP_VERSION=${APP_VERSION}

USER app


#-----------------------------------------------------------------------------------------------------------------------
# Web target — serves the Django application via Gunicorn
#-----------------------------------------------------------------------------------------------------------------------
FROM django-run AS web
CMD ["./docker-entrypoint.sh"]


#-----------------------------------------------------------------------------------------------------------------------
# Worker target — runs the background task processor
#-----------------------------------------------------------------------------------------------------------------------
FROM django-run AS worker
ENV DJANGO_SETTINGS_MODULE=config.settings.worker
CMD ["python", "manage.py", "db_worker"]
