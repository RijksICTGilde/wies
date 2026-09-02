# Wies Project

Internal Dutch government tool for managing colleague assignments (plaatsingen).
Language: Dutch UI, English code.

## Tech Stack

- Django 6 with PostgreSQL
- Jinja2 templates
- [@nldd/design-system](https://www.npmjs.com/package/@nldd/design-system) - NLDD web components
- HTMX for interactivity
- OIDC authentication via Keycloak
- uv for Python dependencies
- Inline editing (pencil icon, HTMX swap) via the Editables system in `wies/core/inline_edit/` — see `features/inline-editing.md`. Same declarations back full-page forms (e.g. `AssignmentCreateForm`).

## Commands

- `just setup` - Fresh environment (loads base dummy data)
- `just load-full-data` - Sync organizations + generate dummy data (needs network)
- `just up` - Start containers
- `just down` - Stop containers
- `just test` - Run tests
- `uv run ruff check --fix` - Lint and fix

## Code Style

- Python 3.14+ with type hints
- Django models in `wies/core/models.py`
- Views in `wies/core/views.py`
- Forms use NlddFormMixin for styling
- Templates in `wies/core/jinja2/`

## Workflow Rules

### Model Changes

1. Update the model in `wies/core/models.py`
2. Give the model a `public_id` if it will ever appear in a URL (the integer PK
   stays internal, always). See `features/public_id.md`.
3. Update `wies/core/management/commands/load_full_data.py` to match new model structure
4. Run `uv run python manage.py makemigrations` to generate migrations
5. Update affected forms and views

### UI Changes

- Use [@nldd/design-system](https://www.npmjs.com/package/@nldd/design-system) - NLDD web components
- Reference: https://minbzk.github.io/storybook/
- Dutch labels and messages
- Web components in a server-rendered app have their own pitfalls (swap
  timing, shadow-DOM boundaries, form-error wiring): `rules/nldd-integration.md`

### Forms & Inline Editing

When extending an existing form OR adding a new editable field on a model
that already has an `EditableSet` (Assignment, Colleague, Placement,
Service, User), declare the field as an `Editable` in
`wies/core/editables/<model>.py` instead of writing a bespoke form field.
Full-page forms reference the same declarations via
`AssignmentEditables.<name>.form_field()`. Workflow and patterns:
`features/inline-editing.md`.

### Changelog

Every user-facing change must be recorded in `CHANGES.md` under the
`## unreleased` heading, as a `- <PR#>: <description>` bullet — the PR
number, so a reader can jump straight to the code/discussion. Add the
entry as part of the same PR; since the PR number isn't known until the
PR is opened, fill it in (or correct a placeholder) once the PR exists. The changelog items are in English.

### Testing

- Run `just test` before completing changes
- Test files in `wies/core/tests/`
- Use `DJANGO_SETTINGS_MODULE=config.settings.local`

## Key Files

- Models: `wies/core/models.py`
- Views: `wies/core/views.py`
- Forms: `wies/core/forms.py`
- Templates: `wies/core/jinja2/`
- Roles/Permissions: `wies/core/roles.py`
- Base fixture: `wies/core/fixtures/base_dummy_data.json` (committed, small dataset)
- Dummy data generator: `wies/core/management/commands/load_full_data.py` (management command)
