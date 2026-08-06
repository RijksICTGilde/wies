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
public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
```

Route on `<uuid:public_id>`, look the object up by `public_id`, and resolve
filter facets through `FacetResolver` so they inherit the fail-closed
behaviour. The migration needs three steps (nullable, backfill distinct
values, then unique + non-null); one `AddField` with a callable default gives
every existing row the same value. Full workflow: `features/public_id.md`.

## Migrations Stay Self-Contained

A migration must import nothing from the app: it is frozen in time, and app
code is not. Spell the model list, the data loop and the field default out in
the migration itself. Prefer a stdlib callable for a field default
(`uuid.uuid4`, not a helper of ours): Django compares defaults by callable
identity, so a migration-local copy of an app function is a different callable
and `makemigrations` keeps proposing an `AlterField` for it forever.

A test that drives the executor (`test_*_migration.py`) must return the
database to the graph's leaf in `tearDown`, never to a hardcoded name.
Migrating to a target that is already applied puts the executor in backwards
mode, so a fixed name silently rolls back everything added after it and leaves
the rest of the suite on an outdated schema.

## Dummy Data

- `wies/core/fixtures/base_dummy_data.json` — small dataset, committed (for `just setup`, no network needed)
- `python manage.py load_full_data` — full dataset via sync + ORM (for `just load-full-data`, needs network)
