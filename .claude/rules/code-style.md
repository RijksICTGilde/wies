# Code Style

## Python

- Python 3.14+ with type hints on public functions
- Use `uv` for package management
- Format with `ruff format`, lint with `ruff check --fix`
- When adding `# noqa` comments, always include what the rule enforces and why the suppression is justified here (e.g. `# noqa: F401 (unused import), PLC0415 (import not at top level) — Django signal registration must happen inside ready()`)

## Django

- Models in `wies/core/models.py`
- Use `verbose_name` for Dutch field labels
- ForeignKey: use `related_name` and `on_delete=models.CASCADE`
- Querysets in `querysets.py` for complex queries
- Use `django.utils.timezone.now()` for current time (not `datetime.now()` or `datetime.utcnow()`)

## Templates (Jinja2)

- Located in `wies/core/jinja2/`
- Use RVO macros from jinja-roos-components
- Dutch labels for all user-facing text

## Commits

- English commit messages
- Reference issue numbers where applicable
