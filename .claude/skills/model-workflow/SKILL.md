---
name: model-workflow
description: Django model change workflow for Wies. Use automatically when modifying models in wies/core/models.py to ensure dummy_data.json is updated and migrations are mentioned.
---

# Model Change Workflow

When changing Django models in Wies, follow this workflow:

## Steps

1. **Update model** in `wies/core/models.py`
2. **Update dummy_data.json** to match new structure
   - Format: Django dumpdata JSON format
   - Include `model`, `pk`, and `fields` keys
3. **Do NOT run makemigrations** - just mention "migration needed" to the user
4. **Update forms** in `forms.py` if fields changed
5. **Update views** if business logic affected
6. **Run tests** with `just test` to verify nothing breaks

## Dummy Data Format

```json
{
  "model": "core.modelname",
  "pk": 1,
  "fields": {
    "field_name": "value"
  }
}
```

## Checklist

- [ ] Model updated
- [ ] dummy_data.json updated
- [ ] Migration mentioned (not executed)
- [ ] Forms updated (if needed)
- [ ] Views updated (if needed)
- [ ] Tests pass
