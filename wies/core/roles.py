"""Group/permission setup for Beheerder, Consultant, BDM.

Per-row authorization for inline-edit and views lives in
``wies/core/permissions.py``. This module is concerned only with
Django Group definitions and what permissions they carry.
"""

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


def viewer_is_bdm(request) -> bool:
    """``is_bdm`` for the request's user, resolved once per request.

    Cached on the request because several surfaces need the flag while building
    one response (team rows, timeline events, the colleague panel) and ``is_bdm``
    costs a groups query each time — the answer is the same for the whole request.
    """
    user = getattr(request, "user", None)
    if user is None:
        return False
    if not hasattr(request, "wies_viewer_is_bdm"):
        request.wies_viewer_is_bdm = is_bdm(user)
    return request.wies_viewer_is_bdm


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
