"""Display helpers for inline edit: labels, rendered values and the concurrency token.

Shared by the inline-edit view and the ``inline_edit()`` Jinja global, so they
live in the engine rather than in the view layer."""

import hashlib
import json

from django.db.models import Model

from wies.core.inline_edit.base import (
    Editable,
    EditableCollection,
    EditableGroup,
    EditableSet,
)
from wies.core.inline_edit.forms import _current_value, resolve_editables


def spec_label(editable_set: type[EditableSet], spec: Editable | EditableGroup | EditableCollection) -> str:
    # Editable: explicit label → model field's verbose_name → attr name. Groups/Collections always carry a label.
    if isinstance(spec, EditableGroup | EditableCollection):
        return spec.label
    if spec.label:
        return spec.label
    if spec.model is not None and spec.field is not None:
        try:
            return spec.model._meta.get_field(spec.field).verbose_name
        except Exception:  # noqa: BLE001
            return spec.name or spec.field or ""
    return spec.name or ""


def edit_state(editable_set, spec, obj):
    """The values this edit is based on, in a JSON-serialisable shape.

    Only Editable/EditableGroup specs reach this: collections are read-only in
    the inline-edit engine and have no save path to guard with a token.
    """
    state = {}
    for e in resolve_editables(editable_set, spec):
        value = _current_value(obj, e)
        if isinstance(value, list):
            # Rows carry their own shape (dicts for organizations, models for
            # M2M), so let audit_state flatten them where it exists rather than
            # leaning on repr. Order-independent either way.
            value = e.audit_state(value) if e.audit_state else sorted(str(getattr(i, "pk", i)) for i in value)
        elif isinstance(value, Model):
            value = value.pk
        state[e.field or e.name] = value
    return state


def hash_state(state) -> str:
    payload = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def concurrency_token(editable_set, spec, obj) -> str:
    """A short hash of the values this edit is based on, embedded in the form and
    re-checked under a row lock at save time. Differing tokens mean the values
    changed since rendering, and the save is rejected instead of overwriting."""
    return hash_state(edit_state(editable_set, spec, obj))


def resolve_display(obj, spec, editables) -> dict:
    # Returns {"template": path} to include a partial or {"text": str} for plain rendering.
    if spec.display is None:
        if isinstance(spec, EditableCollection):
            # Rarely useful, so a collection is expected to declare a display.
            return {"text": str(spec.initial(obj))}
        if isinstance(spec, EditableGroup):
            parts = []
            for e in editables:
                v = _current_value(obj, e)
                parts.append("" if v is None else str(v))
            return {"text": " · ".join(p for p in parts if p)}
        value = _current_value(obj, spec)
        return {"text": "" if value is None else str(value)}

    if callable(spec.display):
        return {"text": str(spec.display(obj))}

    if isinstance(spec.display, str) and spec.display.endswith(".html"):
        return {"template": spec.display}
    return {"text": str(spec.display)}
