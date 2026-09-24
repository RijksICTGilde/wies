"""Row-level permission engine: ``has_permission(verb, obj, user, field=None)``.

The rules live in ``wies/core/permissions.py`` and are *declarations*, not
function bodies: a rule says what the object has to be (``requires``) and who it
serves (``grants``), each holder with the relation it needs to the object
(``Scope``). This module executes that declaration and the role matrix on
``/beheer/rollen/`` reads it to build its table, so the page cannot drift from
the rule.

Rules register with ``rule(verb, target, ...)`` against either a model class
(whole-object) or an Editable/EditableGroup/EditableCollection instance
(field-level). Class-level access (LIST/CREATE pages) stays on Django's group
permissions + ``@permission_required`` decorators, not duplicated here.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import StrEnum
from typing import TYPE_CHECKING

from wies.core.models import Assignment, Colleague, Placement, Service
from wies.core.roles import ROLE_STAFF, is_staff_member

if TYPE_CHECKING:
    from collections.abc import Callable

    from wies.core.inline_edit.base import Editable, EditableCollection, EditableGroup


class Verb(StrEnum):
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


@dataclass(frozen=True)
class Scope:
    """The relation a holder needs to the object it acts on.

    The wording of the row and the predicate that makes it true sit together, so
    a rule names a relation and never spells out how the role page prints it.
    """

    name: str
    label: str
    # ``predicate(user, obj, grant)``. No scope reads the grant today; a merk
    # scope will (#526), and adding the argument then means visiting every scope.
    predicate: Callable[[object, object, object], bool]
    # The relations this one asks for at once. A grant covers a row when its parts
    # are a subset of the row's, which is how ANY covers every row and how "eigen"
    # covers "eigen, binnen je merk".
    parts: frozenset[str] | None = None

    def __post_init__(self):
        if self.parts is None:
            object.__setattr__(self, "parts", frozenset({self.name}))

    def __repr__(self) -> str:
        return f"Scope.{self.name.upper()}"


def all_of(*scopes: Scope) -> Scope:
    """A relation that is every one of ``scopes`` at once.

    The other way to combine is "either of these", and that is two ``Grant``
    entries with the same holder; there is no ``any_of`` because a rule's grants
    already add up.

    Name the result as a module constant and add it to ``SCOPES``: the role matrix
    walks that tuple, so a combination missing from it prints no row at all.
    """
    return Scope(
        "+".join(scope.name for scope in scopes),
        ", ".join(scope.label for scope in scopes),
        lambda user, obj, grant: all(scope.predicate(user, obj, grant) for scope in scopes),
        frozenset().union(*(scope.parts for scope in scopes)),
    )


_ASSIGNMENT_PATH = {Assignment: (), Service: ("assignment",), Placement: ("service", "assignment")}


def assignment_of(obj):
    """The Assignment ``obj`` belongs to, or None for a model that has none."""
    path = _ASSIGNMENT_PATH.get(type(obj))
    if path is None:
        return None
    for step in path:
        obj = getattr(obj, step)
    return obj


def _is_assignment_owner(user, obj, _grant) -> bool:
    assignment = assignment_of(obj)
    colleague = getattr(user, "colleague", None)
    return bool(assignment is not None and colleague and assignment.owner_id == colleague.id)


def _is_placed_on_assignment(user, obj, _grant) -> bool:
    assignment = assignment_of(obj)
    colleague = getattr(user, "colleague", None)
    if assignment is None or not colleague:
        return False
    return Placement.objects.filter(service__assignment=assignment, colleague=colleague).exists()


def _is_placed_on_service(user, obj, _grant) -> bool:
    colleague = getattr(user, "colleague", None)
    if not colleague or not isinstance(obj, Service):
        return False
    return Placement.objects.filter(service=obj, colleague=colleague).exists()


def _is_self(user, obj, _grant) -> bool:
    """``obj`` is the user: their User row, or the Colleague row that is them.

    Django compares model instances by class and pk, so the two shapes cannot be
    confused with each other.
    """
    return obj == user or (isinstance(obj, Colleague) and obj == getattr(user, "colleague", None))


# One signature for every scope, so no caller special-cases ANY. Its parts are
# empty because it asks for no relation at all, which is what makes it cover
# every row without the matrix naming it.
ANY = Scope("any", "van een ander", lambda _user, _obj, _grant: True, frozenset())
OWN = Scope("own", "eigen", _is_assignment_owner)
PLACED = Scope("placed", "waarop je geplaatst bent", _is_placed_on_assignment)
PLACED_ON_SERVICE = Scope("placed_on_service", "waarop je geplaatst bent", _is_placed_on_service)
SELF = Scope("self", "je eigen", _is_self)

# Narrowest relation first, so a row is read before the row that widens it.
SCOPES = (OWN, SELF, PLACED, PLACED_ON_SERVICE, ANY)


class _Condition:
    """Something the object itself has to be, whoever is asking."""

    label: str

    def holds(self, obj) -> bool:
        raise NotImplementedError


class _Audience:
    """An entry of a rule's ``grants``."""

    scope: Scope

    def holds(self, user, obj, verb: Verb) -> bool:
        raise NotImplementedError


