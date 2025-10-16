from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied


def user_can_edit_assignments(user):
    """
    Check if user can edit assignments (is in BDM group or is superuser)

    Args:
        user: Django User instance

    Returns:
        bool: True if user can edit assignments
    """
    return user.groups.filter(name='BDM').exists() or user.is_superuser


class UserCanEditAssignmentsMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to users who can edit assignments.
    Used for assignment create/update/delete operations.
    """

    def test_func(self):
        """Check if user can edit assignments"""
        return user_can_edit_assignments(self.request.user)

    def handle_no_permission(self):
        """Raise PermissionDenied with custom message"""
        raise PermissionDenied("Je moet lid zijn van de BDM groep om opdrachten te kunnen aanpassen.")
