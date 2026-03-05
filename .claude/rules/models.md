# Model Change Workflow

When changing Django models:

1. **Update model** in `wies/core/models.py`
2. **Update `wies/core/management/commands/load_full_data.py`** to match new model structure
3. **Update `wies/core/fixtures/base_dummy_data.json`** if fields were added (required), renamed, or removed
4. **Do NOT run makemigrations** - just mention "migration needed"
5. **Update forms** in `forms.py` if fields changed
6. **Update views** if business logic affected
7. **Run tests** to verify nothing breaks

## Dummy Data

- `wies/core/fixtures/base_dummy_data.json` — small dataset, committed (for `just setup`, no network needed)
- `python manage.py load_full_data` — full dataset via sync + ORM (for `just load-full-data`, needs network)
