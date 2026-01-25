# Wies

Internal tool for managing colleague placements within the Dutch government. Wies provides an overview of who is working where, on what, and when.

## Tech Stack

- **Backend**: Django 6 with SQLite
- **Templates**: Jinja2 with [jinja-roos-components](https://github.com/RijksICTGilde/jinja-roos-components)
- **Styling**: [RVO Design System](https://github.com/nl-design-system/rvo) (Dutch government design system)
- **Interactivity**: HTMX
- **Authentication**: OIDC via Keycloak
- **Package management**: uv

## Prerequisites

- [Docker](https://www.docker.com/)
- [just](https://github.com/casey/just)
- [uv](https://docs.astral.sh/uv/)
- [npm](https://www.npmjs.com/)
- [pre-commit](https://pre-commit.com/)

## Quick Start

### Setup

Installs dependencies, sets up database with dummy data, creates `.env`:

```bash
just setup
```

Then update `.env`:

- Fill in OIDC credentials
- Set DEV firstname, lastname and email (yourself)

### Start

```bash
just up
```

## Development

### Project Structure

```
wies/
├── core/
│   ├── models.py      # All models
│   ├── views.py       # View functions
│   ├── forms.py       # Django forms with RVOMixin
│   ├── urls.py        # URL routing
│   ├── roles.py       # Roles and permissions
│   ├── querysets.py   # Custom querysets
│   └── jinja2/        # Jinja2 templates
│       └── parts/     # Reusable template partials
├── config/
│   └── settings/      # Django settings per environment
└── dummy_data.json    # Test data for development
```

### Commands

```bash
just setup          # Set up fresh environment
just up             # Start application
just down           # Stop containers
just test           # Run tests
just manage [...]   # Django manage.py commands
just update-vendor  # Update vendor assets (htmx, RVO CSS)
```

### Vendor Assets

This project vendors external JavaScript and CSS dependencies instead of using a CDN. This ensures the application works without external network dependencies and improves security (no CDN in CSP).

**Vendored packages:**

- [htmx](https://htmx.org/) - JavaScript library for AJAX/HTML
- [@nl-rvo/design-tokens](https://www.npmjs.com/package/@nl-rvo/design-tokens) - RVO design tokens
- [@nl-rvo/component-library-css](https://www.npmjs.com/package/@nl-rvo/component-library-css) - RVO component styles

#### Update vendor dependencies

To update vendor dependencies:

1. Edit the version numbers in `justfile`:

   ```
   HTMX_VERSION := "2.0.6"
   RVO_DESIGN_TOKENS_VERSION := "1.11.0"
   RVO_COMPONENT_LIBRARY_VERSION := "4.11.1"
   ```

2. Run the update command:

   ```bash
   just update-vendor
   ```

3. Test the application to verify everything works with the new versions.

4. Commit the updated files in `wies/core/static/vendor/`.

### Testing

Run all tests:

```bash
just test
```

Run specific tests:

```bash
just manage test wies.core.tests.test_roles
```

### Special URLs

Not linked in the UI:

- `/djadmin/` - Django admin
- `/djadmin/db/` - Drop database and load dummy data
- `/plaatsingen/import/` - Import placements from CSV

## Architecture

### User Roles

| Role           | Description                  | Permissions                   |
| -------------- | ---------------------------- | ----------------------------- |
| **Beheerder**  | Administrator                | User and label management     |
| **Consultant** | Employee                     | View-only access              |
| **BDM**        | Business Development Manager | Create and manage assignments |

### Core Concepts

| Term           | Description                                     |
| -------------- | ----------------------------------------------- |
| **Plaatsing**  | Placement of a colleague on a service           |
| **Opdracht**   | Assignment/project for a ministry               |
| **Dienst**     | Service/work needed for an assignment           |
| **Collega**    | Colleague with skills who can be placed         |
| **Ministerie** | Government organization that issues assignments |

## Deployment

### Docker

```bash
# Build image
docker build -t wies .

# Run with gunicorn (default entrypoint)
docker run -p 8000:8000 --env-file .env wies
```

### Docker Compose

```bash
# Start only the Django application
docker compose up

# Start Django + cron scheduler (for scheduled tasks)
docker compose --profile cron up
```

> **Note:** Services with `profiles: [cron]` do NOT start with regular `docker compose up`. Use `--profile cron` to include them.

### Kubernetes

For Kubernetes deployment:

1. **Web deployment**: Use the default image entrypoint (gunicorn). Mount a PersistentVolume for the SQLite database.
2. **Scheduled tasks**: Create a CronJob that runs the management command directly

Example CronJob for organization sync:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: wies-sync-organizations
spec:
  schedule: "21 3 * * *" # Daily at 3:21 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: sync
              image: wies:latest
              command: ["python", "manage.py", "sync_organizations", "--yes"]
          restartPolicy: OnFailure
```

### Scheduled Tasks

Organization data is synced from [organisaties.overheid.nl](https://organisaties.overheid.nl).

| Task               | Schedule      | Command                                     |
| ------------------ | ------------- | ------------------------------------------- |
| Sync organizations | Daily 3:21 AM | `python manage.py sync_organizations --yes` |

## Release Process

1. Everything in `main` branch
2. Change "unreleased" in CHANGES to date
3. Commit and push
4. Tag with date: `git tag -a 2026-01-19 -m "2026-01-19"`
5. Push tag: `git push --tags`
6. CI produces image

## Claude Code

This project has configuration for [Claude Code](https://claude.ai/code) in `.claude/`:

```
.claude/
├── CLAUDE.md    # Project instructions and context
├── rules/       # Code style, testing, security guidelines
├── skills/      # Domain knowledge, Django patterns, UI components
└── agents/      # Specialized agents for UI development
```

Start a Claude Code session in the project root for AI-assisted development with project context.
