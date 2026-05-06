FROM ghcr.io/astral-sh/uv:0.8.0 AS uv
FROM docker.io/python:3.14-slim-trixie AS python


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

#-----------------------------------------------------------------------------------------------------------------------
# Python build stage
#-----------------------------------------------------------------------------------------------------------------------
FROM python AS python-build

ENV UV_CACHE_DIR=/opt/uv-cache/
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV VIRTUAL_ENV=/opt/venv

# Install git to enable installation of jrc from github
# can be removed when jrc is on pypi
RUN apt-get update && apt-get install --no-install-recommends --assume-yes \
  git \
  # Cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

COPY --from=jrc . /jinja-roos-components
RUN --mount=from=uv,source=/uv,target=/bin/uv \
  --mount=type=cache,target=/opt/uv-cache/ \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  uv sync --active --frozen


#-----------------------------------------------------------------------------------------------------------------------
# Django run stage
#-----------------------------------------------------------------------------------------------------------------------
FROM python AS django-run

# Create app user
RUN groupadd --gid 1000 app \
  && useradd --gid app --uid 1000 --shell /bin/bash --home-dir /app app

# Install (required) system dependencies
RUN apt-get update && apt-get install --no-install-recommends --assume-yes \
  # Devcontainer dependencies and utils
  sudo git bash-completion vim \
  # Cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# copy results from build stages
COPY --from=python-build --chown=app:app /opt/venv /opt/venv
COPY --from=python-build --chown=app:app /jinja-roos-components /jinja-roos-components

# copy uv to enable runtime including editable package during development
COPY --from=uv /uv /bin/uv

COPY --chown=app:app . /app
RUN chown -R app:app /app
RUN rm -rf /app/docker && \
  rm -rf /app/.dockerignore && \
  rm -rf /app/pyproject.toml && \
  rm -rf /app/uv.lock && \
  rm -rf /app/temp

RUN python manage.py collectstatic

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
CMD ["python", "manage.py", "db_worker"]
