# Model Change Workflow

When changing Django models:

1. **Update model** in `wies/core/models.py`
2. **Update dummy_data.json** to match new structure
3. **Do NOT run makemigrations** - just mention "migration needed"
4. **Update forms** in `forms.py` if fields changed
5. **Update views** if business logic affected
6. **Run tests** to verify nothing breaks

## Dummy Data Format

Django dumpdata format:

- model: "core.modelname"
- pk: integer
- fields: { field values }

## Model Design Principles

- **YAGNI**: Don't add fields/methods until needed
- **Single source of truth**: Use config dicts for related constants:
  ```python
  CONFIG = {"key": {"label": "...", "is_x": True}}
  MyChoices = models.TextChoices("MyChoices", {k.upper(): (k, v["label"]) for k, v in CONFIG.items()})
  ```
- **Validation**: Use `clean()` method, place right after `__str__`
- **Unique optional fields**: Use `blank=True, null=True, unique=True`
