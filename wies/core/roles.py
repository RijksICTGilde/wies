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
)

User = get_user_model()


def user_can_edit_assignment(user, assignment):
    """Any-field access: admin perm, owner, or a placed colleague. Wies-sourced only."""
    if not user.is_authenticated:
        return False
    if assignment.source not in ("wies", ""):
        return False
    if user.has_perm("core.change_assignment"):
        return True
    if not hasattr(user, "colleague"):
        return False
    if assignment.owner and assignment.owner.id == user.colleague.id:
        return True
    return Placement.objects.filter(service__assignment=assignment, colleague__id=user.colleague.id).exists()


def user_is_assignment_owner_or_admin(user, assignment):
    """Management-field access (owner/period/organizations/team). Excludes placed consultants."""
    if not user.is_authenticated:
        return False
    if assignment.source not in ("wies", ""):
        return False
    if user.has_perm("core.change_assignment"):
        return True
    if not hasattr(user, "colleague"):
        return False
    return bool(assignment.owner and assignment.owner.id == user.colleague.id)


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
            (OrganizationUnit, ["view_organizationunit"]),
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
