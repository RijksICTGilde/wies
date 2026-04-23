# Inline editing

`wies/core/inline_edit/` makes a model field inline-editable: a pencil
next to the value, HTMX swap to a small form on click, save swaps back
with a brief checkmark flash.

The same declaration is reused by full-page forms (e.g.
`AssignmentCreateForm`), so a label change or queryset tweak only has
to be made once.

## Mental model

```
EditableSet  (per model)
  ├── Editable             single field
  ├── EditableGroup        multiple fields edited together (e.g. period)
  └── EditableCollection   N rows of a child object (e.g. services on an assignment)
```

One shared URL, `/inline-edit/<model_label>/<pk>/<name>/`, serves every
editable. It handles the full flow: GET returns the display (or the
form with `?edit=true`), POST validates and saves, `?cancel=true`
restores the display, and permission denials degrade to a read-only
display with a Dutch warning alert.

## File layout

```
wies/core/inline_edit/
├── base.py              # Editable, EditableGroup, EditableCollection, EditableSet
├── forms.py             # build_form_class, build_form_from, save_*
├── views.py             # inline_edit_view (single generic endpoint)
├── jinja.py             # inline_edit(obj, name) Jinja global
└── editables/
    ├── __init__.py      # REGISTRY dict — explicit model_label → EditableSet mapping
    ├── assignment.py
    ├── colleague.py     # dynamic labels_<id> via resolve_dynamic
    ├── placement.py
    ├── service.py
    └── user_profile.py

wies/core/jinja2/parts/inline_edit/
├── display.html            # read-mode wrapper (pencil + value)
├── form.html               # edit-mode wrapper (form + save/cancel)
├── collection_form.html    # edit-mode wrapper for EditableCollection
└── displays/               # per-field custom display partials (optional)
```

## Adding an inline-editable field

### 1. Trivial: just a model field

```python
class AssignmentEditables(EditableSet):
    model = Assignment
    object_permission = staticmethod(user_can_edit_assignment)

    name = Editable(label="Opdracht naam")
```

Type, required, choices, max_length auto-derive from the Django model
field. Override only what's different.

```jinja
{{ inline_edit(assignment, "name") }}
```

### 2. Custom widget / validators

```python
extra_info = Editable(
    label="Beschrijving",
    widget=forms.Textarea(attrs={"rows": 4}),
    error_messages={"required": "Beschrijving is verplicht"},
)
```

### 3. FK / M2M queryset

```python
def _bdm_queryset():
    return Colleague.objects.filter(user__groups__name="Business Development Manager").order_by("name")

owner = Editable(
    label="Business Manager",
    choices=_bdm_queryset,   # callable, not the queryset itself
    required=True,
    empty_label=" ",
)
```

Wrap querysets in a callable — they evaluate lazily per request.

### 4. Custom display (partial)

```python
owner = Editable(
    ...,
    display="parts/inline_edit/displays/assignment_owner.html",
)
```

The partial receives `obj` (instance), `value` (current value; for a
group, a dict keyed by field name; for a collection, the row list),
and `editable` (the spec). It must degrade gracefully when optional
extras are absent — post-save re-renders don't carry them.

### 5. Custom display (callable)

```python
display=lambda assignment: f"#{assignment.id} {assignment.name}"
```

### 6. Group edited together

```python
period = EditableGroup(
    label="Looptijd",
    fields=[start_date, end_date],
    clean=_period_clean,            # cross-field validator
    display="parts/inline_edit/displays/assignment_period.html",
)
```

One URL, one form with both inputs, one cross-field `clean`. The
display partial's `value` is `{"start_date": ..., "end_date": ...}`.

### 7. Field that doesn't map 1:1 to a model attribute

```python
organizations = Editable(
    label="Opdrachtgever(s)",
    form_field=lambda: OrganizationsField(required=True),
    initial=_organizations_initial,   # (obj) -> current value
    save=_save_organizations,         # (obj, value) -> persist
    display="parts/inline_edit/displays/assignment_organizations.html",
)
```

Wrap multi-statement saves in `transaction.atomic()` so a partial
failure doesn't leave the DB torn.

### 8. Group-level atomic save

When several fields must persist together (e.g. through-table rows),
attach `save` to the `EditableGroup` — it sees the whole
`cleaned_data` dict.

### 9. Collection of child objects

When one editable edits N rows of child objects (e.g. services +
placements on an assignment):

```python
services = EditableCollection(
    label="Team",
    formset_factory=_services_formset_factory,  # (data=None, initial=None) -> formset
    initial=_services_initial,                   # (obj) -> list[dict]
    save=_save_services,                         # (obj, formset) -> persist
    form_template="parts/assignment_services_form.html",
    display="parts/inline_edit/displays/assignment_services.html",
)
```

