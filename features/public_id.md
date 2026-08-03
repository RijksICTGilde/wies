# Public IDs in URLs

`wies/core/public_id.py` gives URL-exposed records an unguessable
`public_id`, so the sequential database PK never appears in a URL. This
blocks enumeration: without it an authenticated user could walk
`/opdrachten/1/`, `/opdrachten/2/`, ... and harvest opdrachten,
colleague names/e-mail and placements — and, via the filters, whole
overviews (who sits at which organization).

The PK stays internal (the audit log references records by their internal
id and has no retention window, so replacing the PK would break it).
`public_id` is a separate, unique column added alongside it.

## What carries a public_id

The client-facing models: `LabelCategory`, `Label`, `Skill`,
`Colleague`, `Assignment`, `Placement`, `Service`, `OrganizationUnit`,
`Suborganization` (plus `User`). Each declares `public_id` and inherits
from `PublicIdModel` (see _Collision handling_).

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
  Django's built-in `<uuid:>` path converter — no custom alphabet or
  converter to maintain. Every reviewer and tool recognises it on sight.

A shorter, "prettier" token (e.g. base58, ~12 chars) was considered for
shorter URLs, but the gain is purely cosmetic and does not justify
departing from the standard.

## Why a separate column, not the PK

The performance stories about UUIDs are almost all about UUID **as the
primary key**. We avoid them by keeping the integer PK internal:

- **Size multiplies.** A 16-byte UUID PK lives in every foreign key and
  every index that carries the PK (int = 4 bytes). Joins and indexes grow;
  less fits in cache.
- **Random inserts.** A random UUID PK lands anywhere in the index →
  page splits, fragmentation, write amplification (catastrophic on
  MySQL/InnoDB via clustering; Postgres suffers less but still bloats).
- **Audit log.** `Event`/`AuthEvent` reference records by internal `id`;
  replacing the PK would break that.

With a separate `public_id` column there is exactly **one** secondary
unique index per table whose inserts are random — bounded, on
low-write tables. All relationships, joins and the audit log stay on the
cheap int PK. (At our scale a UUID PK in Postgres would perform fine
anyway; there is simply no reason for it, and real migration risk.)

## Properties

- **UUIDv4**, 122 bits — unguessable, and a realistic collision is
  astronomically unlikely.
- **Routing:** Django's built-in `<uuid:public_id>` converter, so a
  malformed value 404s at routing and never reaches the database.
- **Filters:** the facet params arrive as raw query strings; a `UUIDField`
  lookup would raise on a non-UUID value, so `parse_public_ids()` converts
  them to UUIDs first (junk is dropped and simply matches nothing). The
  tree traversal and per-org counts stay on internal `id`; only the URL
  boundary speaks UUID.
- **Select options:** Django keys `ModelChoiceField` options on the pk, so
  `use_public_id_choices()` sets `to_field_name="public_id"` for every
  choice field whose model has one. `_build_form_field` applies it to all
  Editables; the hand-declared fields in `forms.py` pass the same
  `to_field_name`. A model without a `public_id` (e.g. `Group`) keeps the
  pk. Junk and stale pks come back as a normal "invalid choice" error.

## Collision handling

`public_id` uniqueness is enforced by the column constraint. On the
astronomically rare clash, `PublicIdModel.save()` regenerates the
`public_id` and retries (up to 3 attempts) instead of surfacing a 500.
Any _other_ `IntegrityError` (e.g. a duplicate name) is re-raised
untouched, and each attempt runs in a savepoint so a caller's surrounding
transaction survives the failed insert.

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
  was exactly such a spot — the tree emitted `public_id` while the form
  field still resolved on PK.
- **Two spots still round-trip a pk on purpose.** The inline-edit field
  name for a label category (`labels_<pk>`) and the hidden `id` /
  `placement_id` on the team rows in `ServiceForm`. Both identify a row
  the caller was already shown, and the services save re-verifies each one
  belongs to the target Assignment before writing. They are walkable in
  principle, but yield only which taxonomy/row ids exist, never record
  data, and no read path accepts an integer.

## Key files

- `wies/core/public_id.py` — `generate_public_id` (uuid4) and
  `parse_public_ids` (filter-input parsing)
- `wies/core/models.py` — `PublicIdModel` (the retry base) and the
  per-model `public_id` field
- `wies/core/inline_edit/forms.py` — `use_public_id_choices` (select
  option values)
- `wies/core/tests/test_public_id.py` — per-model id, routing rejects the
  int form, choice fields reject the pk, collision retry
