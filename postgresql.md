# Migrate from SQLite to PostgreSQL

## Context

The Wies application currently uses SQLite for all environments. PostgreSQL provides better concurrency (important with the background worker) and is the standard for production Django apps.

The codebase uses no raw SQL and no SQLite-specific features, so the migration is straightforward. Since you can't execute commands on the production server, the migration is split into two releases.

## Two-phase release strategy

### Release 1: Add data export button (deploy on current SQLite)

Add a "Download database dump" button to the existing admin_db page (`/djadmin/db/`). This runs `dumpdata` and returns a JSON file download. Deploy this on the current SQLite version so you can download the production data before switching databases.

### Release 2: Switch to PostgreSQL

Switch all settings, Docker, and CI to PostgreSQL. Add a "Load database dump" button to admin_db so you can upload the JSON file from Release 1 into the new PostgreSQL database.

---

## Release 1 — Data export button

### Files to modify

| File                             | Change                                                               |
| -------------------------------- | -------------------------------------------------------------------- |
| `wies/core/views.py`             | Add `dumpdata` action to `admin_db` view, returns JSON file download |
| `wies/core/jinja2/admin_db.html` | Add "Download database dump" button                                  |

### Implementation

In the `admin_db` view, add a new action `export_data` that:

- Calls `management.call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=output)`
- Returns an `HttpResponse` with `content_type="application/json"` and `Content-Disposition: attachment; filename="wies_datadump.json"`

Add a corresponding button on `admin_db.html`.

**Tag and deploy this release. Use the button to download the production data dump.**

---

## Release 2 — Switch to PostgreSQL

### Files to modify

| File                                      | Change                                                            |
| ----------------------------------------- | ----------------------------------------------------------------- |
| `pyproject.toml`                          | Add `psycopg[binary]` dependency                                  |
| `config/settings/base.py`                 | Switch to PostgreSQL, remove `WRITABLE_FOLDER`                    |
| `config/settings/test.py`                 | Remove SQLite override (use base PostgreSQL config)               |
| `docker-compose.yml`                      | Add `postgres:18` service, add `depends_on`                       |
| `Dockerfile`                              | Install `libpq5`, remove `/data/db_data` mkdir                    |
| `docker-entrypoint.sh`                    | Add wait-for-db before migrate                                    |
| `justfile`                                | Update `dropdb` usage, update production comments                 |
| `.env.local.example`                      | Replace `WRITABLE_FOLDER` with PostgreSQL vars                    |
| `.env.prod.example`                       | Replace `WRITABLE_FOLDER` with hosting provider's DB vars         |
| `.github/workflows/test.yml`              | Add PostgreSQL service container                                  |
| `wies/core/views.py`                      | Add `import_data` action to `admin_db` (file upload + `loaddata`) |
| `wies/core/jinja2/admin_db.html`          | Add "Upload database dump" form                                   |
| `wies/core/management/commands/dropdb.py` | Update for PostgreSQL (flush instead of file delete)              |
| `.env`                                    | Update with PostgreSQL vars (local dev, gitignored)               |

### Step-by-step

#### 1. Add `psycopg[binary]` to `pyproject.toml`

#### 2. Update `config/settings/base.py`

Use the hosting provider's env var names with local dev defaults:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DATABASE_DB", "wies"),
        "USER": os.environ.get("DATABASE_SERVER_USER", "wies"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", "wies"),
        "HOST": os.environ.get("DATABASE_SERVER_HOST", "localhost"),
        "PORT": os.environ.get("DATABASE_SERVER_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}
```

Remove `WRITABLE_FOLDER` (only used for SQLite path).

#### 3. Update `config/settings/test.py`

Remove the `DATABASES` override entirely. Django auto-creates a `test_wies` database for tests.

#### 4. Add PostgreSQL to `docker-compose.yml`

Add a `postgres` service using `postgres:18`, with a named volume. Add `depends_on: postgres` to `django` and `db_worker`.

#### 5. Update `Dockerfile`

In the `django-run` stage, add `libpq5` to the `apt-get install` line. Remove `mkdir -p /data/db_data`.

#### 6. Update `docker-entrypoint.sh`

Add a wait loop using Django's DB connection check before running migrate:

```bash
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
```

#### 7. Update `justfile`

- Update `rebuild-db` to use `manage.py flush --noinput` instead of `dropdb` + file deletion
- Update production run comments (remove `-v ./db:/app/db`)

#### 8. Update environment example files

**`.env.local.example`** — replace `WRITABLE_FOLDER` with:

```
DATABASE_SERVER_HOST=postgres
DATABASE_SERVER_PORT=5432
DATABASE_SERVER_USER=wies
DATABASE_PASSWORD=wies
DATABASE_DB=wies
```

**`.env.prod.example`** — same keys with placeholder values (matches hosting provider's standard names).

#### 9. Update CI workflow (`.github/workflows/test.yml`)

Add PostgreSQL 18 service container with health check to `test-django` job. Add DB env vars to the test step.

#### 10. Add data import to `admin_db`

Add a file upload form + `import_data` action that:

- Accepts the JSON dump file
- Saves to a temp file
- Calls `management.call_command("loaddata", temp_file_path)`
- Reports success/failure via messages

#### 11. Update `dropdb` management command

Replace the SQLite file-deletion logic with `management.call_command("flush", "--noinput")` or remove the command and use flush directly in the justfile.

---

## Production migration workflow

1. **Deploy Release 1** (still on SQLite) — tagged release with export button
2. **Go to `/djadmin/db/`** and click "Download database dump" — save the JSON file
3. **Deploy Release 2** (PostgreSQL) — the hosting provider provides the DB env vars
4. `docker-entrypoint.sh` runs `migrate` on the empty PostgreSQL database automatically
5. **Go to `/djadmin/db/`** and upload the JSON dump file via "Upload database dump"
6. Verify the application works with the migrated data

## Verification

1. `just setup` works and creates a fresh PostgreSQL database with dummy data
2. `just up` starts all services (postgres, django, worker)
3. `just test` passes against PostgreSQL
4. CI pipeline passes with PostgreSQL service container
5. Export button downloads valid JSON dump
6. Import button successfully loads a dump into a fresh database
