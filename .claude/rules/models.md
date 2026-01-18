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
