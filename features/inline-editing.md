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
wies/core/
├── views.py                 # all views, including the generic inline_edit_view
├── inline_edit/
│   ├── base.py              # Editable, EditableGroup, EditableCollection, EditableSet
│   ├── forms.py             # build_form_class, save_*
│   └── jinja.py             # inline_edit(obj, name) Jinja global
├── editables/
│   ├── __init__.py          # REGISTRY dict — explicit model_label → EditableSet mapping
│   ├── assignment.py
│   ├── colleague.py         # dynamic labels_<id> via resolve_dynamic
│   ├── placement.py
│   ├── service.py
│   └── user.py
├── permission_engine.py     # Verb, has_permission, @rule
└── permissions.py           # all row-level @rule(...) declarations

wies/core/jinja2/
├── parts/inline_edit/       # display.html, form.html, collection_form.html
└── rvo/forms/displays/      # per-field display partials (textarea.html, etc.)
```

## Adding an inline-editable field

### 1. Trivial: just a model field

```python
class AssignmentEditables(EditableSet):
    class Meta:
        model = Assignment

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
    display="rvo/forms/displays/assignment_owner.html",
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
    clean=_validate_period,         # cross-field validator
    display="rvo/forms/displays/assignment_period.html",
)
```

One URL, one form with both inputs, one cross-field `clean`. The
display partial's `value` is `{"start_date": ..., "end_date": ...}`.

A group may also set `form_template` to lay its fields out itself
(see `PlacementEditables.period`). That template is a **body**: it is
included by `form.html`, which owns the `<form>` element, the
concurrency token, the non-field errors, the alert and the buttons. So
render form fields only — no `<form>`, no save/cancel buttons. Anything
the body needs on the form element (data attributes for JS, say) goes
on a container `<div>` inside the body instead.

### 7. Field that doesn't map 1:1 to a model attribute

```python
organizations = Editable(
    label="Opdrachtgever(s)",
    form_field_factory=lambda: OrganizationsField(required=True),
    initial=_organizations_initial,   # (obj) -> current value
    save=_save_organizations,         # (obj, value) -> persist
    display="rvo/forms/displays/organizations.html",
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
    display="rvo/forms/displays/assignment_services.html",
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
    class Meta:
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

Row-level authorization is its own subsystem
(`wies/core/permission_engine.py` + `wies/core/permissions.py`) used by
the inline-edit view and full-page forms alike. Class-level access
(LIST overview pages, CREATE-new pages) stays on Django's
`@permission_required` / `@login_required` decorators with group
permissions in `setup_roles()` — not duplicated here.

### Engine

```python
from wies.core.permission_engine import Verb, has_permission, rule

# Lookup
has_permission(verb, obj, user, field=None) -> bool
```

- `obj` is a model **instance** for row-level checks.
- `field` is an `Editable` / `EditableGroup` / `EditableCollection`
  instance for field-level narrowing (optional, positional or keyword).
- `verb` may be a `Verb` enum member or a list/tuple of them
  (OR-composition).
- Returns `False` for anonymous users.
- Returns `True` for `is_superuser` users — single god-mode short-circuit;
  rule bodies never repeat it.
- Lookup order: `(verb, model, field.name)` → `(verb, model, None)`.
  Field rules override the whole-object rule for the same model.
- Verbs available: `READ`, `UPDATE`, `DELETE`. Class-level access (LIST
  overviews, CREATE-new pages) stays on Django's group permissions and
  `@permission_required` decorators — those operate on the model class,
  not on rows, so they live outside this engine.

### Registering rules

All rules live in `wies/core/permissions.py`, imported in
`CoreConfig.ready()` so registrations happen at startup.

```python
from wies.core.editables import AssignmentEditables
from wies.core.models import Assignment, Placement
from wies.core.permission_engine import Verb, has_permission, rule

UPDATE = Verb.UPDATE


@rule(UPDATE, Assignment)                              # whole-object
def update_assignment(user, a):
    return _is_wies_sourced(a) and (_has_change_perm(user, a) or _is_assignment_owner(user, a))


@rule(UPDATE, Placement)                               # delegate to parent
def update_placement(user, p):
    return has_permission(UPDATE, p.service.assignment, user)


@rule(UPDATE, AssignmentEditables.extra_info)          # field-level: more permissive
def update_assignment_extra_info(user, a):
    if not _is_wies_sourced(a):
        return False
    return has_permission(UPDATE, a, user) or _is_placed_on_assignment(user, a)


@rule(UPDATE, UserEditables.email)                     # field-level: stricter
def update_user_email(user, target):
    return _has_change_perm(user, target)              # admin-only, no self-edit branch
```

Predicates (`_is_wies_sourced`, `_has_change_perm`,
`_is_assignment_owner`, …) are private helpers in the same file. Rule
bodies are plain Python returning `bool` — no DSL, no operator
overloading.

### Calling `has_permission`

```python
# Generic inline-edit view (already wired)
if not has_permission(Verb.UPDATE, obj, request.user, spec):
    return _permission_denied(...)

# Regular Django view
def assignment_panel(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    return render(..., {"user_can_edit": has_permission(Verb.UPDATE, assignment, request.user)})

# Jinja template (`has_permission`, `Verb`, and each EditableSet are
# registered as Jinja globals in config/jinja2.py)
{% if has_permission(Verb.UPDATE, assignment, user, AssignmentEditables.extra_info) %}
  <pencil />
{% endif %}
```

Denial in the inline-edit view returns the display partial with a
warning alert and no pencil. The registry is the only place
authorization is declared — Editables describe rendering, the rule
file describes who's allowed.

### Out of scope for this engine

- **Class-level access** (LIST overviews, CREATE-new) lives on
  Django's `@permission_required` / `setup_roles()`.
- **Row-level filtering for LIST** ("which assignments can I see?") is
  a queryset question — model managers handle it.
- **Parent-bound CREATE** ("create Placement on _this_ Service") would
  need a `parent=` kwarg on the engine. The flow doesn't exist yet —
  team edits go through the assignment's `services` field-level
  UPDATE.

## Reusing an editable in a full-page form

Plain `forms.Form` body — call `form_field()` per editable:

```python
class AssignmentCreateForm(RvoFormMixin, forms.Form):
    name = AssignmentEditables.name.form_field()
    extra_info = AssignmentEditables.extra_info.form_field()
    start_date = AssignmentEditables.start_date.form_field()
    end_date = AssignmentEditables.end_date.form_field()
    owner = AssignmentEditables.owner.form_field()
    organizations = AssignmentEditables.organizations.form_field()

    def clean(self):
        cleaned = super().clean()
        # cross-field checks here (e.g. end >= start)
        return cleaned
```

Field config (widget, choices, validators, error messages) flows from
the editable. Cross-field validation that mirrors an `EditableGroup`
clean lives in the form's `clean()` method.

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

1. Create `wies/core/editables/<model>.py`, defining an
   `EditableSet` subclass with a `class Meta: model = ...`.
2. Import the class in `wies/core/editables/__init__.py` and add a
   `model_label → class` entry to `REGISTRY`. Explicit mapping: no
   metaclass magic, IDE "Find Usages" works, accidental deletion
   fails loudly.
3. Add per-row rules in `wies/core/permissions.py` if any field
   needs row-level authorization beyond the model-level rule.

## Concurrent edits

Every edit form embeds a `_concurrency_token`: a hash of the values the
form was rendered from. On save the view re-reads the object under
`select_for_update()` and recomputes the token. If it differs, someone
changed the data in the meantime, so instead of overwriting, the bound
form comes back with a warning and a token for the new state — Opslaan
then saves anyway, Annuleren shows the changed data.

For a single `Editable` whose value is text, the warning names the value
that is stored now (`_concurrency_conflict_alert`), so the user can see
what Opslaan would overwrite. A group, a collection or a non-text value
(dates, related objects, lists) keeps the generic message: each would
need its own formatting to read well.

The token is rendered by `form.html` / `collection_form.html`, never by
a custom body, so a new editable cannot forget it. A POST without a
token cannot be checked and therefore counts as a conflict (and is
logged); the returned form carries a fresh token, so a retry succeeds.

A submit that fails validation never reaches the check, so that
re-render keeps the token it was posted with rather than a fresh one —
otherwise correcting the input would adopt whatever changed in the
meantime and overwrite it unwarned. The object can also be deleted
between the permission check and the lock; that renders the same denial
partial as a missing or forbidden object.

Two consequences when extending the engine:

- An `EditableCollection` needs an `audit_state` — it is the collection's
  state snapshot. Without one there is nothing to hash and
  `_concurrency_token` raises `ImproperlyConfigured`.
- Tests that POST to the endpoint must fetch the form first. Use
  `post_inline_edit` from `wies/core/tests/inline_edit_helpers.py`.

The lock is taken on the object being edited, so two edits of the _same_
object serialize. Edits of _different_ objects do not, even when they
write the same rows: `AssignmentEditables.services` rewrites the
placements of its assignment, while a period edit via the profile locks
only that `Placement`. A team save can therefore still pass its check and
then overwrite a placement edit that commits in between. The window is
narrow and both writers go through a lock, but it is not closed.

## Audit events

An `EditableSet` records audit events only when it sets
`audit_events = True`:

```python
class AssignmentEditables(EditableSet):
    audit_events = True
```

The event's `object_type` is the model's class name, and it is persisted
on every event written, so renaming the model orphans the events already
stored under the old name — migrate them along with the rename.

Today `AssignmentEditables` and `UserEditables` set `audit_events`.
Colleague, Service and Placement edits are not recorded under their own
type — Placement instead mirrors onto its assignment, see below.

## Mirroring an edit onto another object's timeline

An `EditableSet` may declare `audit_mirror`, an `(obj, user)` context
manager wrapped around the save and its audit event:

```python
class PlacementEditables(EditableSet):
    audit_mirror = staticmethod(_mirror_edit_onto_assignment)
```

`PlacementEditables` uses it to record a placement edit as a "Team"
event on the parent assignment, since a placement has no audit type of
its own. Put such model-specific behaviour here rather than in the
generic view.

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
- **Putting domain access checks inline in the view** — the generic
  view delegates to `has_permission` against the rule registry; add
  rules in `permissions.py` rather than touching the view.

## Tests

Infrastructure tests live in `wies/core/tests/test_inline_edit.py`;
permission engine + per-rule tests in `wies/core/tests/test_permissions.py`.
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
- New rules: add a unit test in `test_permissions.py` covering the
  allow + deny branches.
