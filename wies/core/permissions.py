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
    OWN,
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
    ROLE_ASSIGNMENT_ADMIN,
    ROLE_BDM,
    ROLE_CONSULTANT,
    ROLE_OFFICE_ASSISTANT,
    ROLE_STAFF,
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
        Grant(Role(ROLE_ASSIGNMENT_ADMIN)),
        Grant(Role(ROLE_BDM), scope=OWN),
    ],
)

rule(
    UPDATE,
    Service,
    label="Dienst bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_ASSIGNMENT_ADMIN)),
        Grant(Role(ROLE_BDM), scope=OWN),
    ],
)

rule(
    UPDATE,
    Placement,
    label="Teamlid verplaatsen",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_ASSIGNMENT_ADMIN)),
        Grant(Role(ROLE_BDM), scope=OWN),
    ],
)

rule(
    UPDATE,
    Colleague,
    label="Collega bewerken",
    grants=[
        Grant(Role(ROLE_OFFICE_ASSISTANT)),
        Grant(Anyone(), scope=SELF),
    ],
)

rule(
    UPDATE,
    User,
    label="Gebruiker bewerken",
    grants=[
        Grant(Role(ROLE_OFFICE_ASSISTANT)),
        Grant(Anyone(), scope=SELF),
    ],
)


# --- Whole-object DELETE rules ----------------------------------------------

rule(
    DELETE,
    Assignment,
    label="Opdracht verwijderen",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_ASSIGNMENT_ADMIN)),
        Grant(Role(ROLE_BDM), scope=OWN),
    ],
)


# --- Field-level UPDATE rules -----------------------------------------------

rule(
    UPDATE,
    AssignmentEditables.name,
    label="Naam van een opdracht bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_ASSIGNMENT_ADMIN)),
        Grant(Role(ROLE_BDM), scope=OWN),
        Grant(Role(ROLE_CONSULTANT), scope=PLACED),
    ],
)

rule(
    UPDATE,
    AssignmentEditables.extra_info,
    label="Extra informatie bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_ASSIGNMENT_ADMIN)),
        Grant(Role(ROLE_BDM), scope=OWN),
        Grant(Role(ROLE_CONSULTANT), scope=PLACED),
    ],
)

rule(
    UPDATE,
    ServiceEditables.description,
    label="Dienstomschrijving bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_ASSIGNMENT_ADMIN)),
        Grant(Role(ROLE_BDM), scope=OWN),
        Grant(Role(ROLE_CONSULTANT), scope=PLACED_ON_SERVICE),
    ],
)

rule(
    READ,
    ContractPeriod,
    label="Contracturen van een collega zien",
    grants=[
        Grant(Role(ROLE_BDM)),
        Grant(Role(ROLE_OFFICE_ASSISTANT)),
        Grant(Role(ROLE_STAFF)),
    ],
)

rule(
    UPDATE,
    ContractPeriod,
    label="Contracturen van een collega bijhouden",
    grants=[Grant(Role(ROLE_OFFICE_ASSISTANT))],
)

# Nobody: an address is changed on the user form, which is where ``may_change_email``
# can see the new one and refuse a move to or from a STAFF_EMAILS address.
rule(
    UPDATE,
    UserEditables.email,
    label="E-mailadres inline wijzigen",
    grants=[],
)
