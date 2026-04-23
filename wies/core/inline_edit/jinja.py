"""Jinja global: ``{{ inline_edit(obj, name) }}``. Registered in ``config/jinja2.py``."""

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from jinja2 import pass_context

from wies.core.inline_edit.base import Editable, EditableCollection
from wies.core.inline_edit.editables import REGISTRY
from wies.core.inline_edit.forms import _current_value, resolve_editables
from wies.core.inline_edit.views import (
    _permission_denied,
    _resolve_display,
    _spec_label,
)


@pass_context
def inline_edit(ctx, obj, name, **extras):
    """Render the display partial for ``obj.<name>``.

    ``**extras`` merge into the partial context. The post-save re-render
    does NOT carry them — design partials to degrade gracefully.
    """
    if obj is None:
        return mark_safe("")

    # obj._meta (not type(obj)._meta) — request.user is a SimpleLazyObject wrapper
    # whose class has no _meta; instance attribute access resolves through the wrapper.
    model_label = obj._meta.model_name
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        raise RuntimeError(
            f"No EditableSet registered for model '{model_label}'. Add it to wies.core.inline_edit.editables.REGISTRY."
        )

    spec = editable_set._editables.get(name) or editable_set.resolve_dynamic(name)
    if spec is None:
        raise RuntimeError(f"No editable '{name}' registered on {editable_set.__name__} (for model '{model_label}').")

    request = ctx.get("request")
    user = getattr(request, "user", None)
    is_collection = isinstance(spec, EditableCollection)
    editables = [] if is_collection else resolve_editables(editable_set, spec)

    user_can_edit = user is not None and _permission_denied(editable_set, spec, user, obj) is None

    display = _resolve_display(obj, spec, editables)
    if is_collection:
        value = spec.initial(obj)
    elif isinstance(spec, Editable):
        value = _current_value(obj, spec)
    else:
        value = {e.field or e.name: _current_value(obj, e) for e in editables}
    render_ctx = {
        "target": f"inline-edit-{model_label}-{obj.pk}-{name}",
        "url": reverse("inline-edit", args=[model_label, obj.pk, name]),
        "label": _spec_label(editable_set, spec),
        "obj": obj,
        "editable": spec,
        "value": value,
        "display": display,
        "user_can_edit": user_can_edit,
        "alert": None,
        "saved": False,
        **extras,
    }
    # Trusted template; any user-supplied values go through Jinja's auto-escape.
    html = render_to_string("parts/inline_edit/display.html", render_ctx, request=request)
    return mark_safe(html)  # noqa: S308
