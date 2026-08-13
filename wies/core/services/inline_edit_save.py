"""Saving a list of editable specs with the same audit events as inline edit.

Shared by the child-sheet panels (placement, assignment) and the onboarding flow,
so saving outside the HTMX inline-edit route audits identically.
"""

from __future__ import annotations

from wies.core.inline_edit.audit import emit_inline_edit_audit_event
from wies.core.inline_edit.base import EditableGroup
from wies.core.inline_edit.forms import _current_value, resolve_editables, save_spec


def save_edit_specs(request, specs, cleaned_data) -> bool:
    """Saves all specs with the same audit events as inline edit.

    Opens no transaction of its own: the caller sets the boundary, so a panel can
    add its own follow-up work inside the same transaction.

    Returns True if any spec's value actually changed — the inline-edit view uses
    this to decide whether to announce a save (onboarding submits every field, so
    an untouched one must not report "opgeslagen").
    """
    changed = False
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
        changed = changed or (before != after)
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
    return changed
