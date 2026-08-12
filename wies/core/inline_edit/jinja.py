"""Jinja globals ``inline_edit`` and ``inline_edit_form``, registered in ``config/jinja2.py``."""

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from jinja2 import pass_context

from wies.core.editables import REGISTRY
from wies.core.inline_edit.base import Editable, EditableCollection
from wies.core.inline_edit.forms import _current_value, build_form_class, resolve_editables
from wies.core.permission_engine import Verb, has_permission
from wies.core.views import _concurrency_token, _resolve_display, _spec_label


@pass_context
def inline_edit(ctx, obj, name, **extras):
    """Renders the display partial for ``obj.<name>``.

    ``**extras`` merge into the partial context, but the post-save re-render does
    not carry them, so partials must degrade gracefully without them.
    """
    if obj is None:
        return mark_safe("")

    # obj._meta (not type(obj)._meta) — request.user is a SimpleLazyObject wrapper
    # whose class has no _meta; instance attribute access resolves through the wrapper.
    model_label = obj._meta.model_name
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        raise RuntimeError(
            f"No EditableSet registered for model '{model_label}'. Add it to wies.core.editables.REGISTRY."
        )

    spec = editable_set._editables.get(name) or editable_set.resolve_dynamic(name)
    if spec is None:
        raise RuntimeError(f"No editable '{name}' registered on {editable_set.__name__} (for model '{model_label}').")

    request = ctx.get("request")
    user = getattr(request, "user", None)
    is_collection = isinstance(spec, EditableCollection)
    editables = [] if is_collection else resolve_editables(editable_set, spec)

    user_can_edit = has_permission(Verb.UPDATE, obj, user, spec)

    display = _resolve_display(obj, spec, editables)
    if is_collection:
        value = spec.initial(obj)
    elif isinstance(spec, Editable):
        value = _current_value(obj, spec)
    else:
        value = {e.field or e.name: _current_value(obj, e) for e in editables}
    render_ctx = {
        "target": f"inline-edit-{model_label}-{obj.public_id}-{name}",
        "edit_url": reverse("inline-edit", args=[model_label, obj.public_id, name]),
        "label": _spec_label(editable_set, spec),
        "obj": obj,
        "editable": spec,
        "value": value,
        "display": display,
        "user_can_edit": user_can_edit,
        "hide_edit_button": getattr(spec, "hide_edit_button", False),
        "alert": None,
        "saved": False,
        # display_context fires here and in _render_inline_edit_display, so the
        # partial renders the same on first load and after an edit/cancel (#395).
        **(spec.display_context(obj, request) if getattr(spec, "display_context", None) else {}),
        **extras,
    }
    # Trusted template; any user-supplied values go through Jinja's auto-escape.
    html = render_to_string("parts/inline_edit/display.html", render_ctx, request=request)
    return mark_safe(html)  # noqa: S308


@pass_context
def inline_edit_form(ctx, obj, name, **extras):
    """Renders ``obj.<name>`` straight in edit mode, without its own buttons.

    For places where the field should be immediately fillable, such as onboarding.
    The form keeps its own hx-post, so the caller submits it when it suits — in the
    wizard that is "Volgende".
    """
    if obj is None:
        return mark_safe("")

    model_label = obj._meta.model_name
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        raise RuntimeError(
            f"No EditableSet registered for model '{model_label}'. Add it to wies.core.editables.REGISTRY."
        )
    spec = editable_set._editables.get(name) or editable_set.resolve_dynamic(name)
    if spec is None:
        raise RuntimeError(f"No editable '{name}' registered on {editable_set.__name__} (for model '{model_label}').")

    request = ctx.get("request")
    user = getattr(request, "user", None)
    if isinstance(spec, EditableCollection) or not has_permission(Verb.UPDATE, obj, user, spec):
        # No permission (or a collection, which needs a formset): fall back to the
        # read view rather than a form that would be rejected on save.
        return inline_edit(ctx, obj, name, **extras)

    editables = resolve_editables(editable_set, spec)
    form_cls, initial = build_form_class(editables, obj=obj, group_clean=getattr(spec, "clean", None))
    render_ctx = {
        "target": f"inline-edit-{model_label}-{obj.public_id}-{name}",
        "edit_url": reverse("inline-edit", args=[model_label, obj.public_id, name]),
        "label": _spec_label(editable_set, spec),
        "obj": obj,
        "editable": spec,
        "form": form_cls(initial=initial),
        "bare": True,
        # Without a token the save view rejects the post as a conflict; the view
        # sets it on a normal inline edit, but this macro renders the form itself.
        "concurrency_token": _concurrency_token(editable_set, spec, obj),
        **extras,
    }
    html = render_to_string("parts/inline_edit/form.html", render_ctx, request=request)
    return mark_safe(html)  # noqa: S308
