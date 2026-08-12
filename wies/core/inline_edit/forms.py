"""Form builder + saver for Editables. See ``features/inline-editing.md``."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, cast

from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.db.models import ManyToManyField
from django.forms.models import fields_for_model

from wies.core.form_mixins import NlddFormMixin
from wies.core.inline_edit.base import Editable, EditableGroup, EditableSet

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db.models import Model


def has_public_id(model: type[Model]) -> bool:
    try:
        model._meta.get_field("public_id")
    except FieldDoesNotExist:
        return False
    return True


def use_public_id_choices(field: forms.Field) -> None:
    """Makes a ModelChoiceField render and accept ``public_id`` instead of the pk.

    Option values cross the client boundary. Models without a public_id (e.g.
    Group) keep the pk. See ``features/public_id.md``.
    """
    queryset = getattr(field, "queryset", None)
    if queryset is not None and has_public_id(queryset.model):
        field.to_field_name = "public_id"


def _takes_obj(fn: Callable) -> bool:
    """Returns whether a choices callable wants the edited object passed in."""
    try:
        return len(inspect.signature(fn).parameters) >= 1
    except TypeError, ValueError:  # Builtins and C functions have no signature.
        return False


def _build_form_field(editable: Editable, obj: Model | None = None) -> forms.Field:  # noqa: C901 — straight-line override application; breaking it apart would hide the structure
    # Priority: explicit form_field_factory → derive from model field → CharField fallback.
    # Overrides (label/widget/choices/validators/error_messages/empty_label) apply last.
    if editable.form_field_factory is not None:
        base = editable.form_field_factory() if callable(editable.form_field_factory) else editable.form_field_factory
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
        # A choices callable may take the edited object so it can keep the current
        # value in the list even when the normal rules exclude it (see _bdm_queryset).
        if callable(editable.choices):
            opts = editable.choices(obj) if _takes_obj(editable.choices) else editable.choices()
        else:
            opts = editable.choices
        if hasattr(base, "queryset"):
            base.queryset = opts
        else:
            base.choices = list(opts)
    if editable.empty_label is not None and hasattr(base, "empty_label"):
        base.empty_label = editable.empty_label
    use_public_id_choices(base)

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
    field_objs: dict[str, Model] | None = None,
) -> tuple[type[forms.Form], dict[str, Any]]:
    """Returns (FormClass, initial): an NlddFormMixin form with one field per Editable.

    ``field_objs`` maps a field name to its owning object, for forms bundling
    several objects; without it ``obj`` applies to every field.
    """
    form_fields: dict[str, forms.Field] = {}
    initial: dict[str, Any] = {}
    for e in editables:
        key = e.field or e.name
        if not key:
            raise ValueError(f"Editable must have a field or name: {e!r}")
        form_fields[key] = _build_form_field(e, (field_objs or {}).get(key, obj))
        if obj is not None:
            initial[key] = _current_value(obj, e)

    attrs: dict[str, Any] = dict(form_fields)
    if group_clean is not None:

        def _clean(self):
            return group_clean(self.cleaned_data)

        attrs["clean"] = _clean

    created_cls = type("InlineEditForm", (NlddFormMixin, forms.Form), attrs)
    form_cls = cast("type[forms.Form]", created_cls)
    return form_cls, initial


def resolve_editables(editable_set: type[EditableSet], spec: Editable | EditableGroup) -> list[Editable]:
    """Flattens a spec into its Editables. Groups resolve string names against the set's siblings."""
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


def save_editables(editables: list[Editable], cleaned_data: dict, obj: Model) -> None:
    """Persists cleaned_data. Order: scalar setattr → obj.save() → M2M .set() → custom save."""
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
    """Persists a spec. A group with its own save writes atomically; else per-field."""
    if isinstance(spec, EditableGroup) and spec.save is not None:
        spec.save(obj, cleaned_data)
        return
    save_editables(editables, cleaned_data, obj)


def build_combined_form_class(specs, *, bound_obj=None):
    """Returns one form class spanning several specs, plus its initial values.

    ``specs`` is a list of ``(editable_set, spec, obj)``. Used by the child sheets
    that bundle fields across two models (Service + Placement); field names do not
    collide, so they flatten into one form. A group ``clean`` still applies.
    """
    editables: list[Editable] = []
    initial: dict = {}
    # Each editable keeps its own object; `bound_obj` cannot cover that here.
    field_objs: dict[str, Model] = {}
    group_clean = None
    for editable_set, spec, obj in specs:
        spec_editables = resolve_editables(editable_set, spec)
        editables.extend(spec_editables)
        for e in spec_editables:
            key = e.field or e.name
            initial[key] = _current_value(obj, e)
            if obj is not None:
                field_objs[key] = obj
        if getattr(spec, "clean", None):
            group_clean = spec.clean
    form_cls, _ = build_form_class(editables, obj=bound_obj, group_clean=group_clean, field_objs=field_objs)
    return form_cls, initial
