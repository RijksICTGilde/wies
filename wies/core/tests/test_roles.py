import importlib
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.settings import base
from wies.core.models import Label, LabelCategory
from wies.core.roles import ROLE_BDM, ROLE_LABELS, ROLE_OFFICE_ASSISTANT, ROLE_STAFF, setup_roles

User = get_user_model()


class RBACSetupTest(TestCase):
    """Integration tests for RBAC role setup"""

    @override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
    def test_setup_roles_does_not_grant_bdm_to_staff(self):
        """setup_roles() runs on every start; a staff member who removed BDM from
        themselves must not get it back."""
        User.objects.create_user(email="staff@rijksoverheid.nl", first_name="S", last_name="T")

        setup_roles()

        assert not Group.objects.get(name=ROLE_BDM).user_set.exists()

    def test_setup_roles_creates_exactly_the_roles_that_have_a_label(self):
        """Both sides of a role's name, which drift apart in silence: a group with
        no entry in ``ROLE_LABELS`` prints its key on the user sheet, and a label
        with no group can never be granted. Applicatiebeheer is absent on purpose:
        an address list rather than a group.

        It is also what keeps ``rijksauth/0012`` done. That migration drops the
        Opdrachtbeheer group, and ``setup_roles()`` runs on every container start,
        so a role put back here would return on the next deploy and stand on the
        user sheet under its key.
        """
        Group.objects.all().delete()

        setup_roles()

        assert set(Group.objects.values_list("name", flat=True)) == set(ROLE_LABELS) - {ROLE_STAFF}

    def test_setup_roles_creates_user_admin_group(self):
        """Test that setup_roles creates the Office assistent group"""
        setup_roles()

        # Office assistent group should exist
        assert Group.objects.filter(name=ROLE_OFFICE_ASSISTANT).exists()

    def test_setup_roles_grants_user_permissions(self):
        """Test that Office assistent group has all user management permissions"""
        setup_roles()

        admin_group = Group.objects.get(name=ROLE_OFFICE_ASSISTANT)

        # Check all expected permissions
        expected_permissions = ["view_user", "add_user", "delete_user", "change_user"]
        for codename in expected_permissions:
            assert admin_group.permissions.filter(codename=codename).exists(), (
                f"Office assistent group missing {codename} permission"
            )

    def test_setup_roles_grants_suborganization_permissions(self):
        """Test that Office assistent group can manage suborganizations (merken)"""
        setup_roles()

        admin_group = Group.objects.get(name=ROLE_OFFICE_ASSISTANT)

        expected_permissions = [
            "view_suborganization",
            "add_suborganization",
            "change_suborganization",
            "delete_suborganization",
        ]
        for codename in expected_permissions:
            assert admin_group.permissions.filter(codename=codename).exists(), (
                f"Office assistent group missing {codename} permission"
            )

    def test_beheerder_group_user_can_access_views(self):
        """Test that a user in Office assistent group can access all user management views"""
        setup_roles()

        # Create user and add to Office assistent group
        admin_user = User.objects.create_user(
            email="admin@rijksoverheid.nl",
            first_name="Admin",
            last_name="User",
        )
        admin_group = Group.objects.get(name=ROLE_OFFICE_ASSISTANT)
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


class StaffEmailsSettingTest(SimpleTestCase):
    """``settings.STAFF_EMAILS`` in ``config/settings/base.py``.

    Reloading the module re-runs the assignment; ``django.conf.settings`` copied
    its values at startup, so the reload cannot leak into other tests.
    """

    def _emails_with(self, **env):
        with patch.dict(os.environ, {"STAFF_EMAILS": "", **env}):
            return importlib.reload(base).STAFF_EMAILS

    def test_addresses_are_split_trimmed_and_lowercased(self):
        emails = self._emails_with(STAFF_EMAILS=" Een@rijksoverheid.nl , Twee@rijksoverheid.nl ")

        assert emails == ["een@rijksoverheid.nl", "twee@rijksoverheid.nl"]

    def test_an_unset_key_gives_an_empty_list(self):
        """Not [""]: an empty entry would match a user without an email address."""
        assert self._emails_with() == []
