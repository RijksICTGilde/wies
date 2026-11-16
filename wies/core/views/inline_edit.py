"""Inline-edit view (generic HTMX endpoint).

See ``features/inline-editing.md`` for the full contract."""

import json
import logging
from contextlib import nullcontext

from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html

from wies.core.editables import REGISTRY
from wies.core.inline_edit.base import (
    Editable,
    EditableCollection,
    EditableGroup,
    EditableSet,
)
from wies.core.inline_edit.display import concurrency_token, edit_state, hash_state, resolve_display, spec_label
from wies.core.inline_edit.forms import (
    _current_value,
    build_form_class,
    resolve_editables,
)
from wies.core.permission_engine import Verb, has_permission
from wies.core.services.inline_edit_save import save_edit_specs

logger = logging.getLogger(__name__)


PERMISSION_DENIED_ALERT = {
    "kind": "warning",
    "message": "Je hebt geen rechten om dit veld te bewerken.",
}


CONCURRENCY_CONFLICT_ALERT = {
    "kind": "warning",
    "message": "Deze gegevens zijn ondertussen gewijzigd. "
    "Kies 'Opslaan' om je wijziging toch door te voeren, of 'Annuleren' om de gewijzigde gegevens over te nemen.",
}


CONFLICT_VALUE_MAX_LENGTH = 120


def _readable_current_value(obj, spec) -> str | None:
    """A short, human-readable form of a single field's current value, naming the
    concurrent change in the conflict warning. A group or collection has no single
    value, so this returns None and the caller uses the generic warning."""
    if not isinstance(spec, Editable):
        return None
    value = _current_value(obj, spec)
    # The audit timeline already renders this field for a human (the colleague's
    # name, not "Colleague object (3)"), so reuse that chain.
    if spec.audit_state:
        value = spec.audit_state(value)
    if spec.render_change:
        text = spec.render_change(value)
    elif isinstance(value, list):
        # A list on a scalar Editable is an M2M (e.g. labels); name the members.
        text = ", ".join(str(v) for v in value)
    else:
        text = "" if value is None else str(value)
    text = str(text).strip()
    if not text:
        return "geen"
    if len(text) > CONFLICT_VALUE_MAX_LENGTH:
        text = text[:CONFLICT_VALUE_MAX_LENGTH].rstrip() + "…"
    return text


def _concurrency_conflict_alert(editable_set, spec, obj) -> dict:
    """The conflict warning, naming the field and the concurrent value where one
    can be shown, so the user need not press Annuleren — losing their own input —
    just to find out what changed."""
    concurrent = _readable_current_value(obj, spec)
    if concurrent is None:
        return CONCURRENCY_CONFLICT_ALERT
    # The alert renders its message as HTML; ``format_html`` escapes both
    # interpolations, the value being user content.
    return {
        "kind": "warning",
        "message": format_html(
            "<strong>{}</strong> is ondertussen gewijzigd naar <strong>“{}”</strong>. "
            "Klik op 'Opslaan' om jouw wijziging alsnog door te voeren, "
            "of op 'Annuleren' om de wijziging over te nemen.",
            spec_label(editable_set, spec),
            concurrent,
        ),
    }


def _submitted_token(request) -> str:
    return request.POST.get("_concurrency_token", "")


def _has_concurrency_conflict(request, editable_set, spec, obj, *, state=None) -> bool:
    """Whether this POST was built on a stale view of ``obj``.

    Call inside the transaction holding the row lock, so the state read here is
    the state the save writes over. A missing token counts as a conflict: every
    form this endpoint renders carries one, so its absence means staleness cannot
    be established. ``state`` reuses a snapshot the caller already read.
    """
    submitted = _submitted_token(request)
    if not submitted:
        logger.warning(
            "Inline edit POST without a concurrency token; treated as a conflict (model=%s, editable=%s, pk=%s)",
            editable_set.model._meta.model_name,
            spec.name,
            obj.pk,
        )
        return True
    if state is None:
        state = edit_state(editable_set, spec, obj)
    return submitted != hash_state(state)


