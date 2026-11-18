"""The change history of an opdracht, rendered as readable sentences."""

import logging

from django import forms
from django.shortcuts import get_object_or_404, render

from wies.core.editables import REGISTRY
from wies.core.editables.assignment import restricted_change_ids
from wies.core.inline_edit.base import (
    EditableCollection,
)
from wies.core.models import (
    Assignment,
    Event,
)
from wies.core.visibility_rules import (
    PRIVACY_BM,
    PRIVACY_OWN,
)

logger = logging.getLogger(__name__)


def assignment_events_partial(request, public_id):
    assignment = get_object_or_404(Assignment, public_id=public_id)
    events = list(
        Event.objects.filter(
            object_type="Assignment",
            object_id=assignment.id,
        )
        .select_related("user__colleague")
        .order_by("-timestamp")[:20]
    )
    events = [event for event in events if _attach_audit_render_data(event, assignment, request)]
    for event in events:
        _attach_audit_sentence(event)
    return render(request, "parts/assignment_events_timeline.html", {"events": events})


HET_FIELD_LABELS = {"team", "onderdeel"}


def _field_phrase(label: str) -> str:
    """Turns a field label into a sentence fragment: "Beschrijving" -> "de
    beschrijving", "Team" -> "het team". A label with an inner capital is a name,
    not a common noun ("Business Manager"), so its casing is left alone."""
    if not label or label == "een veld":
        return label or "een veld"
    noun = label[: -len("(s)")].strip() + "s" if label.endswith("(s)") else label
    # Judge the casing on the part outside any parenthetical, so "E-mail (ODI)"
    # is not read as a name because of the acronym.
    head = noun.split("(")[0]
    if not any(c.isupper() for c in head[1:]):
        noun = noun[0].lower() + noun[1:]
    article = "het" if noun.lower() in HET_FIELD_LABELS else "de"
    return f"{article} {noun}"


def _attach_audit_sentence(event) -> None:
    """Phrases the event as one running sentence, commit-message style.

    Long values (textareas) stay out of the sentence; the template renders them
    as Van/Naar blocks underneath. Requires ``_attach_audit_render_data`` to have
    run first, for render_kind, formatted_old/new and diff_entries.
    """
    colleague = getattr(event.user, "colleague", None) if event.user else None
    event.author_name = colleague.name if colleague else ""
    author = event.author_name or "Onbekende gebruiker"
    event.type_label = "Aangemaakt" if event.action == "create" else "Gewijzigd"
    if event.action == "create":
        event.sentence = f"{author} heeft deze opdracht aangemaakt."
        return
    if event.context.get("merge"):
        ids = event.context.get("merged_ids") or []
        noun = "dubbele opdracht" if len(ids) == 1 else "dubbele opdrachten"
        joined_ids = ", ".join(f"#{i}" for i in ids)
        event.sentence = f"{author} heeft {len(ids)} {noun} samengevoegd ({joined_ids})."
        return
    label = _field_phrase(event.context.get("field_label") or "een veld")
    if event.render_kind == "collection":
        clauses = [entry["text"] for entry in event.diff_entries or []]
        if not clauses:
            event.sentence = f"{author} heeft {label} gewijzigd."
        elif len(clauses) == 1:
            event.sentence = f"{author} heeft {clauses[0]}."
        else:
            event.sentence = f"{author} heeft {', '.join(clauses[:-1])} en {clauses[-1]}."
        return
    old, new = event.formatted_old, event.formatted_new
    if event.render_kind == "textarea":
        if not old and new:
            event.sentence = f"{author} heeft {label} toegevoegd."
        elif old and not new:
            event.sentence = f"{author} heeft {label} verwijderd."
        else:
            event.sentence = f"{author} heeft {label} gewijzigd."
        return
    if old and new:
        event.sentence = f'{author} heeft {label} van "{old}" naar "{new}" gewijzigd.'
    elif new:
        event.sentence = f'{author} heeft {label} naar "{new}" gewijzigd.'
    elif old:
        event.sentence = f"{author} heeft {label} leeggemaakt."
    else:
        event.sentence = f"{author} heeft {label} gewijzigd."


