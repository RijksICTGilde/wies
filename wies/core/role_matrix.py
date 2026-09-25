"""The role matrix on ``/beheer/rollen/``, see ``features/roles.md``.

The rows about opdrachten, diensten, collega's and gebruikers are *read* from the
rules in ``permissions.py``: one row per relation a rule mentions, one column per
authority. Nothing is probed, so no stand-in acts on an object and no Placement
query runs.

The rows underneath are not rules and still ask their own predicate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import Group, Permission

from wies.core.models import Assignment, Colleague, ContractPeriod, Placement, Service
from wies.core.permission_engine import (
    ANY,
    SCOPES,
    registered_rules,
)
from wies.core.roles import (
    ROLE_BDM,
    ROLE_CONSULTANT,
    ROLE_OFFICE_ASSISTANT,
    ROLE_STAFF,
    is_staff_member,
    may_administer_roles,
    may_change_email,
    may_view_users,
    role_label,
)
from wies.core.visibility_rules import evaluate_assignment_visibility, evaluate_placement_visibility, show_bm_page
from wies.rijksauth.models import User

if TYPE_CHECKING:
    from collections.abc import Callable

STAFF = role_label(ROLE_STAFF)
# (column heading, Django groups, application administration)
COLUMNS = [
    (role_label(ROLE_CONSULTANT), (ROLE_CONSULTANT,), False),
    ("BDM", (ROLE_BDM,), False),
    (role_label(ROLE_OFFICE_ASSISTANT), (ROLE_OFFICE_ASSISTANT,), False),
    (STAFF, (), True),
]

SECTION_ORDER = ["Opdrachten", "Zichtbaarheid", "Gebruikers en collega's", "Applicatie"]

SECTION_BY_MODEL = {
    Assignment: "Opdrachten",
    Service: "Opdrachten",
    Placement: "Opdrachten",
    Colleague: "Gebruikers en collega's",
    ContractPeriod: "Gebruikers en collega's",
    User: "Gebruikers en collega's",
}

_OTHER = -99  # pk of a colleague that is not the stand-in
_PAST_START, _PAST_END, _TODAY = date(2000, 1, 1), date(2000, 1, 2), date(2000, 1, 3)


# --- The rows that are rules -------------------------------------------------


def section_of(model) -> str:
    section = SECTION_BY_MODEL.get(model)
    if section is None:
        msg = f"No role matrix section for {model.__name__}; add one to SECTION_BY_MODEL."
        raise KeyError(msg)
    return section


def _reaches(grant, rule, user) -> bool:
    """Whether ``grant`` covers this column, once its relation is satisfied.

    Every holder asks about the viewer alone, so it answers with its own code and
    no object.
    """
    return grant.holder.qualifies(user, None, rule.verb)


def _rule_cell(rule, scope, user) -> bool:
    """A grant covers a row when its relation asks no more than the row's: whoever
    may edit any opdracht may edit the one they own."""
    return any(grant.scope.parts <= scope.parts and _reaches(grant, rule, user) for grant in rule.grants)


def row_scopes(rule) -> set:
    """The relations a rule distinguishes: the ones its own grants name, and always
    the relation-free row that says what holds for somebody else's object."""
    return {ANY} | {grant.scope for grant in rule.grants}


def cells_for(rule, scope, users) -> list[bool]:
    """The row a rule produces for one relation, one cell per stand-in."""
    return [_rule_cell(rule, scope, user) for user in users]


def rule_rows() -> list[tuple[str, str, object, object]]:
    """``[(section, label, rule, scope)]``, the label composed from the rule and
    the relation, each of which carries its own wording."""
    rows = []
    for rule in registered_rules().values():
        scopes = row_scopes(rule)
        rows += [
            (section_of(rule.model), f"{rule.label} ({scope.label})", rule, scope)
            for scope in SCOPES
            if scope in scopes
        ]
    return rows


# --- The rows that are not rules ---------------------------------------------


class _Groups:
    """Answers ``groups.filter(name=...).exists()`` and nothing else, so a rule
    that asks something new fails loudly instead of getting a wrong answer."""

    def __init__(self, names: frozenset[str]):
        self._names = names

    def filter(self, *, name: str) -> SimpleNamespace:
        found = name in self._names
        return SimpleNamespace(exists=lambda: found)


