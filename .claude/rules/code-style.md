# Code Style

## Python

- Python 3.13+ with type hints on public functions
- Use `uv` for package management
- Format with `ruff format`, lint with `ruff check --fix`

## Django

- Models in `wies/core/models.py`
- Use `verbose_name` for Dutch field labels
- ForeignKey: use `related_name` and `on_delete=models.CASCADE`
- Querysets in `querysets.py` for complex queries

## Templates (Jinja2)

- Located in `wies/core/jinja2/`
- Use RVO macros from jinja-roos-components
- Dutch labels for all user-facing text

## Commits

- English commit messages
- Reference issue numbers where applicable
