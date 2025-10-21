FROM ghcr.io/astral-sh/uv:0.8.0 AS uv
FROM docker.io/python:3.13-slim-bookworm AS python


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

# Install (required) system dependencies
RUN apt-get update && apt-get install --no-install-recommends --assume-yes \
  # Devcontainer dependencies and utils
  git \
  # Cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

RUN --mount=from=uv,source=/uv,target=/bin/uv \
  --mount=type=cache,target=/opt/uv-cache/ \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  uv sync --active --frozen


#-----------------------------------------------------------------------------------------------------------------------
# JavaScript build stage
#-----------------------------------------------------------------------------------------------------------------------
FROM python AS js-build

RUN apt-get update && apt-get install --no-install-recommends --assume-yes \
  curl \
  && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
  && apt-get install --no-install-recommends --assume-yes nodejs \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.npm \
  --mount=type=bind,source=package.json,target=package.json \
  --mount=type=bind,source=package-lock.json,target=package-lock.json \
  npm ci


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
COPY --from=js-build --chown=app:app /app/node_modules /app/node_modules

# copy uv to enable runtime including editable package
COPY --from=uv /uv /bin/uv

COPY --chown=app:app . /app
RUN chown -R app:app /app
RUN rm -rf /app/docker && \
  rm -rf /app/.dockerignore && \
  rm -rf /app/pyproject.toml && \
  rm -rf /app/uv.lock && \
  rm -rf /app/package.json && \
  rm -rf /app/package-lock.json && \
  rm -rf /app/temp

# patch original faulty index.css
RUN mv overwrite_index.css node_modules/@nl-rvo/assets/index.css

RUN mkdir -p /data/db_data && chown -R app:app /data

RUN python manage.py collectstatic

USER app

CMD ["./docker-entrypoint.sh"]
