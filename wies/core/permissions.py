"""All permission rules for the wies app.

Open this file to see who can do what: every ``rule(...)`` below is both the
right that is enforced and the row the role matrix (``/beheer/rollen/``) prints.
The vocabulary and the evaluation live in ``wies/core/permission_engine.py``.

Imported in ``wies.core.apps.CoreConfig.ready`` so registrations happen
at startup.
"""

from __future__ import annotations

from wies.core.editables import (
    AssignmentEditables,
    ServiceEditables,
    UserEditables,
)
from wies.core.models import Assignment, Colleague, ContractPeriod, Placement, Service
from wies.core.permission_engine import (
    PLACED,
    PLACED_ON_SERVICE,
    SELF,
    WIES_SOURCED,
    Anyone,
    Grant,
    Role,
    Verb,
    rule,
)
from wies.core.roles import (
    ROLE_BUSINESS_MANAGER,
    ROLE_CONSULTANT,
    ROLE_USER_ADMIN,
)
from wies.rijksauth.models import User

READ = Verb.READ
UPDATE = Verb.UPDATE
DELETE = Verb.DELETE

# --- Whole-object UPDATE rules ----------------------------------------------

rule(
    UPDATE,
    Assignment,
    label="Opdracht bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BUSINESS_MANAGER)),
    ],
)

rule(
    UPDATE,
    Service,
    label="Dienst bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BUSINESS_MANAGER)),
    ],
)

rule(
    UPDATE,
    Placement,
    label="Teamlid verplaatsen",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BUSINESS_MANAGER)),
    ],
)

rule(
    UPDATE,
    Colleague,
    label="Collega bewerken",
    grants=[
        Grant(Role(ROLE_USER_ADMIN)),
        Grant(Anyone(), SELF),
    ],
)

rule(
    UPDATE,
    User,
    label="Gebruiker bewerken",
    grants=[
        Grant(Role(ROLE_USER_ADMIN)),
        Grant(Anyone(), SELF),
    ],
)


# --- Whole-object DELETE rules ----------------------------------------------

rule(
    DELETE,
    Assignment,
    label="Opdracht verwijderen",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BUSINESS_MANAGER)),
    ],
)


# --- Field-level UPDATE rules -----------------------------------------------

rule(
    UPDATE,
    AssignmentEditables.name,
    label="Naam van een opdracht bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BUSINESS_MANAGER)),
        Grant(Role(ROLE_CONSULTANT), PLACED),
    ],
)

rule(
    UPDATE,
    AssignmentEditables.extra_info,
    label="Extra informatie bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BUSINESS_MANAGER)),
        Grant(Role(ROLE_CONSULTANT), PLACED),
    ],
)

rule(
    UPDATE,
    ServiceEditables.description,
    label="Dienstomschrijving bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BUSINESS_MANAGER)),
        Grant(Role(ROLE_CONSULTANT), PLACED_ON_SERVICE),
    ],
)

rule(
    READ,
    ContractPeriod,
    label="Contracturen van een collega zien",
    grants=[
        Grant(Role(ROLE_BUSINESS_MANAGER)),
        Grant(Role(ROLE_USER_ADMIN)),
    ],
)

# A Business Manager plans with the hours and so reads them; keeping them is beheer.
rule(
    UPDATE,
    ContractPeriod,
    label="Contracturen van een collega bijhouden",
    grants=[Grant(Role(ROLE_USER_ADMIN))],
)

# Nobody: an address is changed on the user form, which is where ``may_change_email``
# can see the new one and refuse a move to or from a STAFF_EMAILS address.
rule(
    UPDATE,
    UserEditables.email,
    label="E-mailadres inline wijzigen",
    grants=[],
)
