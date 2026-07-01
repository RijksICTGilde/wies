# Wies

Internal tool for managing colleague placements within the Dutch government. Wies provides an overview of who is working where, on what, and when.

## Tech Stack

- **Backend**: Django 6 with PostgreSQL
- **Templates**: Jinja2 with [jinja-roos-components](https://github.com/RijksICTGilde/jinja-roos-components)
- **Styling**: [RVO Design System](https://github.com/nl-design-system/rvo) (Dutch government design system)
- **Interactivity**: HTMX
- **Authentication**: OIDC via Keycloak
- **Package management**: uv

## Prerequisites

- [Docker](https://www.docker.com/)
- [just](https://github.com/casey/just)
- [uv](https://docs.astral.sh/uv/)
- [Node.js](https://nodejs.org/) (for JavaScript tests)
- [pre-commit](https://pre-commit.com/)

## Quick Start

### Setup

Installs dependencies, sets up database with base dummy data, creates `.env`:

```bash
just setup
```

Optionally, generate and load full dummy data for performance testing (requires network):

```bash
just load-full-data
```

Then update `.env`:

- Fill in OIDC credentials
- Set `INITIAL_USER_FIRSTNAME`, `INITIAL_USER_LASTNAME`, `INITIAL_USER_EMAIL` (yourself)
- Set `STAFF_EMAILS`

### Start

```bash
just up
```

## Development

### Project Structure

- `wies/core/` — main Django app (models, views, forms, templates, tests)
- `wies/rijksauth/` — OIDC auth integration
- `config/settings/` — Django settings per environment
- `docs/` — beheerplan, privacy declaration and other docs
- `features/` — feature-specific design docs (e.g. inline editing)

### Commands

```bash
just setup          # Set up fresh environment (base dummy data)
just load-full-data # Generate and load full dummy data
just up             # Start application
just down           # Stop containers
just test           # Run all tests (Django + JS)
just test django    # Run Django tests only
just test js        # Run JavaScript tests only
just manage [...]   # Django manage.py commands
just lint           # Run ruff check + format check
just format         # Auto-fix lint issues and format code
just pre-commit     # Run all pre-commit hooks
just update-vendor  # Update vendor assets (htmx)
```

### Vendor Assets

This project vendors external JavaScript instead of using a CDN. This ensures the application works without external network dependencies and improves security (no CDN in CSP).

**Vendored packages:**

- [htmx](https://htmx.org/) - JavaScript library for AJAX/HTML

#### Update vendor dependencies

To update vendor dependencies:

1. Edit the version numbers at the top of `justfile` (e.g. `HTMX_VERSION`).

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

Run Django or JavaScript tests separately:

```bash
just test django
just test js
```

Run specific Django tests:

```bash
just manage test wies.core.tests.test_roles
```

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

## Release Process

1. Everything in `main` branch
2. Change "unreleased" in CHANGES to date
3. Commit and push
4. Tag with date: `git tag -a 2026-01-19 -m "2026-01-19"`
5. Push tag: `git push --tags`
6. CI produces image and deploys

## Claude Code

This project has configuration for [Claude Code](https://claude.ai/code) in `.claude/` (project instructions, rules, skills, and agents). Start a Claude Code session in the project root for AI-assisted development with project context.
