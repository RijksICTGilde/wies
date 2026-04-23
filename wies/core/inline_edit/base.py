"""Core abstractions for the inline-edit system.

Editable, EditableGroup, EditableCollection, EditableSet — see
``features/inline-editing.md``.
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
    permission: Callable[[Any, Model], bool] | None = None
    save: Callable[[Model, Any], None] | None = None

    # For unbound editables (no 1:1 model field). `form_field` takes
    # priority over field inference; `initial` reads the current value.
    form_field: forms.Field | Callable[[], forms.Field] | None = None
    initial: Callable[[Model], Any] | None = None

    # Set by EditableSet.__init_subclass__ — the attribute name on the set.
    # Identifier used in URLs / registry keys / DOM target ids.
    name: str | None = None


@dataclass
class EditableGroup:
    """Multiple editables edited together as one subform."""

    label: str
    fields: list[str | Editable]
    display: str | Callable[[Model], Any] | None = None
    clean: Callable[[dict], dict] | None = None
    permission: Callable[[Any, Model], bool] | None = None
    # Group-level save; takes the whole cleaned_data dict. Use when
    # several fields must persist atomically.
    save: Callable[[Model, dict], None] | None = None
    name: str | None = None


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
    permission: Callable[[Any, Model], bool] | None = None
    name: str | None = None


class EditableSet:
    """Per-model declaration. Subclass, declare Editables as class attrs.

    Registration into the runtime lookup lives in
    ``wies.core.inline_edit.editables.REGISTRY`` (explicit, not via a
    metaclass hook).
    """

    model: type[Model]
    object_permission: Callable[[Any, Model], bool] | None = None

    _editables: dict[str, Editable | EditableGroup]

    @classmethod
    def resolve_dynamic(cls, name: str) -> Editable | EditableGroup | EditableCollection | None:
        """Build an Editable at request time for a name not in the static set.

        Default: no dynamic editables. Override for DB-driven per-row cases.
        """
        return None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "model") or cls.model is None:
            return
        cls._editables = {}
        for attr_name, attr in list(vars(cls).items()):
            if isinstance(attr, Editable):
                # `form_field` signals an unbound editable — skip model/field binding.
                if attr.form_field is None:
                    if attr.model is None:
                        attr.model = cls.model
                    if attr.field is None:
                        attr.field = attr_name
                attr.name = attr_name
                cls._editables[attr_name] = attr
            elif isinstance(attr, EditableGroup | EditableCollection):
                attr.name = attr_name
                cls._editables[attr_name] = attr
