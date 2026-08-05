# Public IDs in URLs

`wies/core/public_id.py` gives URL-exposed records an unguessable
`public_id`, so the sequential database PK never appears in a URL. This
blocks enumeration: without it an authenticated user could walk
`/opdrachten/1/`, `/opdrachten/2/`, ... and harvest opdrachten,
colleague names/e-mail and placements, and via the filters whole
overviews (who sits at which organization).

The PK stays internal (the audit log references records by their internal
id and has no retention window, so replacing the PK would break it).
`public_id` is a separate, unique column added alongside it.

## What carries a public_id

The client-facing models: `LabelCategory`, `Label`, `Skill`,
`Colleague`, `Assignment`, `Placement`, `Service`, `OrganizationUnit`,
`Suborganization` (plus `User`). Each declares the field the same way:

```python
public_id = models.UUIDField(default=generate_public_id, unique=True, editable=False)
```

It appears in the object URLs (panels `?opdracht=`/`?collega=`/
`?plaatsing=`, the beheer edit/delete routes, the inline-edit endpoint)
and in the filter facets (`?org=`, `?rol=`, `?labels=`, `?merk=`,
including the organization tree in the modal).

## Why UUIDv4

UUIDv4 is the industry-standard opaque, unguessable identifier, and we
have no good reason to deviate:

- **Unguessable:** 122 bits of randomness; not walkable or predictable.
- **No time leak:** unlike v7/ULID, v4 carries no timestamp.
- **Standard and recognisable:** native `UUIDField` (Postgres `uuid`) and
  Django's built-in `<uuid:>` path converter, so there is no custom
  alphabet or converter to maintain. Every reviewer and tool recognises
  it on sight.

A shorter, "prettier" token (e.g. base58, ~12 chars) was considered for
shorter URLs, but the gain is purely cosmetic and does not justify
departing from the standard.

## Why a separate column, not the PK

The performance stories about UUIDs are almost all about UUID **as the
primary key**. We avoid them by keeping the integer PK internal:

- **Size multiplies.** A 16-byte UUID PK lives in every foreign key and
  every index that carries the PK (int = 4 bytes). Joins and indexes grow;
  less fits in cache.
- **Random inserts.** A random UUID PK lands anywhere in the index, which
  means page splits, fragmentation and write amplification (catastrophic
  on MySQL/InnoDB via clustering; Postgres suffers less but still bloats).
- **Audit log.** `Event`/`AuthEvent` reference records by internal `id`;
  replacing the PK would break that.

With a separate `public_id` column there is exactly **one** secondary
unique index per table whose inserts are random, bounded and on
low-write tables. All relationships, joins and the audit log stay on the
cheap int PK. (At our scale a UUID PK in Postgres would perform fine
anyway; there is simply no reason for it, and real migration risk.)

## Properties

- **Uniqueness** is the column constraint, and nothing else. At 122 bits
  a collision is not a case worth writing code for: with a million rows
  in one table the probability is on the order of 1 in 10^25, many orders
  below a silent bitflip corrupting the value on its way to disk. An
  earlier version regenerated and retried on clash; it cost a savepoint
  on every write of every model and an extra query on every unrelated
  `IntegrityError`, so it was removed.
- **Routing:** Django's built-in `<uuid:public_id>` converter, so a
  malformed value 404s at routing and never reaches the database.
- **Filters:** the facet params arrive as raw query strings, so
  `FacetResolver` resolves each one to internal ids once per request
  (`_apply_filters` runs once per facet to compute the cross-filter
  counts). The tree traversal and per-org counts stay on internal `id`;
  only the URL boundary speaks UUID.
- **Filters fail closed.** A facet that is present in the URL but
  resolves to no row filters everything away, it is never dropped. See
  `ResolvedFacet.requested`. A stale id in a shared or bookmarked URL
  must not quietly show more than it asks for, and this is uniform across
  `?org=`, `?org_self=`, `?rol=`, `?merk=` and `?labels=`.
- **But never into a dead end.** A value that resolves to nothing still
  counts as an active filter (`ResolvedFacet.active_values`), so the empty
  list keeps its chip strip and its "Wis alle filters" button. Without
  that the user lands on an empty page with no filter in sight and no way
  back. Unknown organizations get their own chip label
  (`UNKNOWN_ORG_LABEL`), since the org chips are built by hand rather than
  matched against a rendered option.
- **An empty value is not a filter.** `?org=` is an unset select, not a
  selection that matched nothing, so `resolve_facet` drops blank tokens
  before deciding `requested`. Emptying the list on a blank value would
  strand the user on a filter they never chose.
- **Select options:** Django keys `ModelChoiceField` options on the pk, so
  `use_public_id_choices()` sets `to_field_name="public_id"` for every
  choice field whose model has one. `_build_form_field` applies it to all
  Editables; the hand-declared fields in `forms.py` pass the same
  `to_field_name`. A model without a `public_id` (e.g. `Group`) keeps the
  pk. Junk and stale pks come back as a normal "invalid choice" error.

## Adding a public_id to a new model

1. Declare the field exactly as above and add the model to
   `.claude/rules/models.md`'s checklist reflex: anything that lands in a
   URL needs one.
2. Write the migration in three steps (nullable, backfill distinct values,
   then unique + non-null). One `AddField` with a callable default gives
   every existing row the _same_ value and breaks the unique constraint.
   See `wies/core/migrations/0012_public_ids.py`.
3. Route on `<uuid:public_id>` and look the object up by `public_id`.
4. If the model appears in a filter facet, resolve it through
   `FacetResolver` so it inherits the fail-closed behaviour.

## Caveats

- **A public_id is not authorization.** It hides the PK, but if an
  endpoint forgets its role check, knowing or guessing a public_id still
  grants access. It is defense-in-depth on top of the permission checks,
  not a replacement. Likewise, tokenised filters raise the bar for bulk
  extraction; they do not stop a determined scraper paging the list.
- **Consistency is the live risk, not the generator.** Anything crossing
  the client boundary (URLs, hidden form inputs, `data-*` attributes,
  JSON the browser consumes) must use `public_id`; a half-migrated spot
  that leaks a PK reintroduces the enumeration it removed. The org picker
  was exactly such a spot: the tree emitted `public_id` while the form
  field still resolved on PK.
- **Two spots still round-trip a pk on purpose.** The inline-edit field
  name for a label category (`labels_<pk>`) and the hidden `id` /
  `placement_id` on the team rows in `ServiceForm`. Both identify a row
  the caller was already shown, and the services save re-verifies each one
  belongs to the target Assignment before writing. They are walkable in
  principle, but yield only which taxonomy/row ids exist, never record
  data, and no read path accepts an integer.

## Key files

- `wies/core/public_id.py`: `generate_public_id` (uuid4),
  `parse_public_ids` (filter-input parsing), and `ResolvedFacet` /
  `resolve_facet` / `FacetResolver` (per-request facet resolution)
- `wies/core/models.py`: the per-model `public_id` field
- `wies/core/views.py`: `PublicIdFacetsMixin`, which gives a list view its
  `facets` resolver and the shared org-filter/chip helpers
- `wies/core/inline_edit/forms.py`: `use_public_id_choices` (select
  option values)
- `wies/core/tests/test_public_id.py`: per-model id, routing rejects the
  int form, choice fields reject the pk, and every facet failing closed
