"""Row-level permission engine: ``has_permission(verb, obj, user, field=None)``.

Application-specific rules live in ``wies/core/permissions.py``.

Rules register with ``@rule(verb, target)`` against either a model class
(whole-object) or an Editable/EditableGroup/EditableCollection instance
(field-level). Class-level access (LIST/CREATE pages) stays on Django's
group permissions + ``@permission_required`` decorators — not duplicated
here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from wies.core.inline_edit.base import Editable, EditableCollection, EditableGroup


class Verb(StrEnum):
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


# Lookup key: (verb, model class, optional field name)
_RULES: dict[tuple[Verb, type, str | None], Callable] = {}


def rule(verb: Verb, target):
    """Register a rule for a verb on a target.

    ``target`` is a Django Model class (whole-object) or an Editable /
    EditableGroup / EditableCollection instance bound to a model
    (field-level).
    """

    def register(fn: Callable) -> Callable:
        if isinstance(target, type):
            _RULES[(verb, target, None)] = fn
        else:
            if target.model is None:
                msg = (
                    f"Cannot register rule for unbound editable: {target!r}. "
                    "Editables get their model from the EditableSet's Meta."
                )
                raise ValueError(msg)
            _RULES[(verb, target.model, target.name)] = fn
        return fn

    return register


def has_permission(
    verbs: Verb | list[Verb] | tuple[Verb, ...],
    obj,
    user,
    field: Editable | EditableGroup | EditableCollection | None = None,
) -> bool:
    """Return True iff `user` is allowed to perform `verbs` on `obj`.

    - ``obj`` is a model **instance** for row-level checks.
    - ``field`` is an Editable for field-level narrowing (optional).
    - Multiple verbs (list/tuple) are OR-composed: True if any verb's rule passes.
    - Returns True for any superuser. Returns False for anonymous users.
    - Lookup order: ``(verb, model, field.name)`` → ``(verb, model, None)``.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True

    if field is not None:
        if field.model is None:
            return False
        model = field.model
        fname = field.name
    else:
        model = type(obj)
        fname = None

    verb_iter = verbs if isinstance(verbs, (list, tuple)) else (verbs,)
    for verb in verb_iter:
        fn = _RULES.get((verb, model, fname)) or _RULES.get((verb, model, None))
        if fn and fn(user, obj):
            return True
    return False


def registered_rules() -> dict[tuple[Verb, type, str | None], Callable]:
    """Read-only view of the registry. For use in startup checks and tests."""
    return dict(_RULES)
