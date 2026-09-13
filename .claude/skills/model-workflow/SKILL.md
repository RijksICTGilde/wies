---
name: model-workflow
description: Django model change workflow for Wies. Use automatically when modifying models in wies/core/models.py to ensure load_full_data.py is updated and migrations are mentioned.
---

# Model Change Workflow

When changing Django models in Wies, follow this workflow:

## Steps

1. **Update model** in `wies/core/models.py`
2. **Update `wies/core/management/commands/load_full_data.py`** (the dummy-data generator's `generate()`) to match new model structure — both size profiles run through it
3. **Do NOT run makemigrations** - just mention "migration needed" to the user
4. **Update forms** in `forms.py` if fields changed
5. **Update views** if business logic affected
6. **Run tests** with `just test` to verify nothing breaks

## Dummy Data

One generator, two size profiles (both run `load_full_data.generate()`):

- `python manage.py load_dummy_data --profile base` — small dataset, local orgs, no network (for `just setup`)
- `python manage.py load_dummy_data --profile full` (alias: `load_full_data`) — full dataset via org sync + ORM (for `just load-full-data`, needs network)

## Checklist

- [ ] Model updated
- [ ] load_full_data.py updated
- [ ] Base fixture updated (if structural model change)
- [ ] Migration mentioned (not executed)
- [ ] Forms updated (if needed)
- [ ] Views updated (if needed)
- [ ] Tests pass