class _WiesSourced(_Condition):
    label = "alleen voor opdrachten uit Wies"

    def holds(self, obj) -> bool:
        assignment = assignment_of(obj)
        return assignment is not None and assignment.source in ("wies", "")


WIES_SOURCED = _WiesSourced()


class _Holder:
    """Who a rule serves. The relation they need to the object is the ``Grant``'s,
    so a holder is only ever the answer to "who"."""

    def qualifies(self, user, obj, verb: Verb) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class Role(_Holder):
    """Whoever holds the role, named by its key (``ROLE_*``).

    Membership is a Django group, except for ``ROLE_STAFF`` (see ``roles.py``);
    a rule should not have to care, so that one is a ``Role`` like any other.
    """

    group: str

    def qualifies(self, user, obj, verb: Verb) -> bool:
        if self.group == ROLE_STAFF:
            return is_staff_member(user)
        return user.groups.filter(name=self.group).exists()


@dataclass(frozen=True)
class Anyone(_Holder):
    """No role needed; the grant's scope is the whole condition."""

    def qualifies(self, user, obj, verb: Verb) -> bool:
        return True


@dataclass(frozen=True)
class Grant(_Audience):
    """One audience of a rule: a holder, and the relation they need to the object."""

    holder: _Holder
    scope: Scope = ANY

    def holds(self, user, obj, verb: Verb) -> bool:
        return self.scope.predicate(user, obj, self) and self.holder.qualifies(user, obj, verb)


@dataclass(frozen=True)
class Rule:
    """One registered right, as it is declared and as it is executed."""

    verb: Verb
    model: type
    field_name: str | None
    label: str
    grants: tuple[_Audience, ...]
    requires: tuple[_Condition, ...] = dataclass_field(default_factory=tuple)

    def __call__(self, user, obj) -> bool:
        """Execute the declaration. The registry maps a key to this object, so a
        test can still swap a rule for a plain callable of its own."""
        if not all(condition.holds(obj) for condition in self.requires):
            return False
        return any(grant.holds(user, obj, self.verb) for grant in self.grants)


# Lookup key: (verb, model class, optional field name)
_RULES: dict[tuple[Verb, type, str | None], Rule] = {}


def rule(verb: Verb, target, *, label: str, grants, requires=()) -> Rule:
    """Declare and register a rule for a verb on a target.

    ``target`` is a Django Model class (whole-object) or an Editable /
    EditableGroup / EditableCollection instance bound to a model (field-level).

    ``label`` is the row the role matrix prints and ``grants`` is who the rule
    serves, as ``Grant`` entries; both are mandatory keywords, so a right cannot
    be added without appearing in the matrix. An empty ``grants`` declares that
    nobody may do it, and the matrix shows that row as "Nee" in every column.
    """
    grants = tuple(grants)
    requires = (requires,) if isinstance(requires, _Condition) else tuple(requires)
    if not all(isinstance(grant, _Audience) for grant in grants):
        msg = f"Rule {label!r} must name its audience as Grant entries, got {grants!r}."
        raise TypeError(msg)
    if not all(isinstance(condition, _Condition) for condition in requires):
        msg = f"Rule {label!r} must state its requirements as conditions, got {requires!r}."
        raise TypeError(msg)

    if isinstance(target, type):
        model, field_name = target, None
    else:
        if target.model is None:
            msg = (
                f"Cannot register rule for unbound editable: {target!r}. "
                "Editables get their model from the EditableSet's Meta."
            )
            raise ValueError(msg)
        model, field_name = target.model, target.name

    registered = Rule(verb=verb, model=model, field_name=field_name, label=label, grants=grants, requires=requires)
    _RULES[(verb, model, field_name)] = registered
    return registered


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
    - Returns False for anonymous users.
    - Lookup order: ``(verb, model, field.name)`` → ``(verb, model, None)``.
    """
    if not getattr(user, "is_authenticated", False):
        return False

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


def registered_rules() -> dict[tuple[Verb, type, str | None], Rule]:
    """Read-only view of the registry. The role matrix and the tests read this."""
    return dict(_RULES)
