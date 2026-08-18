"""Audit-event emission for Editables. See ``features/inline-editing.md``.

Turns a before/after snapshot of a spec into timeline events. Kept out of the
view layer so panels and full-page forms write identical events.
"""

from __future__ import annotations

from wies.core.inline_edit.base import Editable, EditableCollection, EditableGroup
from wies.core.services.events import create_event


def record_editable_change(editable, obj, object_type, old_value, new_value, user, request=None) -> None:
    to_state = editable.audit_state or (lambda v: v)
    old_state = to_state(old_value)
    new_state = to_state(new_value)
    if old_state == new_state:
        return
    create_event(
        object_type=object_type,
        action="update",
        source="user",
        object_id=obj.id,
        user=user,
        request=request,
        context={
            "field_name": editable.field or editable.name or "",
            "field_label": editable.label or editable.name or "",
            "old_value": old_state,
            "new_value": new_state,
        },
    )


def _diff_collection_state(old_state: list[dict], new_state: list[dict]) -> list[dict]:
    old_by_id = {r["id"]: r for r in old_state}
    new_by_id = {r["id"]: r for r in new_state}
    changes: list[dict] = [{"old": None, "new": r} for r in new_state if r["id"] not in old_by_id]
    changes.extend({"old": r, "new": None} for r in old_state if r["id"] not in new_by_id)
    changes.extend(
        {"old": old_by_id[sid], "new": new_by_id[sid]}
        for sid in old_by_id.keys() & new_by_id.keys()
        if old_by_id[sid] != new_by_id[sid]
    )
    return changes


def emit_inline_edit_audit_event(
    editable_set, spec, obj, before, after, user, *, child_editables=None, request=None
) -> None:
    object_type = editable_set.audit_type()
    if object_type is None:
        return

    if isinstance(spec, Editable):
        record_editable_change(spec, obj, object_type, before, after, user, request=request)
        return

    if isinstance(spec, EditableGroup):
        for child in child_editables or []:
            record_editable_change(
                child, obj, object_type, before.get(child.name), after.get(child.name), user, request=request
            )
        return

    if isinstance(spec, EditableCollection):
        if spec.audit_state is None:
            return
        changes = _diff_collection_state(before, after)
        if not changes:
            return
        create_event(
            object_type=object_type,
            action="update",
            source="user",
            object_id=obj.id,
            user=user,
            request=request,
            context={
                "field_name": spec.name or "",
                "field_label": spec.label or spec.name or "",
                "changes": changes,
            },
        )
