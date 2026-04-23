"""Form builder + saver for Editables. See ``features/inline-editing.md``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django import forms
from django.db.models import ManyToManyField
from django.forms.models import fields_for_model

from wies.core.form_mixins import RvoFormMixin
from wies.core.inline_edit.base import Editable, EditableGroup, EditableSet

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db.models import Model


def _build_form_field(editable: Editable) -> forms.Field:  # noqa: C901 — straight-line override application; breaking it apart would hide the structure
    # Priority: explicit form_field → derive from model field → CharField fallback.
    # Overrides (label/widget/choices/validators/error_messages/empty_label) apply last.
    if editable.form_field is not None:
        base = editable.form_field() if callable(editable.form_field) else editable.form_field
    elif editable.model is not None and editable.field is not None:
        model_fields = fields_for_model(editable.model, fields=[editable.field])
        base = model_fields[editable.field]
    else:
        base = forms.CharField(required=bool(editable.required))

    if editable.label is not None:
        base.label = editable.label
    if editable.help_text is not None:
        base.help_text = editable.help_text
    if editable.required is not None:
        base.required = editable.required
    if editable.error_messages:
        base.error_messages.update(editable.error_messages)
    if editable.validators:
        base.validators.extend(editable.validators)
    if editable.widget is not None:
        base.widget = editable.widget() if isinstance(editable.widget, type) else editable.widget
    if editable.choices is not None:
        opts = editable.choices() if callable(editable.choices) else editable.choices
        if hasattr(base, "queryset"):
            base.queryset = opts
        else:
            base.choices = list(opts)
    if editable.empty_label is not None and hasattr(base, "empty_label"):
        base.empty_label = editable.empty_label

    return base


def _current_value(obj: Model, editable: Editable) -> Any:
    # Priority: editable.initial(obj) → model field (M2M → list, scalar → attr) → None.
    if obj is None:
        return None
    if editable.initial is not None:
        return editable.initial(obj)
    if editable.model is None or editable.field is None:
        return None
    model_field = obj._meta.get_field(editable.field)
    if isinstance(model_field, ManyToManyField):
        return list(getattr(obj, editable.field).all())
    return getattr(obj, editable.field)


def build_form_class(
    editables: list[Editable],
    obj: Model | None = None,
    group_clean: Callable[[dict], dict] | None = None,
) -> tuple[type[forms.Form], dict[str, Any]]:
    """Return (FormClass, initial): RvoFormMixin-enabled form with one field per Editable."""
    form_fields: dict[str, forms.Field] = {}
    initial: dict[str, Any] = {}
    for e in editables:
        key = e.field or e.name
        if not key:
            raise ValueError(f"Editable must have a field or name: {e!r}")
        form_fields[key] = _build_form_field(e)
        if obj is not None:
            initial[key] = _current_value(obj, e)

    attrs: dict[str, Any] = dict(form_fields)
    if group_clean is not None:

        def _clean(self):
            return group_clean(self.cleaned_data)

        attrs["clean"] = _clean

    created_cls = type("InlineEditForm", (RvoFormMixin, forms.Form), attrs)
    form_cls = cast("type[forms.Form]", created_cls)
    return form_cls, initial


def resolve_editables(editable_set: type[EditableSet], spec: Editable | EditableGroup) -> list[Editable]:
    """Flatten a spec into its Editables. Groups resolve string names against the set's siblings."""
    if isinstance(spec, Editable):
        return [spec]
    if isinstance(spec, EditableGroup):
        resolved = []
        for f in spec.fields:
            if isinstance(f, Editable):
                resolved.append(f)
            elif isinstance(f, str):
                sibling = editable_set._editables.get(f)
                if sibling is None or not isinstance(sibling, Editable):
                    msg = f"EditableGroup references unknown Editable '{f}' in {editable_set.__name__}"
                    raise KeyError(msg)
                resolved.append(sibling)
            else:
                raise TypeError(f"EditableGroup.fields must contain str or Editable, got {type(f)}")
        return resolved
    raise TypeError(f"Unexpected spec type: {type(spec)}")


def build_form_from(
    editable_set: type[EditableSet],
    fields: list[str | Editable | EditableGroup],
    obj: Model | None = None,
) -> type[forms.Form]:
    """Build a form class from a selection of editables on an EditableSet.

    ``fields`` accepts attribute names, Editable instances, or EditableGroup
    instances (expanded into members). Used by full-page forms that reuse
    inline-edit declarations.
    """
    resolved: list[Editable] = []
    group_clean: Callable | None = None
    for item in fields:
        if isinstance(item, str):
            spec = editable_set._editables.get(item)
            if spec is None:
                raise ValueError(f"Unknown editable '{item}' on {editable_set.__name__}")
            resolved.extend(resolve_editables(editable_set, spec))
            if isinstance(spec, EditableGroup) and spec.clean is not None:
                group_clean = spec.clean
        elif isinstance(item, EditableGroup):
            resolved.extend(resolve_editables(editable_set, item))
            if item.clean is not None:
                group_clean = item.clean
        elif isinstance(item, Editable):
            resolved.append(item)
        else:
            raise TypeError(f"Unexpected field spec: {item!r}")

    form_cls, _ = build_form_class(resolved, obj=obj, group_clean=group_clean)
    return form_cls


def save_editables(editables: list[Editable], cleaned_data: dict, obj: Model) -> None:
    """Persist cleaned_data. Order: scalar setattr → obj.save() → M2M .set() → custom save."""
    custom_save: list[Editable] = []
    m2m: list[Editable] = []

    for e in editables:
        if e.save is not None:
            custom_save.append(e)
            continue
        if e.field is None:
            raise ValueError(f"Editable without field or save: {e!r}")
        model_field = obj._meta.get_field(e.field)
        if isinstance(model_field, ManyToManyField):
            m2m.append(e)
            continue
        setattr(obj, e.field, cleaned_data.get(e.field))

    obj.save()

    for e in m2m:
        value = cleaned_data.get(e.field) or []
        getattr(obj, e.field).set(value)

    for e in custom_save:
        key = e.field or e.name
        e.save(obj, cleaned_data.get(key))


def save_spec(
    spec: Editable | EditableGroup,
    editables: list[Editable],
    cleaned_data: dict,
    obj: Model,
) -> None:
    """Persist a spec. Group with its own save → atomic whole-group; else per-field."""
    if isinstance(spec, EditableGroup) and spec.save is not None:
        spec.save(obj, cleaned_data)
        return
    save_editables(editables, cleaned_data, obj)
