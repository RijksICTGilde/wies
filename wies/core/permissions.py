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
    ROLE_BDM,
    ROLE_CONSULTANT,
    ROLE_OFFICE_ASSISTANT,
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
        Grant(Role(ROLE_BDM)),
    ],
)

rule(
    UPDATE,
    Service,
    label="Dienst bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BDM)),
    ],
)

rule(
    UPDATE,
    Placement,
    label="Teamlid verplaatsen",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BDM)),
    ],
)

rule(
    UPDATE,
    Colleague,
    label="Collega bewerken",
    grants=[
        Grant(Role(ROLE_OFFICE_ASSISTANT)),
        Grant(Anyone(), SELF),
    ],
)

rule(
    UPDATE,
    User,
    label="Gebruiker bewerken",
    grants=[
        Grant(Role(ROLE_OFFICE_ASSISTANT)),
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
        Grant(Role(ROLE_BDM)),
    ],
)


# --- Field-level UPDATE rules -----------------------------------------------

rule(
    UPDATE,
    AssignmentEditables.name,
    label="Naam van een opdracht bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BDM)),
        Grant(Role(ROLE_CONSULTANT), PLACED),
    ],
)

rule(
    UPDATE,
    AssignmentEditables.extra_info,
    label="Extra informatie bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BDM)),
        Grant(Role(ROLE_CONSULTANT), PLACED),
    ],
)

rule(
    UPDATE,
    ServiceEditables.description,
    label="Dienstomschrijving bewerken",
    requires=WIES_SOURCED,
    grants=[
        Grant(Role(ROLE_BDM)),
        Grant(Role(ROLE_CONSULTANT), PLACED_ON_SERVICE),
    ],
)

# Not Applicatiebeheer: it runs the platform and carries nothing functional, and
# contract hours are as functional as data gets. Whoever does both holds a role
# for the second half; 0012 hands the addresses in STAFF_EMAILS both roles once.
rule(
    READ,
    ContractPeriod,
    label="Contracturen van een collega zien",
    grants=[
        Grant(Role(ROLE_BDM)),
        Grant(Role(ROLE_OFFICE_ASSISTANT)),
    ],
)

rule(
    UPDATE,
    ContractPeriod,
    label="Contracturen van een collega bijhouden",
    grants=[
        Grant(Role(ROLE_BDM)),
        Grant(Role(ROLE_OFFICE_ASSISTANT)),
    ],
)

# Nobody: an address is changed on the user form, which is where ``may_change_email``
# can see the new one and refuse a move to or from a STAFF_EMAILS address.
rule(
    UPDATE,
    UserEditables.email,
    label="E-mailadres inline wijzigen",
    grants=[],
)
