"""Core abstractions for the inline-edit system.

Editable, EditableGroup, EditableCollection, EditableSet — see
``features/inline-editing.md``.

Permissions are NOT declared on Editables; they live in
``wies/core/permission_rules.py`` and are looked up by the engine in
``wies/core/permissions.py``.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from django import forms
    from django.db.models import Model


@dataclass
class Editable:
    """One editable field. Missing metadata auto-fills from the bound model field."""

    # Binding (set by EditableSet.__init_subclass__).
    model: type[Model] | None = None
    field: str | None = None

    label: str | None = None
    help_text: str | None = None
    required: bool | None = None
    widget: forms.Widget | type[forms.Widget] | None = None
    choices: Iterable | Callable[[], Iterable] | None = None
    validators: list[Callable] = dataclasses.field(default_factory=list)
    error_messages: dict[str, str] = dataclasses.field(default_factory=dict)
    empty_label: str | None = None  # ModelChoiceField only.

    display: str | Callable[[Model], Any] | None = None
    save: Callable[[Model, Any], None] | None = None

    # Extra context merged into the display partial on EVERY render path
    # (initial panel render, inline-edit save, inline-edit cancel).
    # Signature ``(obj, request) -> dict``. Use for values the partial needs
    # but that aren't derivable from ``value`` alone — e.g. a navigation URL
    # that must survive an edit/cancel round-trip (#395).
    display_context: Callable[[Model, Any], dict] | None = None

    # For unbound editables (no 1:1 model field). `form_field_factory`
    # takes priority over field inference; `initial` reads the current value.
    form_field_factory: forms.Field | Callable[[], forms.Field] | None = None
    initial: Callable[[Model], Any] | None = None

    # Convert the field's raw value to a snapshot stored as the event's
    # ``old_value`` / ``new_value``. Required when the raw value isn't
    # encodable by ``DjangoJSONEncoder`` (e.g. a model instance).
    audit_state: Callable[[Any], Any] | None = None
    # Build the display string shown in the audit log UI for this
    # field's audit value. Default: ``str(value or "")``.
    render_change: Callable[[Any], str] | None = None

    # Set by EditableSet.__init_subclass__ — the attribute name on the set.
    # Identifier used in URLs / registry keys / DOM target ids.
    name: str | None = None

    def form_field(self) -> forms.Field:
        """Return a Django Field built from this Editable's config.

        Used both inside the inline-edit engine and by full-page forms
        that want to reference editable-derived fields directly:

            class MyForm(forms.Form):
                name = MyEditables.name.form_field()
        """
        # Imported inside the method to avoid pulling form modules at import time.
        from wies.core.inline_edit.forms import _build_form_field  # noqa: PLC0415

        return _build_form_field(self)


@dataclass
class EditableGroup:
    """Multiple editables edited together as one subform."""

    label: str
    fields: list[str | Editable]
    display: str | Callable[[Model], Any] | None = None
    clean: Callable[[dict], dict] | None = None
    # Group-level save; takes the whole cleaned_data dict. Use when
    # several fields must persist atomically.
    save: Callable[[Model, dict], None] | None = None
    # Custom form body template (path relative to jinja2 roots). When set,
    # the view renders this template instead of the generic form.html.
    # Template receives the same context as form.html plus ``editable`` (the group).
    form_template: str | None = None
    name: str | None = None
    # Set by EditableSet.__init_subclass__ — the model owning this group.
    # Required so the group can be used as a permission-rule key.
    model: type[Model] | None = None


@dataclass
class EditableCollection:
    """N rows of a child object owned by the parent (e.g. services on an assignment).

    The three callables bridge a Django FormSet to the parent:

    - ``formset_factory(data=None, initial=None)`` → formset instance.
    - ``initial(obj)`` → list of row dicts (prefills formset + feeds display).
    - ``save(obj, formset)`` → persist the validated formset (diff-and-sync).
      May raise ``ValidationError`` for stale/tampered rows.
    """

    label: str
    formset_factory: Callable[..., Any]
    initial: Callable[[Model], list[dict]]
    save: Callable[[Model, Any], None]
    # Body template included inside collection_form.html; receives the
    # formset as ``formset``.
    form_template: str | None = None
    display: str | Callable[[Model], Any] | None = None
    # Same contract as ``Editable.display_context``; may override ``value`` so
    # the display can filter what ``initial`` returns (e.g. per viewer).
    display_context: Callable[[Model, Any], dict] | None = None
    # Snapshot of the collection state — rows keyed by ``id``, each
    # encodable by ``DjangoJSONEncoder``. Required to opt this
    # collection into audit events.
    audit_state: Callable[[Model], list[dict]] | None = None
    # Render one ``{"old": row|None, "new": row|None}`` change as a
    # bullet line in the audit log UI, optionally with an inline
    # Van/Naar block under the bullet for long values.
    render_change: Callable[[dict], dict] | None = None
    # Suppress the auto-rendered pencil + clickable-value wrapper on the
    # display partial. Use when the parent template provides its own
    # edit trigger (e.g. the "Team bewerken" button).
    hide_edit_button: bool = False
    name: str | None = None
    # Set by EditableSet.__init_subclass__ — the model owning this collection.
    model: type[Model] | None = None


class EditableSet:
    """Per-model declaration. Subclass and declare Editables as class attrs::

        class FooEditables(EditableSet):
            class Meta:
                model = Foo

            name = Editable(...)
            description = Editable(...)

    Permission rules for these fields live in
    ``wies/core/permission_rules.py``, registered via
    ``@rule(UPDATE, FooEditables.description)``.

    Registration into the runtime lookup lives in
    ``wies.core.editables.REGISTRY`` (explicit, not via a
    metaclass hook).
    """

    _editables: dict[str, Editable | EditableGroup | EditableCollection]
    model: type[Model]  # Resolved from `Meta.model` by __init_subclass__.

    @classmethod
    def resolve_dynamic(cls, name: str) -> Editable | EditableGroup | EditableCollection | None:
        """Build an Editable at request time for a name not in the static set.

        Default: no dynamic editables. Override for DB-driven per-row cases.
        """
        return None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Subclasses without `Meta.model` are abstract bases — nothing to bind.
        meta = getattr(cls, "Meta", None)
        model = getattr(meta, "model", None)
        if model is None:
            return

        cls.model = model
        cls._editables = {
            name: cls._bind(attr, name, model)
            for name, attr in vars(cls).items()
            if isinstance(attr, (Editable, EditableGroup, EditableCollection))
        }

    @staticmethod
    def _bind(
        attr: Editable | EditableGroup | EditableCollection,
        name: str,
        model: type[Model],
    ) -> Editable | EditableGroup | EditableCollection:
        """Backfill metadata on a declared editable so the engine can resolve it later."""
        attr.name = name
        if attr.model is None:
            attr.model = model
        # Plain Editables default to a model field of the same name.
        # `form_field_factory` opts out: it lets an Editable supply its own form field when
        # there's no 1:1 model field to bind to (e.g. composite values like
        # `Assignment.organizations`, which is served by a custom OrganizationsField).
        if isinstance(attr, Editable) and attr.field is None and attr.form_field_factory is None:
            attr.field = name
        return attr
