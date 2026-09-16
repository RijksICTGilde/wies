"""The role matrix on ``/beheer/rollen/``: what each role may do, on its own.

Every cell is answered by the real rules (``has_permission``, the visibility
rules, ``may_grant``), asked for a stand-in user that holds exactly one role.
Nothing is parsed from the predicates and nothing is written: the stand-in and
the objects it acts on are unsaved, with negative primary keys so a query in a
rule (``_is_placed_on_assignment``) runs and finds nothing.

``test_role_matrix.py`` keeps this honest: every registered ``@rule`` needs a
row, and the stand-in must answer like a saved user with the same role.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import Group, Permission

from wies.core.editables import AssignmentEditables, ServiceEditables, UserEditables
from wies.core.models import Assignment, Colleague, Placement, Service
from wies.core.permission_engine import Verb, has_permission
from wies.core.roles import (
    ASSIGNMENT_ADMIN_GROUP_NAME,
    BDM_GROUP_NAME,
    CONSULTANT_GROUP_NAME,
    USER_ADMIN_GROUP_NAME,
    is_staff_member,
    may_grant,
)
from wies.core.visibility_rules import evaluate_assignment_visibility, evaluate_placement_visibility, show_bm_page
from wies.rijksauth.models import User

if TYPE_CHECKING:
    from collections.abc import Callable

PLATFORM = "Platformbeheer"
# (column heading, Django group or None for platform administration)
COLUMNS = [
    ("Consultant", CONSULTANT_GROUP_NAME),
    ("BDM", BDM_GROUP_NAME),
    (ASSIGNMENT_ADMIN_GROUP_NAME, ASSIGNMENT_ADMIN_GROUP_NAME),
    (USER_ADMIN_GROUP_NAME, USER_ADMIN_GROUP_NAME),
    (PLATFORM, None),
]

_OTHER = -99  # pk of a colleague that is not the stand-in
_PAST_START, _PAST_END, _TODAY = date(2000, 1, 1), date(2000, 1, 2), date(2000, 1, 3)


class _Groups:
    """Answers ``groups.filter(name=...).exists()`` and nothing else, so a rule
    that asks something new fails loudly instead of getting a wrong answer."""

    def __init__(self, names: frozenset[str]):
        self._names = names

    def filter(self, *, name: str) -> SimpleNamespace:
        found = name in self._names
        return SimpleNamespace(exists=lambda: found)


class StandIn:
    """A logged-in user with the given roles, as far as the rules can tell."""

    is_authenticated = True

    def __init__(self, group_names, email: str, pk: int, perms: frozenset[str]):
        self.groups = _Groups(frozenset(group_names))
        self.email = email
        self.colleague = Colleague(pk=pk, email=email)
        # The same person as a User row, for the rules that compare against one.
        self.account = User(pk=pk, email=email)
        self._perms = perms

    def has_perm(self, perm: str) -> bool:
        return perm in self._perms

    def __eq__(self, other):
        return other is self or other is self.account

    __hash__ = object.__hash__


def _group_perms(group_names) -> frozenset[str]:
    return frozenset(
        f"{app_label}.{codename}"
        for app_label, codename in Permission.objects.filter(group__name__in=group_names).values_list(
            "content_type__app_label", "codename"
        )
    )


def stand_in(group_name: str | None, pk: int = -1) -> StandIn:
    """The stand-in for one column: a group, or ``None`` for platform administration."""
    if group_name is None:
        return StandIn((), next(iter(sorted(settings.STAFF_EMAILS)), ""), pk, frozenset())
    return StandIn((group_name,), "rollenmatrix@example.invalid", pk, _group_perms([group_name]))


def _assignment(u, *, own: bool) -> Assignment:
    return Assignment(pk=-1, source="wies", owner_id=u.colleague.pk if own else _OTHER)


def _service(u, *, own: bool) -> Service:
    return Service(pk=-1, assignment=_assignment(u, own=own))


def _can(verb, obj, field=None):
    return lambda u: has_permission(verb, obj(u), u, field=field)


def _sees_ended_placement(u, *, own: bool) -> bool:
    placed = u.colleague.pk if own else _OTHER
    request = SimpleNamespace(user=u)
    return evaluate_placement_visibility(_PAST_START, _PAST_END, placed, request, _TODAY).visible


@dataclass(frozen=True)
class Row:
    label: str
    check: Callable[[StandIn], bool]
    # The ``permission_engine`` key this row asks, for the coverage test.
    rule: tuple | None = None


def _rule(verb, model, editable=None) -> tuple:
    return (verb, model, editable.name if editable else None)


UPDATE, DELETE = Verb.UPDATE, Verb.DELETE

SECTIONS: list[tuple[str, list[Row]]] = [
    (
        "Opdrachten",
        [
            Row(
                "Opdracht bewerken (eigen)",
                _can(UPDATE, lambda u: _assignment(u, own=True)),
                _rule(UPDATE, Assignment),
            ),
            Row("Opdracht bewerken (van een ander)", _can(UPDATE, lambda u: _assignment(u, own=False))),
            Row(
                "Opdracht verwijderen (eigen)",
                _can(DELETE, lambda u: _assignment(u, own=True)),
                _rule(DELETE, Assignment),
            ),
            Row("Opdracht verwijderen (van een ander)", _can(DELETE, lambda u: _assignment(u, own=False))),
            Row(
                "Naam van een opdracht bewerken (van een ander)",
                _can(UPDATE, lambda u: _assignment(u, own=False), AssignmentEditables.name),
                _rule(UPDATE, Assignment, AssignmentEditables.name),
            ),
            Row(
                "Extra informatie bewerken (van een ander)",
                _can(UPDATE, lambda u: _assignment(u, own=False), AssignmentEditables.extra_info),
                _rule(UPDATE, Assignment, AssignmentEditables.extra_info),
            ),
            Row(
                "Dienst bewerken (van een ander)",
                _can(UPDATE, lambda u: _service(u, own=False)),
                _rule(UPDATE, Service),
            ),
            Row(
                "Dienstomschrijving bewerken (van een ander)",
                _can(UPDATE, lambda u: _service(u, own=False), ServiceEditables.description),
                _rule(UPDATE, Service, ServiceEditables.description),
            ),
            Row(
                "Teamlid verplaatsen (van een ander)",
                _can(UPDATE, lambda u: Placement(pk=-1, service=_service(u, own=False))),
                _rule(UPDATE, Placement),
            ),
        ],
    ),
    (
        "Zichtbaarheid",
        [
            Row("Eigen afgelopen plaatsing zien", lambda u: _sees_ended_placement(u, own=True)),
            Row("Afgelopen plaatsing van een collega zien", lambda u: _sees_ended_placement(u, own=False)),
            Row(
                "Afgelopen opdracht van een Business Manager zien",
                lambda u: (
                    evaluate_assignment_visibility(_PAST_START, _PAST_END, SimpleNamespace(user=u), _TODAY).visible
                ),
            ),
            Row("Business management-sectie", lambda u: show_bm_page(SimpleNamespace(user=u))),
        ],
    ),
    (
        "Gebruikers en collega's",
        [
            Row(
                "Gebruiker aanmaken en verwijderen",
                lambda u: u.has_perm("rijksauth.add_user") and u.has_perm("rijksauth.delete_user"),
            ),
            Row(
                "Gebruiker bewerken (van een ander)",
                _can(UPDATE, lambda u: User(pk=_OTHER)),
                _rule(UPDATE, User),
            ),
            Row("Eigen profiel bewerken", _can(UPDATE, lambda u: u.account)),
            Row(
                "E-mailadres wijzigen (van een ander)",
                _can(UPDATE, lambda u: User(pk=_OTHER), UserEditables.email),
                _rule(UPDATE, User, UserEditables.email),
            ),
            Row(
                "Collega bewerken (van een ander)",
                _can(UPDATE, lambda u: Colleague(pk=_OTHER)),
                _rule(UPDATE, Colleague),
            ),
            Row("Eigen collegagegevens bewerken", _can(UPDATE, lambda u: u.colleague)),
            Row(
                "Rol Consultant of BDM toekennen",
                lambda u: may_grant(u, CONSULTANT_GROUP_NAME) and may_grant(u, BDM_GROUP_NAME),
            ),
            Row(
                "Rol Gebruikersbeheer of Opdrachtbeheer toekennen",
                lambda u: may_grant(u, USER_ADMIN_GROUP_NAME) and may_grant(u, ASSIGNMENT_ADMIN_GROUP_NAME),
            ),
        ],
    ),
    ("Platform", [Row("Statistieken en database", is_staff_member)]),
]


def build_matrix() -> list[tuple[str, list[tuple[str, list[bool]]]]]:
    """``[(section, [(row label, [allowed per column])])]``."""
    users = [stand_in(group) for _heading, group in COLUMNS]
    return [(title, [(row.label, [bool(row.check(u)) for u in users]) for row in rows]) for title, rows in SECTIONS]


def group_permissions() -> list[tuple[str, list[bool]]]:
    """The Django model permissions per column, straight from ``Group.permissions``."""
    held = {
        group.name: {perm.pk for perm in group.permissions.all()}
        for group in Group.objects.filter(name__in=[g for _h, g in COLUMNS if g]).prefetch_related("permissions")
    }
    perms = Permission.objects.filter(group__name__in=held).distinct().order_by("content_type__app_label", "codename")
    return [(perm.name, [perm.pk in held.get(group, ()) for _h, group in COLUMNS]) for perm in perms]