def _permission_denied(
    editable_set: type[EditableSet],
    spec: Editable | EditableGroup | EditableCollection,
    user,
    obj,
) -> dict | None:
    """Returns the denial alert when the user can't UPDATE this field, None when allowed.

    Lookup goes through the registry in ``wies.core.permissions``, where
    field-level rules win over the whole-object rule for the same model.
    """
    if not has_permission(Verb.UPDATE, obj, user, spec):
        return PERMISSION_DENIED_ALERT
    return None


def _inline_edit_base_ctx(editable_set, spec, obj) -> dict:
    # Shared context for display/form/collection-form renders — target id, URL, label, obj, spec.
    model_label = editable_set.model._meta.model_name
    return {
        "target": f"inline-edit-{model_label}-{obj.public_id}-{spec.name}",
        "edit_url": reverse("inline-edit", args=[model_label, obj.public_id, spec.name]),
        "label": spec_label(editable_set, spec),
        "obj": obj,
        "editable": spec,
    }


def _render_inline_edit_display(
    request,
    editable_set,
    spec,
    editables,
    obj,
    *,
    alert: dict | None = None,
    user_can_edit: bool | None = None,
    saved: bool = False,
) -> HttpResponse:
    # `saved=True` triggers the toast via HX-Trigger-After-Swap.
    # On denial, skip resolving the value: it can be heavy (the services
    # collection queries per row) and the partial handles an empty value fine.
    if alert is not None:
        display: dict = {"text": ""}
        value: object = None
    else:
        display = resolve_display(obj, spec, editables)
        if isinstance(spec, EditableCollection):
            value = spec.initial(obj)
        elif isinstance(spec, Editable):
            value = _current_value(obj, spec)
        else:
            value = {e.field or e.name: _current_value(obj, e) for e in editables}
    extra = {}
    display_context = getattr(spec, "display_context", None)
    if alert is None and display_context is not None:
        extra = display_context(obj, request)
    ctx = {
        **_inline_edit_base_ctx(editable_set, spec, obj),
        "value": value,
        "display": display,
        "user_can_edit": (
            user_can_edit if user_can_edit is not None else has_permission(Verb.UPDATE, obj, request.user, spec)
        ),
        "hide_edit_button": getattr(spec, "hide_edit_button", False),
        "alert": alert,
        **extra,
        # Lets display.html put `autofocus` on the pencil after a save: htmx
        # focuses the first [autofocus] element in swapped-in content, and
        # without it focus drops to <body> with the button that held it.
        # After **extra, so a spec's display_context cannot override the flag
        # and lose focus without anything reporting it.
        "saved": saved,
    }
    response = render(request, "parts/inline_edit/display.html", ctx)
    if saved:
        # The label travels along so the toast names what was saved; in the
        # onboarding wizard several fields are saved in a row. A missing label
        # falls back to the generic text.
        response["HX-Trigger-After-Swap"] = json.dumps(
            {"inline-edit-saved": {"label": getattr(spec, "label", None) or ""}}
        )
    return response


def _render_inline_edit_form(
    request, editable_set, spec, editables, obj, form, *, alert: dict | None = None, token: str | None = None
) -> HttpResponse:
    # form.html always owns the form element and the concurrency token; a group's
    # ``form_template`` only replaces the field body, so it cannot drop either.
    ctx = {
        **_inline_edit_base_ctx(editable_set, spec, obj),
        "form": form,
        "editable": spec,
        "concurrency_token": token if token is not None else concurrency_token(editable_set, spec, obj),
        "alert": alert,
    }
    return render(request, "parts/inline_edit/form.html", ctx)


def _handle_inline_edit_collection(request, editable_set, spec: EditableCollection, obj) -> HttpResponse:
    # Collections are read-only in the inline-edit engine: they render their
    # display, and their rows are edited through a dedicated flow (the team is
    # edited one member at a time via assignment_member_edit_view), not the
    # generic save path. A POST here is therefore never valid.
    if request.method == "POST":
        raise Http404("Collection is not editable")
    return _render_inline_edit_display(request, editable_set, spec, editables=[], obj=obj)


def _public_id_stub(model, public_id):
    """An unsaved instance carrying only ``public_id``, enough for the denial
    partial's target and edit_url. Lets a missing object render byte-identically
    to a forbidden one without a second DB round-trip."""
    stub = model()
    stub.public_id = public_id
    return stub


