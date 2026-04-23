"""Generic inline-edit endpoint. See ``features/inline-editing.md``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from wies.core.inline_edit.base import (
    Editable,
    EditableCollection,
    EditableGroup,
    EditableSet,
)
from wies.core.inline_edit.editables import REGISTRY
from wies.core.inline_edit.forms import (
    _current_value,
    build_form_class,
    resolve_editables,
)

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def _spec_label(editable_set: type[EditableSet], spec: Editable | EditableGroup | EditableCollection) -> str:
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


PERMISSION_DENIED_ALERT = {
    "kind": "warning",
    "message": "Je hebt geen rechten om dit veld te bewerken.",
}


def _permission_denied(
    editable_set: type[EditableSet],
    spec: Editable | EditableGroup,
    user,
    obj,
) -> dict | None:
    """Return the denial alert when either the set-level or spec-level gate blocks; None when allowed."""
    op = getattr(editable_set, "object_permission", None)
    if op is not None and not op(user, obj):
        return PERMISSION_DENIED_ALERT
    if spec.permission is not None and not spec.permission(user, obj):
        return PERMISSION_DENIED_ALERT
    return None


def _resolve_display(obj, spec, editables) -> dict:
    # Returns {"template": path} to include a partial or {"text": str} for plain rendering.
    if spec.display is None:
        if isinstance(spec, EditableCollection):
            # Collections without an explicit display fall back to a
            # newline-joined string of the initial row dicts — rarely
            # useful, so collections are expected to declare display.
            return {"text": str(spec.initial(obj))}
        if isinstance(spec, EditableGroup):
            # No explicit group display — render each member's value.
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


def _render_display(
    request: HttpRequest,
    editable_set,
    spec,
    editables,
    obj,
    *,
    alert: dict | None = None,
    user_can_edit: bool | None = None,
    saved: bool = False,
) -> HttpResponse:
    # `saved=True` triggers the pencil→check flash; `alert` carries a denial warning.
    model_label = editable_set.model._meta.model_name
    name = spec.name
    display = _resolve_display(obj, spec, editables)
    if isinstance(spec, EditableCollection):
        value = spec.initial(obj)
    elif isinstance(spec, Editable):
        value = _current_value(obj, spec)
    else:
        value = {e.field or e.name: _current_value(obj, e) for e in editables}
    ctx = {
        "target": f"inline-edit-{model_label}-{obj.pk}-{name}",
        "url": reverse("inline-edit", args=[model_label, obj.pk, name]),
        "label": _spec_label(editable_set, spec),
        "obj": obj,
        "editable": spec,
        "value": value,
        "display": display,
        "user_can_edit": (
            user_can_edit
            if user_can_edit is not None
            else _permission_denied(editable_set, spec, request.user, obj) is None
        ),
        "alert": alert,
        "saved": saved,
    }
    return render(request, "parts/inline_edit/display.html", ctx)


def _render_form(
    request: HttpRequest,
    editable_set,
    spec,
    editables,
    obj,
    form,
) -> HttpResponse:
    # Edit-mode partial: form + save/cancel. On validation failure, `form` carries inline errors.
    model_label = editable_set.model._meta.model_name
    name = spec.name
    ctx = {
        "target": f"inline-edit-{model_label}-{obj.pk}-{name}",
        "url": reverse("inline-edit", args=[model_label, obj.pk, name]),
        "label": _spec_label(editable_set, spec),
        "obj": obj,
        "editable": spec,
        "form": form,
    }
    return render(request, "parts/inline_edit/form.html", ctx)


def _render_collection_form(
    request: HttpRequest,
    editable_set,
    spec: EditableCollection,
    obj,
    formset,
) -> HttpResponse:
    # Inner body from spec.form_template; receives the formset as `formset`.
    model_label = editable_set.model._meta.model_name
    ctx = {
        "target": f"inline-edit-{model_label}-{obj.pk}-{spec.name}",
        "url": reverse("inline-edit", args=[model_label, obj.pk, spec.name]),
        "label": _spec_label(editable_set, spec),
        "obj": obj,
        "editable": spec,
        "formset": formset,
    }
    return render(request, "parts/inline_edit/collection_form.html", ctx)


def _attach_formset_error(formset, message: str) -> None:
    # FormSets lack a public API for this; _non_form_errors is the documented workaround
    # (is_valid() uses the same internal path when clean() raises).
    existing = list(formset.non_form_errors()) if hasattr(formset, "_non_form_errors") else []
    formset._non_form_errors = ErrorList([*existing, message])


def _handle_collection(request: HttpRequest, editable_set, spec: EditableCollection, obj) -> HttpResponse:
    # FormSet equivalent of the Editable/Group path in inline_edit_view.
    if request.method == "POST":
        formset = spec.formset_factory(data=request.POST)
        if formset.is_valid():
            try:
                spec.save(obj, formset)
            except ValidationError as exc:
                for message in exc.messages:
                    _attach_formset_error(formset, message)
                return _render_collection_form(request, editable_set, spec, obj, formset)
            return _render_display(request, editable_set, spec, editables=[], obj=obj, saved=True)
        return _render_collection_form(request, editable_set, spec, obj, formset)

    if request.GET.get("cancel"):
        return _render_display(request, editable_set, spec, editables=[], obj=obj)
    if request.GET.get("edit"):
        formset = spec.formset_factory(initial=spec.initial(obj))
        return _render_collection_form(request, editable_set, spec, obj, formset)
    return _render_display(request, editable_set, spec, editables=[], obj=obj)


def inline_edit_view(request, model_label, pk, name):
    """Generic HTMX endpoint. See ``features/inline-editing.md`` for the full contract."""
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        raise Http404("Unknown model")
    spec = editable_set._editables.get(name) or editable_set.resolve_dynamic(name)
    if spec is None:
        raise Http404("Unknown editable")

    obj = get_object_or_404(editable_set.model, pk=pk)

    # Permission ladder — denial always returns display partial with alert.
    denial = _permission_denied(editable_set, spec, request.user, obj)
    if denial:
        editables_for_display: list[Editable] = (
            [] if isinstance(spec, EditableCollection) else resolve_editables(editable_set, spec)
        )
        return _render_display(
            request,
            editable_set,
            spec,
            editables_for_display,
            obj,
            alert=denial,
            user_can_edit=False,
        )

    if isinstance(spec, EditableCollection):
        return _handle_collection(request, editable_set, spec, obj)

    editables = resolve_editables(editable_set, spec)

    # Import here to avoid circulars at module load time.
    from wies.core.inline_edit.forms import save_spec  # noqa: PLC0415

    if request.method == "POST":
        form_cls, _ = build_form_class(
            editables,
            obj=obj,
            group_clean=getattr(spec, "clean", None),
        )
        form = form_cls(request.POST)
        if form.is_valid():
            save_spec(spec, editables, form.cleaned_data, obj)
            return _render_display(
                request,
                editable_set,
                spec,
                editables,
                obj,
                saved=True,
            )
        return _render_form(request, editable_set, spec, editables, obj, form)

    if request.GET.get("cancel"):
        return _render_display(request, editable_set, spec, editables, obj)
    if request.GET.get("edit"):
        form_cls, initial = build_form_class(
            editables,
            obj=obj,
            group_clean=getattr(spec, "clean", None),
        )
        return _render_form(
            request,
            editable_set,
            spec,
            editables,
            obj,
            form_cls(initial=initial),
        )
    return _render_display(request, editable_set, spec, editables, obj)
