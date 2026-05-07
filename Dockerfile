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
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers

# Install git to enable installation of jrc from github
# can be removed when jrc is on pypi
RUN apt-get update && apt-get install --no-install-recommends --assume-yes \
  git \
  # Cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

RUN --mount=from=uv,source=/uv,target=/bin/uv \
  --mount=type=cache,target=/opt/uv-cache/ \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  uv sync --active --frozen \
  && /opt/venv/bin/playwright install chromium


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
  # Chromium runtime libs for Playwright (Debian trixie names; t64 = 64-bit time_t transition)
  libglib2.0-0t64 libnss3 libnspr4 libdbus-1-3 \
  libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libasound2t64 libatspi2.0-0t64 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
  libgbm1 libpango-1.0-0 libcairo2 libx11-6 libxcb1 libxext6 fonts-liberation \
  # Cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# copy results from build stages
COPY --from=python-build --chown=app:app /opt/venv /opt/venv
COPY --from=python-build --chown=app:app /opt/playwright-browsers /opt/playwright-browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
ENV VIRTUAL_ENV=/opt/venv

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
