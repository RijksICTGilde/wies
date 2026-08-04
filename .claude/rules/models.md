# Model Change Workflow

When changing Django models:

1. **Update model** in `wies/core/models.py`
2. **Add a `public_id`** if the model will ever appear in a URL (object route,
   panel param, filter facet, hidden form value). See below.
3. **Update `wies/core/management/commands/load_full_data.py`** to match new model structure
4. **Update `wies/core/fixtures/base_dummy_data.json`** if fields were added (required), renamed, or removed
5. **Run `uv run python manage.py makemigrations`** to generate migrations
6. **Update forms** in `forms.py` if fields changed
7. **Update views** if business logic affected
8. **Run tests** to verify nothing breaks

## Public IDs in URLs

The integer PK is internal and must never end up in a URL: it is sequential,
so exposing it lets any logged-in user enumerate records. A model that is
reachable from the client carries a `public_id` instead:

```python
public_id = models.UUIDField(default=generate_public_id, unique=True, editable=False)
```

Route on `<uuid:public_id>`, look the object up by `public_id`, and resolve
filter facets through `FacetResolver` so they inherit the fail-closed
behaviour. The migration needs three steps (nullable, backfill distinct
values, then unique + non-null); one `AddField` with a callable default gives
every existing row the same value. Full workflow: `features/public_id.md`.

## Dummy Data

- `wies/core/fixtures/base_dummy_data.json` — small dataset, committed (for `just setup`, no network needed)
- `python manage.py load_full_data` — full dataset via sync + ORM (for `just load-full-data`, needs network)
