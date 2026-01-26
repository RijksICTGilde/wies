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
    User,
)


def user_can_view_organization(user, organization=None) -> bool:
    """All authenticated users can view organizations."""
    return user.is_authenticated


def user_can_edit_organization(user, organization=None) -> bool:
    """Only Beheerders can edit organization units."""
    if not user.is_authenticated:
        return False
    return user.has_perm("core.change_organizationunit")


def user_can_edit_assignment(user, assignment):
    """
    Check if a user can edit an assignment.

    A user can edit an assignment if they:
    - Have the 'core.change_assignment' permission, OR
    - Are the BDM (owner) of the assignment, OR
    - Are assigned to the assignment as a colleague

    Args:
        user: User object to check permissions for
        assignment: Assignment object to check edit permissions against

    Returns:
        bool: True if user can edit the assignment, False otherwise
    """
    if not user.is_authenticated:
        return False

    # Check permission
    if user.has_perm("core.change_assignment"):
        return True

    # Check if user has a colleague profile
    if not hasattr(user, "colleague"):
        return False

    # Check if user is the owner (BDM)
    if assignment.owner and assignment.owner.id == user.colleague.id:
        return True

    # Check if user is assigned to the assignment
    return Placement.objects.filter(service__assignment=assignment, colleague__id=user.colleague.id).exists()


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
                OrganizationUnit,
                ["view_organizationunit", "add_organizationunit", "change_organizationunit", "delete_organizationunit"],
            ),
        ],
        "Consultant": [],
        "Business Development Manager": [
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
