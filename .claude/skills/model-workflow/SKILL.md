---
name: model-workflow
description: Django model change workflow for Wies. Use automatically when modifying models in wies/core/models.py to ensure load_full_data.py is updated and migrations are mentioned.
---

# Model Change Workflow

When changing Django models in Wies, follow this workflow:

## Steps

1. **Update model** in `wies/core/models.py`
2. **Update `wies/core/management/commands/load_full_data.py`** to match new model structure
3. **Update `wies/core/fixtures/base_dummy_data.json`** if fields were added (required), renamed, or removed — otherwise `just setup` will break
4. **Do NOT run makemigrations** - just mention "migration needed" to the user
5. **Update forms** in `forms.py` if fields changed
6. **Update views** if business logic affected
7. **Run tests** with `just test` to verify nothing breaks

## Dummy Data

- `wies/core/fixtures/base_dummy_data.json` — small dataset, committed (for `just setup`, no network needed)
- `wies/core/management/commands/load_full_data.py` — generates full dataset via sync + ORM (for `just load-full-data`, needs network)

## Checklist

- [ ] Model updated
- [ ] load_full_data.py updated
- [ ] Base fixture updated (if structural model change)
- [ ] Migration mentioned (not executed)
- [ ] Forms updated (if needed)
- [ ] Views updated (if needed)
- [ ] Tests pass
