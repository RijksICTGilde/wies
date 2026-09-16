"""Group/permission setup and role predicates for Gebruikersbeheer, Opdrachtbeheer,
Consultant and BDM. The authority model is described in ``features/roles.md``.

Per-row authorization for inline-edit and views lives in
``wies/core/permissions.py``. This module owns the Django Group definitions,
the group-membership / staff predicates they build on, and the request-cached
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

BDM_GROUP_NAME = "Business Development Manager"
USER_ADMIN_GROUP_NAME = "Gebruikersbeheer"
ASSIGNMENT_ADMIN_GROUP_NAME = "Opdrachtbeheer"

# Roles that create privilege, so only platform administration (``STAFF_EMAILS``)
# may grant or revoke them.
STAFF_GRANTED_GROUPS = frozenset({USER_ADMIN_GROUP_NAME, ASSIGNMENT_ADMIN_GROUP_NAME})


def is_bdm(user) -> bool:
    """Whether the user holds the BDM role (Django group ``BDM_GROUP_NAME``).

    Used as a visibility gate: a BDM sees ended and future placements/assignments
    that are otherwise private to the placed colleague — see
    ``evaluate_placement_visibility``.
    """
    return user.is_authenticated and user.groups.filter(name=BDM_GROUP_NAME).exists()


def is_assignment_admin(user) -> bool:
    """Whether the user may act on any assignment (Django group
    ``ASSIGNMENT_ADMIN_GROUP_NAME``)."""
    return user.is_authenticated and user.groups.filter(name=ASSIGNMENT_ADMIN_GROUP_NAME).exists()


def is_staff_member(user) -> bool:
    """Whether the user does platform administration (``STAFF_EMAILS``).

    Gates the platform pages (``/beheer/statistieken/``, ``/beheer/database/``)
    and is the only authority that may grant ``STAFF_GRANTED_GROUPS``. It carries
    no rights on assignments; those come from ``is_assignment_admin``.
    """
    return user.is_authenticated and user.email.lower() in settings.STAFF_EMAILS


def is_bdm_or_assignment_admin(request) -> bool:
    """Whether the request's user holds the BDM or the Opdrachtbeheer role,
    resolved once per request, cached because the audit timeline calls it once per event.
    """
    user = getattr(request, "user", None)
    if user is None:
        return False
    if not hasattr(request, "wies_is_bdm_or_assignment_admin"):
        request.wies_is_bdm_or_assignment_admin = is_bdm(user) or is_assignment_admin(user)
    return request.wies_is_bdm_or_assignment_admin


def setup_roles():
    # Define roles
    roles = {
        USER_ADMIN_GROUP_NAME: [
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
        "Consultant": [],
        ASSIGNMENT_ADMIN_GROUP_NAME: [],
        BDM_GROUP_NAME: [
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