class StandIn:
    """A logged-in user with the given roles, as far as the predicates can tell."""

    is_authenticated = True

    def __init__(self, group_names, email: str, pk: int, perms: frozenset[str]):
        self.groups = _Groups(frozenset(group_names))
        self.email = email
        self.colleague = Colleague(pk=pk, email=email)
        self._perms = perms

    def has_perm(self, perm: str) -> bool:
        return perm in self._perms


def stand_in(group_names, *, staff: bool, pk: int = -1) -> StandIn:
    """The stand-in for one column of ``COLUMNS``."""
    email = next(iter(sorted(settings.STAFF_EMAILS)), "") if staff else "rollenmatrix@example.invalid"
    perms = frozenset(
        f"{app_label}.{codename}"
        for app_label, codename in Permission.objects.filter(group__name__in=group_names).values_list(
            "content_type__app_label", "codename"
        )
    )
    return StandIn(group_names, email, pk, perms)


def column_stand_ins() -> list[StandIn]:
    return [stand_in(groups, staff=staff) for _heading, groups, staff in COLUMNS]


def _in_user_screen(u, *, allowed: bool) -> bool:
    """``allowed`` behind the person half of the user sheet, where the form asks it."""
    return u.has_perm("rijksauth.change_user") and allowed


def _sees_ended_placement(u, *, own: bool) -> bool:
    placed = u.colleague.pk if own else _OTHER
    request = SimpleNamespace(user=u)
    return evaluate_placement_visibility(_PAST_START, _PAST_END, placed, request, _TODAY).visible


@dataclass(frozen=True)
class Row:
    """A row the rules do not carry: a visibility rule or a screen's own gate."""

    section: str
    label: str
    check: Callable[[StandIn], bool]


EXTRA_ROWS = [
    Row("Zichtbaarheid", "Eigen afgelopen plaatsing zien", lambda u: _sees_ended_placement(u, own=True)),
    Row("Zichtbaarheid", "Afgelopen plaatsing van een collega zien", lambda u: _sees_ended_placement(u, own=False)),
    Row(
        "Zichtbaarheid",
        "Afgelopen opdracht van een Business Manager zien",
        lambda u: evaluate_assignment_visibility(_PAST_START, _PAST_END, SimpleNamespace(user=u), _TODAY).visible,
    ),
    Row("Zichtbaarheid", "Business management-sectie", lambda u: show_bm_page(SimpleNamespace(user=u))),
    # Not derivable from the Django permission underneath: since the sheet that
    # hands out roles hangs off this page, it opens for ``may_administer_roles``
    # too, and application administration holds that without ``view_user``.
    Row("Gebruikers en collega's", "Gebruikerslijst openen", may_view_users),
    Row(
        "Gebruikers en collega's",
        "Gebruiker aanmaken en verwijderen",
        lambda u: u.has_perm("rijksauth.add_user") and u.has_perm("rijksauth.delete_user"),
    ),
    Row(
        "Gebruikers en collega's",
        "E-mailadres wijzigen (van een ander)",
        lambda u: _in_user_screen(u, allowed=may_change_email(u, "a@example.invalid", "b@example.invalid")),
    ),
    # One row: no role has a granter of its own, so a row per role would repeat
    # the same answer.
    Row("Gebruikers en collega's", "Rollen toekennen", may_administer_roles),
    Row("Applicatie", "Statistieken en database", is_staff_member),
]


# --- The table ---------------------------------------------------------------


def build_matrix() -> list[tuple[str, list[tuple[str, list[bool]]]]]:
    """``[(section, [(row label, [allowed per column])])]``."""
    users = column_stand_ins()
    rows: dict[str, list[tuple[str, list[bool]]]] = {section: [] for section in SECTION_ORDER}
    for section, label, rule, scope in rule_rows():
        rows[section].append((label, cells_for(rule, scope, users)))
    for row in EXTRA_ROWS:
        rows[row.section].append((row.label, [bool(row.check(user)) for user in users]))
    return [(section, rows[section]) for section in SECTION_ORDER]


def group_permissions() -> list[tuple[str, list[bool]]]:
    """The Django model permissions per column, straight from ``Group.permissions``."""
    held = {
        group.name: {perm.pk for perm in group.permissions.all()}
        for group in Group.objects.filter(name__in={g for _h, groups, _s in COLUMNS for g in groups}).prefetch_related(
            "permissions"
        )
    }
    perms = Permission.objects.filter(group__name__in=held).distinct().order_by("content_type__app_label", "codename")
    return [
        (perm.name, [any(perm.pk in held.get(g, ()) for g in groups) for _h, groups, _s in COLUMNS]) for perm in perms
    ]
