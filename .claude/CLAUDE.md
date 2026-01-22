# Wies Project

Internal Dutch government tool for managing colleague assignments (plaatsingen).
Language: Dutch UI, English code.

## Tech Stack

- Django 5.2 with SQLite
- Jinja2 templates with jinja-roos-components (https://github.com/RijksICTGilde/jinja-roos-components)
- RVO CSS classes for layout/styling (nl-design-system/rvo)
- HTMX for interactivity
- OIDC authentication via Keycloak
- uv for Python dependencies

## Commands

- `just setup` - Fresh environment
- `just up` - Start containers
- `just down` - Stop containers
- `just test` - Run tests
- `uv run ruff check --fix` - Lint and fix

## Code Style

- Python 3.13+ with type hints
- Django models in `wies/core/models.py`
- Views in `wies/core/views.py`
- Forms use RVOMixin for styling
- Templates in `wies/core/jinja2/`

## Workflow Rules

### Model Changes

1. Update the model in `wies/core/models.py`
2. Update `dummy_data.json` to match new structure
3. Do NOT run makemigrations - mention migration needed
4. Update affected forms and views

### UI Changes

- Use jinja-roos-components (`<c-button>`, `<c-input>`, etc.)
- Reference: https://github.com/RijksICTGilde/jinja-roos-components
- Use RVO CSS classes for layout (fallback: https://github.com/nl-design-system/rvo)
- Dutch labels and messages

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
- Dummy data: `dummy_data.json`
