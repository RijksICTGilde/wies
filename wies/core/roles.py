"""Group/permission setup and role predicates for Beheerder, Consultant, BDM.

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


def is_bdm(user) -> bool:
    """Whether the user holds the BDM role (Django group ``BDM_GROUP_NAME``).

    Used as a visibility gate: a BDM sees ended and future placements/assignments
    that are otherwise private to the placed colleague — see
    ``evaluate_placement_visibility``.
    """
    return user.is_authenticated and user.groups.filter(name=BDM_GROUP_NAME).exists()


def is_staff_member(user) -> bool:
    """Whether the given user is a member of the support staff cohort (``STAFF_EMAILS``).

    Used both as a page-access gate (``/beheer/statistieken/``, ``/beheer/database/``)
    and as a per-row edit- and visibility-predicate (e.g. in ``update_assignment``
    and ``is_bdm_or_staff``).
    """
    return user.is_authenticated and user.email.lower() in settings.STAFF_EMAILS


def is_bdm_or_staff(request) -> bool:
    """Whether the request's user holds the BDM role or is a support-staff member,
    resolved once per request, cached because the audit timeline calls it once per event.
    """
    user = getattr(request, "user", None)
    if user is None:
        return False
    if not hasattr(request, "wies_is_bdm_or_staff"):
        request.wies_is_bdm_or_staff = is_bdm(user) or is_staff_member(user)
    return request.wies_is_bdm_or_staff


def setup_roles():
    # Define roles
    roles = {
        "Beheerder": [
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
