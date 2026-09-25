"""Group/permission setup and role predicates for Office assistent, Consultant
and BDM. The authority model is described in ``features/roles.md``.

Per-row authorization for inline-edit and views lives in
``wies/core/permissions.py``. This module owns the Django Group definitions,
the group-membership / app-admin predicates they build on, and the request-cached
visibility gate those feed. It imports nothing from ``permissions.py`` (the
dependency runs the other way), so low-level modules like
``editables/assignment.py`` can import these predicates without a cycle.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from wies.core.models import (
    Assignment,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Suborganization,
)

User = get_user_model()

# Matching uses the key, showing resolves through ``role_label``: a rename is one
# string here, not a data migration.
ROLE_CONSULTANT = "consultant"
ROLE_BDM = "bdm"
ROLE_OFFICE_ASSISTANT = "office_assistant"
# Deliberately not a Django group: who holds this one lives in STAFF_EMAILS.
ROLE_STAFF = "staff"

ROLE_LABELS = {
    ROLE_CONSULTANT: "Consultant",
    ROLE_BDM: "Business Development Manager",
    ROLE_OFFICE_ASSISTANT: "Office assistent",
    ROLE_STAFF: "Applicatiebeheer",
}


def role_label(key: str) -> str:
    """What a role is called on screen.

    A key with no label prints as itself: a group left in the database by an
    older version must stay visible on the roles screen, not turn into a blank tag.
    """
    return ROLE_LABELS.get(key, key)


def is_bdm(user) -> bool:
    """Whether the user holds the BDM role (Django group ``ROLE_BDM``).

    Used as a visibility gate: a BDM sees ended and future placements/assignments
    that are otherwise private to the placed colleague — see
    ``evaluate_placement_visibility``.
    """
    return user.is_authenticated and user.groups.filter(name=ROLE_BDM).exists()


def is_office_assistant(user) -> bool:
    """Whether the user holds the Office assistent role (Django group
    ``ROLE_OFFICE_ASSISTANT``).

    Spelled as the role, not as the Django permission the role happens to carry:
    ``rule(READ, ContractPeriod)`` names the same audience as
    ``Grant(Role(ROLE_OFFICE_ASSISTANT))``, and one audience answers the same on
    both sides. Asking ``rijksauth.change_user`` instead would let a superuser
    through here and not there.
    """
    return user.is_authenticated and user.groups.filter(name=ROLE_OFFICE_ASSISTANT).exists()


def is_staff_member(user) -> bool:
    """Whether the user does application administration (``STAFF_EMAILS``).

    Gates the maintenance pages (``/beheer/statistieken/``, ``/beheer/database/``).
    It carries no rights on assignments; those come from the BDM role.
    """
    return user.is_authenticated and user.email.lower() in settings.STAFF_EMAILS


def can_view_role_hours(user, placement) -> bool:
    """Whether the user may see the hours per week of a role.

    Agreed with Patrick (mail of 13 July 2026): the hours of a placed consultant
    are for who plans with them (BDM, Office assistent) and for the consultant
    themself, not for team mates. An open aanvraag has no one to protect, so its
    hours are visible to everyone who sees the opdracht.

    Application administration is not in that list: it runs the platform and
    carries nothing functional.

    The same audience as ``rule(READ, ContractPeriod)`` in ``permissions.py``,
    and spelled the same way; the role matrix prints it as "Uren van de rol van
    een collega zien".
    """
    if placement is None:
        return True
    # restricted_change_names builds the team rows with a request that has no
    # user, to see what an outsider sees; that outsider sees no hours.
    if user is None:
        return False
    colleague = getattr(user, "colleague", None)
    if colleague is not None and placement.colleague_id == colleague.id:
        return True
    return is_bdm(user) or is_office_assistant(user)


def may_change_email(editor, old: str, new: str) -> bool:
    """Moving a ``STAFF_EMAILS`` address moves application administration, so
    only an application administrator may; ``editor=None`` (the system) may not.

    ``old=""`` is a user being created, and the answer is the same: an account on
    such an address is an application administrator once it is claimed at login,
    whether it was moved there or born there.
    """
    old, new = old.lower(), new.lower()
    if old == new or (old not in settings.STAFF_EMAILS and new not in settings.STAFF_EMAILS):
        return True
    return editor is not None and is_staff_member(editor)


def may_view_role_matrix(user) -> bool:
    """Whether the user may read the role matrix (``/beheer/rollen/``): Office assistent,
    whose Beheer section it sits in, and application administration, which owns the roles.
    The page shows no data, so the gate is wide.
    """
    return user.has_perm("rijksauth.view_user") or is_staff_member(user)


def may_administer_roles(user) -> bool:
    """Whether the user may change someone's roles, from the row menu on the users
    page: Office assistent and application administration. Which roles they are
    then offered is ``may_grant``'s answer, in ``UserForm``.
    """
    return user.has_perm("rijksauth.change_user") or is_staff_member(user)


def may_view_users(user) -> bool:
    """Whether the user may open the users page (``/beheer/gebruikers/``): Office
    assistent, and whoever may grant roles, who picks the person there. Seeing the
    list is all that follows; Nieuwe gebruiker and Verwijderen ask their own Django
    permission, Bewerken asks ``may_administer_roles``.
    """
    return user.has_perm("rijksauth.view_user") or may_administer_roles(user)


def may_grant(_editor, role: str) -> bool:
    """Whether ``editor`` may grant or revoke ``role``; ``editor=None`` is the system.

    The one place the policy lives: ask it about any role rather than testing the
    role yourself, so restricting one later needs no caller changed.
    """
    # Applicatiebeheer is an address list, not a group: change STAFF_EMAILS and deploy.
    return role != ROLE_STAFF


def is_bdm_request(request) -> bool:
    """Whether the request's user holds the BDM role, resolved once per request,
    cached because the audit timeline calls it once per event.
    """
    user = getattr(request, "user", None)
    if user is None:
        return False
    if not hasattr(request, "wies_is_bdm"):
        request.wies_is_bdm = is_bdm(user)
    return request.wies_is_bdm


def setup_roles():
    roles = {
        ROLE_OFFICE_ASSISTANT: [
            (User, ["view_user", "add_user", "delete_user", "change_user"]),
            (
                LabelCategory,
                ["view_labelcategory", "add_labelcategory", "change_labelcategory", "delete_labelcategory"],
            ),
            (Label, ["view_label", "add_label", "change_label", "delete_label"]),
            (
                Suborganization,
                [
                    "view_suborganization",
                    "add_suborganization",
                    "change_suborganization",
                    "delete_suborganization",
                ],
            ),
            (OrganizationUnit, ["view_organizationunit"]),
        ],
        ROLE_CONSULTANT: [],
        ROLE_BDM: [
            (Assignment, ["add_assignment"]),
            (Service, ["add_service"]),
            (Placement, ["add_placement"]),
            (Colleague, ["add_colleague"]),
        ],
    }

    with transaction.atomic():
        for role_name, model_permissions in roles.items():
            group, _created = Group.objects.get_or_create(name=role_name)
            for model, codenames in model_permissions:
                content_type = ContentType.objects.get_for_model(model)
                for codename in codenames:
                    perm = Permission.objects.get(codename=codename, content_type=content_type)
                    group.permissions.add(perm)
