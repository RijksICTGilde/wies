# Code Style

## Python

- Python 3.13+ with type hints on public functions
- Use `uv` for package management
- Format with `ruff format`, lint with `ruff check --fix`
- Run `uv run ruff check` before completing changes

### Ruff Rules to Watch

- **TRY003/EM101/EM102**: Assign exception messages to variable first:

  ```python
  # Wrong
  raise ValidationError("Some message")

  # Right
  msg = "Some message"
  raise ValidationError(msg)
  ```

- **E501**: Line too long (120 max). Use multiline strings for long help_text in migrations.
- **PT009/PT027**: Use `pytest.raises` and `assert` instead of unittest-style
- **PLC0415**: Imports at top of file

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
