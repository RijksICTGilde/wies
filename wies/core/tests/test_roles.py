from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import Group

from wies.core.models import User, LabelCategory, Label
from wies.core.roles import setup_roles


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
        self.assertTrue(Group.objects.filter(name='Beheerder').exists())

    def test_setup_roles_grants_user_permissions(self):
        """Test that Beheerder group has all user management permissions"""
        setup_roles()

        admin_group = Group.objects.get(name='Beheerder')

        # Check all expected permissions
        expected_permissions = ['view_user', 'add_user', 'delete_user', 'change_user']
        for codename in expected_permissions:
            self.assertTrue(
                admin_group.permissions.filter(codename=codename).exists(),
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
        admin_group = Group.objects.get(name='Beheerder')
        admin_user.groups.add(admin_group)

        client = Client()
        client.force_login(admin_user)

        # Test user list access
        response = client.get(reverse('admin-users'))
        self.assertEqual(response.status_code, 200)

        # Test user create form access
        response = client.get(reverse('user-create'))
        self.assertEqual(response.status_code, 200)

        # Test user creation
        category, _ = LabelCategory.objects.get_or_create(name='Merk', defaults={'color': '#0066CC'})
        label = Label.objects.create(name="Test Brand", category=category)
        response = client.post(reverse('user-create'), {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'labels': [label.id],
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

        # Test user deletion
        user_to_delete = User.objects.create(
            username="delete_me",
            email="deleteme@example.com",
            first_name="Delete",
            last_name="Me",
        )
        response = client.post(reverse('user-delete', args=[user_to_delete.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(id=user_to_delete.id).exists())
