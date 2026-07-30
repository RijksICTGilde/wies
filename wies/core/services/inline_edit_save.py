"""Sla een lijst editable-specs op met dezelfde audit-events als inline edit.

Gedeeld door de child-sheet-panelen (plaatsing, opdracht) en de
onboarding-flow, zodat opslaan buiten de HTMX-inline-edit-route byte-identiek
audit-gedrag houdt.
"""

from __future__ import annotations

from wies.core.inline_edit.audit import emit_inline_edit_audit_event
from wies.core.inline_edit.base import EditableGroup
from wies.core.inline_edit.forms import _current_value, resolve_editables, save_spec


def save_edit_specs(request, specs, cleaned_data):
    """Sla alle specs op met dezelfde audit-events als inline edit.

    Geen eigen transactie: de aanroeper bepaalt de grens, zodat een paneel er
    zijn eigen nazorg (zoals de plaatsingsspiegel) in dezelfde transactie bij
    kan leggen.
    """
    for editable_set, spec, obj in specs:
        spec_editables = resolve_editables(editable_set, spec)
        if isinstance(spec, EditableGroup):
            before = {e.name: _current_value(obj, e) for e in spec_editables}
        else:
            before = _current_value(obj, spec)
        save_spec(spec, spec_editables, cleaned_data, obj)
        if isinstance(spec, EditableGroup):
            after = {e.name: _current_value(obj, e) for e in spec_editables}
        else:
            after = _current_value(obj, spec)
        emit_inline_edit_audit_event(
            editable_set,
            spec,
            obj,
            before,
            after,
            request.user,
            child_editables=spec_editables if isinstance(spec, EditableGroup) else None,
            request=request,
        )
