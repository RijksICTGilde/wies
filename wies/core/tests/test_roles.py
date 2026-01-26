from django.contrib.auth.models import AnonymousUser, Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import Label, LabelCategory, OrganizationUnit, User
from wies.core.roles import setup_roles, user_can_edit_organization, user_can_view_organization


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class RBACSetupTest(TestCase):
    """Integration tests for RBAC role setup"""

    def test_setup_roles_creates_beheerder_group(self):
        """Test that setup_roles creates the Beheerder group"""
        setup_roles()

        # Beheerder group should exist
        assert Group.objects.filter(name="Beheerder").exists()

    def test_setup_roles_grants_user_permissions(self):
        """Test that Beheerder group has all user management permissions"""
        setup_roles()

        admin_group = Group.objects.get(name="Beheerder")

        # Check all expected permissions
        expected_permissions = ["view_user", "add_user", "delete_user", "change_user"]
        for codename in expected_permissions:
            assert admin_group.permissions.filter(codename=codename).exists(), (
                f"Beheerder group missing {codename} permission"
            )

    def test_beheerder_group_user_can_access_views(self):
        """Test that a user in Beheerder group can access all user management views"""
        setup_roles()

        # Create user and add to Beheerder group
        admin_user = User.objects.create(
            username="admin_user",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
        )
        admin_group = Group.objects.get(name="Beheerder")
        admin_user.groups.add(admin_group)

        client = Client()
        client.force_login(admin_user)

        # Test user list access
        response = client.get(reverse("admin-users"))
        assert response.status_code == 200

        # Test user create form access
        response = client.get(reverse("user-create"))
        assert response.status_code == 200

        # Test user creation
        category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        label = Label.objects.create(name="Test Brand", category=category)
        response = client.post(
            reverse("user-create"),
            {
                "first_name": "New",
                "last_name": "User",
                "email": "newuser@example.com",
                "labels": [label.id],
            },
        )
        assert response.status_code == 302
        assert User.objects.filter(email="newuser@example.com").exists()

        # Test user deletion
        user_to_delete = User.objects.create(
            username="delete_me",
            email="deleteme@example.com",
            first_name="Delete",
            last_name="Me",
        )
        response = client.post(reverse("user-delete", args=[user_to_delete.id]))
        assert response.status_code == 200
        assert not User.objects.filter(id=user_to_delete.id).exists()


class OrganizationUnitPermissionTest(TestCase):
    """Tests for organization permission functions."""

    def setUp(self):
        setup_roles()
        self.organization = OrganizationUnit.objects.create(
            name="Test Org",
            organization_type="gemeente",
        )

    def test_view_organization_authenticated(self):
        """Authenticated users can view organizations."""
        user = User.objects.create_user(username="viewer@test.nl", email="viewer@test.nl")
        assert user_can_view_organization(user, self.organization)

    def test_view_organization_unauthenticated(self):
        """Unauthenticated users cannot view organizations."""
        anon = AnonymousUser()
        assert not user_can_view_organization(anon, self.organization)

    def test_edit_organization_beheerder(self):
        """Beheerders can edit organizations."""
        user = User.objects.create_user(username="beheerder@test.nl", email="beheerder@test.nl")
        user.groups.add(Group.objects.get(name="Beheerder"))
        assert user_can_edit_organization(user, self.organization)

    def test_edit_organization_regular_user(self):
        """Regular users cannot edit organizations."""
        user = User.objects.create_user(username="regular@test.nl", email="regular@test.nl")
        assert not user_can_edit_organization(user, self.organization)

    def test_edit_organization_unauthenticated(self):
        """Unauthenticated users cannot edit organizations."""
        anon = AnonymousUser()
        assert not user_can_edit_organization(anon, self.organization)
