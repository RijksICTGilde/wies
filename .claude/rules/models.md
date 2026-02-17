# Model Change Workflow

When changing Django models:

1. **Update model** in `wies/core/models.py`
2. **Update `scripts/generate_dummy_data.py`** to match new model structure
3. **If Skills changed**, regenerate base fixture: `python scripts/generate_dummy_data.py --small`
4. **Do NOT run makemigrations** - just mention "migration needed"
5. **Update forms** in `forms.py` if fields changed
6. **Update views** if business logic affected
7. **Run tests** to verify nothing breaks

## Dummy Data

- `wies/core/fixtures/base_dummy_data.json` — small dataset, committed (generated with `--small`)
- `wies/core/fixtures/full_dummy_data.json` — full dataset, gitignored (generated without flag)
- `scripts/generate_dummy_data.py` — generates both fixtures
