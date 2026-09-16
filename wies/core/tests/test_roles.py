from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import Label, LabelCategory
from wies.core.roles import setup_roles

User = get_user_model()


class RBACSetupTest(TestCase):
    """Integration tests for RBAC role setup"""

    def test_setup_roles_creates_assignment_admin_group_without_permissions(self):
        """Opdrachtbeheer's rights are all rule-based, and nobody is put in it."""
        Group.objects.filter(name="Opdrachtbeheer").delete()
        setup_roles()

        group = Group.objects.get(name="Opdrachtbeheer")
        assert not group.permissions.exists()
        assert not group.user_set.exists()

    @override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
    def test_setup_roles_does_not_grant_assignment_admin_to_staff(self):
        """setup_roles() runs on every start; a staff member who removed
        Opdrachtbeheer from themselves must not get it back."""
        User.objects.create_user(email="staff@rijksoverheid.nl", first_name="S", last_name="T")

        setup_roles()

        assert not Group.objects.get(name="Opdrachtbeheer").user_set.exists()

    def test_setup_roles_creates_user_admin_group(self):
        """Test that setup_roles creates the Gebruikersbeheer group"""
        setup_roles()

        # Gebruikersbeheer group should exist
        assert Group.objects.filter(name="Gebruikersbeheer").exists()

    def test_setup_roles_grants_user_permissions(self):
        """Test that Gebruikersbeheer group has all user management permissions"""
        setup_roles()

        admin_group = Group.objects.get(name="Gebruikersbeheer")

        # Check all expected permissions
        expected_permissions = ["view_user", "add_user", "delete_user", "change_user"]
        for codename in expected_permissions:
            assert admin_group.permissions.filter(codename=codename).exists(), (
                f"Gebruikersbeheer group missing {codename} permission"
            )

    def test_setup_roles_grants_suborganization_permissions(self):
        """Test that Gebruikersbeheer group can manage suborganizations (merken)"""
        setup_roles()

        admin_group = Group.objects.get(name="Gebruikersbeheer")

        expected_permissions = [
            "view_suborganization",
            "add_suborganization",
            "change_suborganization",
            "delete_suborganization",
        ]
        for codename in expected_permissions:
            assert admin_group.permissions.filter(codename=codename).exists(), (
                f"Gebruikersbeheer group missing {codename} permission"
            )

    def test_beheerder_group_user_can_access_views(self):
        """Test that a user in Gebruikersbeheer group can access all user management views"""
        setup_roles()

        # Create user and add to Gebruikersbeheer group
        admin_user = User.objects.create_user(
            email="admin@rijksoverheid.nl",
            first_name="Admin",
            last_name="User",
        )
        admin_group = Group.objects.get(name="Gebruikersbeheer")
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
        category, _ = LabelCategory.objects.get_or_create(name="Expertise", defaults={"color": "#0066CC"})
        label = Label.objects.create(name="AI", category=category)
        response = client.post(
            reverse("user-create"),
            {
                "first_name": "New",
                "last_name": "User",
                "email": "newuser@rijksoverheid.nl",
                "labels": [label.public_id],
            },
        )
        assert response.status_code == 302
        assert User.objects.filter(email="newuser@rijksoverheid.nl").exists()

        # Test user deletion
        user_to_delete = User.objects.create_user(
            email="deleteme@rijksoverheid.nl",
            first_name="Delete",
            last_name="Me",
        )
        response = client.post(reverse("user-delete", args=[user_to_delete.public_id]))
        assert response.status_code == 200
        assert not User.objects.filter(id=user_to_delete.id).exists()