The `form_template` is included inside `collection_form.html` and
receives the formset as `formset`. The `display` partial receives the
row list as `value`.

### 10. Per-row editables driven by DB rows

When the set of editables depends on DB content (one editable per
LabelCategory row), override `resolve_dynamic`:

```python
class ColleagueEditables(EditableSet):
    model = Colleague

    @classmethod
    def resolve_dynamic(cls, name):
        if not name.startswith("labels_"):
            return None
        try:
            cat_id = int(name[len("labels_"):])
        except ValueError:
            return None
        category = LabelCategory.objects.filter(pk=cat_id).first()
        if category is None:
            return None
        return _build_label_editable(category)
```

Called by the view and the Jinja global when static `_editables` has
no match. Returning `None` produces a 404.

## Permissions

Two gates, both optional:

```python
class AssignmentEditables(EditableSet):
    object_permission = staticmethod(user_can_edit_assignment)  # set-wide

    name = Editable(permission=lambda user, obj: ...)           # per-field
```

Denial returns the display partial with a warning alert and no
pencil.

## Reusing an editable in a full-page form

```python
_AssignmentCreateFormBase = build_form_from(
    AssignmentEditables,
    fields=[
        AssignmentEditables.name,
        AssignmentEditables.extra_info,
        AssignmentEditables.period,
        AssignmentEditables.owner,
        AssignmentEditables.organizations,
    ],
)


class AssignmentCreateForm(_AssignmentCreateFormBase):
    """Stable importable name; body intentionally empty."""
```

Pass an `EditableGroup` directly and its `clean` becomes the form's
`clean()` — no manual override needed.

## URL contract

```
/inline-edit/<model_label>/<pk>/<name>/
```

- `model_label` — `Model._meta.model_name` (lowercase, e.g. `assignment`).
- `pk` — integer primary key.
- `name` — attribute name on the EditableSet (e.g. `extra_info`,
  `period`, `services`, `labels_42`).

Query params:

- `?edit=true` — return the form (clicked pencil).
- `?cancel=true` — return the display (clicked cancel).
- (no param) — return the display (initial render).

`POST` validates and saves; success returns the display partial with
a `--just-saved` flash, failure returns the form with errors inline.

## DOM contract

Each editable is wrapped in
`<div id="inline-edit-<model>-<pk>-<name>">…</div>`. The wrapper
itself carries no layout class — HTMX swaps it via `outerHTML`, so
keeping it classless means the swap never toggles layout classes on
the target. The display-mode flex layout lives on an inner
`.editable-field-display` block; the edit-mode form is a direct
child. Nothing outside the wrapper should depend on its inner
structure.

## Display partial conventions

- Receive `value` (current value), `obj` (instance), `editable` (the
  spec). Treat any other context as optional — post-save re-renders
  don't get extras passed via `inline_edit(..., extra=...)`.
- Avoid inline `style=` / `onclick=`; use classes in `side_panel.css`
  and delegated handlers in `inline_edit.js`.
- An empty value should show a Dutch placeholder
  (`Niet ingevuld` / `Geen X opgegeven`) styled with
  `rvo-text--italic rvo-text--subtle`.

## Adding/registering a new editables module

1. Create `wies/core/inline_edit/editables/<model>.py`, defining an
   `EditableSet` subclass.
2. Import the class in
   `wies/core/inline_edit/editables/__init__.py` and add a
   `model_label → class` entry to `REGISTRY`. Explicit mapping: no
   metaclass magic, IDE "Find Usages" works, accidental deletion
   fails loudly.

## Common pitfalls

- **Forgetting to add the new EditableSet to `REGISTRY`** — the URL
  will 404.
- **Declaring a queryset directly instead of a callable** in
  `choices=` — evaluated at registration time (often before
  migrations).
- **Mutating model state outside `transaction.atomic()`** in a custom
  `save` — partial failures leave the DB inconsistent.
- **Inline `onclick` / `style` in a display partial** — re-rendered
  on every save; use `inline_edit.js` and `side_panel.css`.
- **Relying on extras passed to the Jinja global on the post-save
  re-render** — only the static partial context is available there.
- **Putting Editable lookups behind privacy filters in the view** —
  the generic view doesn't know your domain rules; use
  `object_permission` / per-field `permission`.

## Tests

Infrastructure tests live in `wies/core/tests/test_inline_edit.py`.
When adding a new editable:

- Smoke test verifying the field saves through the URL is enough for
  trivial cases.
- Custom `save`: assert the side effects (other-category isolation,
  audit writes).
- Custom `display`: assert the rendered output contains distinctive
  markup (including any wrapping `<a>` or structural elements —
  they're easy to miss in a port).
- `EditableGroup.clean`: cover the cross-field rejection path.
- `EditableCollection`: cover the diff-and-sync path; assert that row
  additions, removals, and edits all persist correctly.