def _team_event_privacy_note(assignment, request, changes) -> str:
    """The note on one team row in the timeline, or "" when there is nothing to say.

    Only for a viewer who sees the row while others do not. Derived from the
    event's own colleagues, not from the current team rows: the change is a frozen
    snapshot, so the hidden placement it names may since have been deleted (no
    current row carries a note then), and an unrelated row's note must not label
    this event.
    """
    hidden = restricted_change_ids(assignment, changes)
    if not hidden:
        return ""
    viewer = getattr(request.user, "colleague", None)
    if viewer is not None and hidden == {viewer.id}:
        # The only hidden person the event names is the viewer themselves —
        # someone without the role only ever reaches this case (their filtered
        # list drops changes naming hidden others), and a placed Business Manager
        # gets the wording matching their own row.
        return PRIVACY_OWN
    return PRIVACY_BM


def _attach_audit_render_data(event, obj, request) -> bool:
    """Prepares ``event`` for the timeline. False means the viewer may see nothing
    of it and it must not be rendered at all."""
    event.render_kind = "text"
    event.diff_entries = None
    event.formatted_old = event.context.get("old_value")
    event.formatted_new = event.context.get("new_value")

    # Delete events are kept for the audit trail but never rendered here: a
    # deleted opdracht has no panel to open.
    if event.action != "update":
        return True
    model_label = event.object_type.lower()
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        return True
    spec = editable_set._editables.get(event.context.get("field_name", ""))
    if spec is None:
        return True

    if isinstance(spec, EditableCollection):
        event.render_kind = "collection"
        changes = event.context.get("changes", [])
        if spec.visible_changes is not None:
            try:
                visible = spec.visible_changes(obj, request, changes)
            except AttributeError, TypeError:
                # A legacy row shape the filter can't read is a row whose names
                # we can't clear, so show no rows rather than risk a leak.
                logger.warning(
                    "Audit visible_changes failed for collection Event id=%s field=%s; hiding its rows",
                    event.id,
                    event.context.get("field_name"),
                    exc_info=True,
                )
                return False
            if changes and not visible:
                return False
            # A viewer who sees more than an outsider (a Business Manager gets the unfiltered
            # list) should know this row is hidden from others. Team rows only:
            # other fields look the same to everyone.
            event.privacy_note = _team_event_privacy_note(obj, request, visible)
            changes = visible
        if spec.render_change is not None:
            try:
                event.diff_entries = [spec.render_change(c) for c in changes]
            except TypeError:
                logger.warning(
                    "Audit render_change failed for collection Event id=%s field=%s; falling back to raw context",
                    event.id,
                    event.context.get("field_name"),
                    exc_info=True,
                )
                event.diff_entries = None
        return True

    # A textarea gets the Van/Naar block, unless it is one row high: that is a
    # plain text field allowed to wrap, and "van X naar Y" reads better there.
    widget = getattr(spec, "widget", None)
    is_textarea = isinstance(widget, forms.Textarea) or (
        isinstance(widget, type) and issubclass(widget, forms.Textarea)
    )
    rows = getattr(widget, "attrs", {}).get("rows", 3) if not isinstance(widget, type) else 3
    if is_textarea and int(rows or 3) > 1:
        event.render_kind = "textarea"

    formatter = getattr(spec, "render_change", None) or (lambda v: str(v or ""))
    try:
        event.formatted_old = formatter(event.context.get("old_value"))
        event.formatted_new = formatter(event.context.get("new_value"))
    except TypeError:
        # A legacy event can hold a shape the current render_change no longer
        # accepts; fall back to the raw context values so the row still renders.
        logger.warning(
            "Audit render_change failed for Event id=%s field=%s; falling back to raw context",
            event.id,
            event.context.get("field_name"),
            exc_info=True,
        )
    return True