def _render_inline_edit_denial(request, editable_set, spec, public_id, obj=None, alert=None) -> HttpResponse:
    """The denial partial for an object the user may not edit or that is not there.
    Both render identically, so this endpoint can't be walked as an existence
    oracle over public_ids."""
    display_obj = obj if obj is not None else _public_id_stub(editable_set.model, public_id)
    editables_for_display: list[Editable] = (
        [] if isinstance(spec, EditableCollection) else resolve_editables(editable_set, spec)
    )
    return _render_inline_edit_display(
        request,
        editable_set,
        spec,
        editables_for_display,
        display_obj,
        alert=alert or PERMISSION_DENIED_ALERT,
        user_can_edit=False,
    )


def inline_edit_view(request, model_label, public_id, name):
    """Generic HTMX endpoint. See ``features/inline-editing.md`` for the full contract."""
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        raise Http404("Unknown model")
    spec = editable_set._editables.get(name) or editable_set.resolve_dynamic(name)
    if spec is None:
        raise Http404("Unknown editable")

    obj = editable_set.model.objects.filter(public_id=public_id).first()

    # A missing object and a forbidden one return the same denial partial, so
    # this endpoint can't be walked as an existence oracle.
    denial = _permission_denied(editable_set, spec, request.user, obj) if obj is not None else PERMISSION_DENIED_ALERT
    if denial:
        return _render_inline_edit_denial(request, editable_set, spec, public_id, obj=obj, alert=denial)

    if isinstance(spec, EditableCollection):
        return _handle_inline_edit_collection(request, editable_set, spec, obj)

    editables = resolve_editables(editable_set, spec)

    if request.method == "POST":
        form_cls, _ = build_form_class(
            editables,
            obj=obj,
            group_clean=getattr(spec, "clean", None),
        )
        form = form_cls(request.POST)
        if form.is_valid():
            conflict = False
            saved = False
            try:
                with transaction.atomic():
                    obj = editable_set.model.objects.select_for_update().get(pk=obj.pk)
                    conflict = _has_concurrency_conflict(request, editable_set, spec, obj)
                    if not conflict:
                        # Same save + audit as every other edit path, wrapped in the
                        # set's audit_mirror like save_placement_edit does.
                        mirror = editable_set.audit_mirror
                        with mirror(obj, request.user, request) if mirror else nullcontext():
                            saved = save_edit_specs(request, [(editable_set, spec, obj)], form.cleaned_data)
            except editable_set.model.DoesNotExist:
                # Deleted between the permission check and the lock; the same
                # denial partial keeps this indistinguishable from a 404 or 403.
                return _render_inline_edit_denial(request, editable_set, spec, public_id)
            if conflict:
                # Re-render the bound form, keeping the user's input: Opslaan
                # saves anyway, Annuleren adopts the changed data.
                return _render_inline_edit_form(
                    request,
                    editable_set,
                    spec,
                    editables,
                    obj,
                    form,
                    alert=_concurrency_conflict_alert(editable_set, spec, obj),
                )
            return _render_inline_edit_display(
                request,
                editable_set,
                spec,
                editables,
                obj,
                # The onboarding wizard submits every field on "Volgende", so an
                # untouched one would announce a save that did not happen.
                saved=saved,
            )
        # Keep the token this POST was built on: recomputing it would adopt a
        # change made meanwhile, and the corrected resubmit would overwrite it
        # without ever showing the conflict warning.
        return _render_inline_edit_form(
            request, editable_set, spec, editables, obj, form, token=_submitted_token(request)
        )

    if request.GET.get("cancel"):
        return _render_inline_edit_display(request, editable_set, spec, editables, obj)
    if request.GET.get("edit"):
        form_cls, initial = build_form_class(
            editables,
            obj=obj,
            group_clean=getattr(spec, "clean", None),
        )
        return _render_inline_edit_form(
            request,
            editable_set,
            spec,
            editables,
            obj,
            form_cls(initial=initial),
        )
    return _render_inline_edit_display(request, editable_set, spec, editables, obj)
