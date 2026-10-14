import importlib
import os
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.settings import base
from wies.core.models import Label, LabelCategory
from wies.core.roles import (
    ROLE_BUSINESS_MANAGER,
    ROLE_LABELS,
    ROLE_STAFF,
    ROLE_USER_ADMIN,
    is_business_manager,
    is_staff_member,
    may_grant,
    may_view_role_matrix,
    role_label,
    setup_roles,
)

User = get_user_model()


class RBACSetupTest(TestCase):
    """Integration tests for RBAC role setup"""

    @override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
    def test_setup_roles_does_not_grant_business_manager_to_staff(self):
        """setup_roles() runs on every start; a staff member who removed Business Manager from
        themselves must not get it back."""
        User.objects.create_user(email="staff@rijksoverheid.nl", first_name="S", last_name="T")

        setup_roles()

        assert not Group.objects.get(name=ROLE_BUSINESS_MANAGER).user_set.exists()

    def test_setup_roles_creates_exactly_the_roles_that_have_a_label(self):
        """Both sides of a role's name, which drift apart in silence: a group with
        no entry in ``ROLE_LABELS`` prints its key on the user sheet, and a label
        with no group can never be granted. The Applicatiebeheerder is absent on purpose:
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
        """Test that setup_roles creates the Gebruikersbeheerder group"""
        setup_roles()

        # Gebruikersbeheerder group should exist
        assert Group.objects.filter(name=ROLE_USER_ADMIN).exists()

    def test_setup_roles_grants_user_permissions(self):
        """Test that the Gebruikersbeheerder group has all user management permissions"""
        setup_roles()

        admin_group = Group.objects.get(name=ROLE_USER_ADMIN)

        # Check all expected permissions
        expected_permissions = ["view_user", "add_user", "delete_user", "change_user"]
        for codename in expected_permissions:
            assert admin_group.permissions.filter(codename=codename).exists(), (
                f"Gebruikersbeheerder group missing {codename} permission"
            )

    def test_setup_roles_grants_suborganization_permissions(self):
        """Test that the Gebruikersbeheerder group can manage suborganizations (merken)"""
        setup_roles()

        admin_group = Group.objects.get(name=ROLE_USER_ADMIN)

        expected_permissions = [
            "view_suborganization",
            "add_suborganization",
            "change_suborganization",
            "delete_suborganization",
        ]
        for codename in expected_permissions:
            assert admin_group.permissions.filter(codename=codename).exists(), (
                f"Gebruikersbeheerder group missing {codename} permission"
            )

    def test_beheerder_group_user_can_access_views(self):
        """Test that a user in the Gebruikersbeheerder group can access all user management views"""
        setup_roles()

        # Create user and add to the Gebruikersbeheerder group
        admin_user = User.objects.create_user(
            email="admin@rijksoverheid.nl",
            first_name="Admin",
            last_name="User",
        )
        admin_group = Group.objects.get(name=ROLE_USER_ADMIN)
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


@override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
class LabelRenameCostsOneStringTest(TestCase):
    """What the key/label split promises, and what this round leaned on twice:
    renaming a role is a text change, not a data migration.

    The promise holds because nothing stored and nothing matched carries the
    label. The one thing that does follow it is the CSV import header, by design
    (``CSV_ROLE_COLUMNS`` is built from ``ROLE_LABELS``, so an import file keeps
    reading in words). That is the same string, not a second one.
    """

    #: Every label replaced, so no assertion below can pass on an unmoved name.
    RENAMED = {key: f"Rol {index}" for index, key in enumerate(ROLE_LABELS)}

    def setUp(self):
        setup_roles()
        self.user = User.objects.create_user(email="houder@rijksoverheid.nl", first_name="H", last_name="R")
        self.user.groups.add(Group.objects.get(name=ROLE_USER_ADMIN), Group.objects.get(name=ROLE_BUSINESS_MANAGER))
        self.stored = set(Group.objects.values_list("name", flat=True))
        self.held = set(self.user.groups.values_list("name", flat=True))

    def test_renaming_every_label_moves_no_group_and_no_membership(self):
        with patch.dict(ROLE_LABELS, self.RENAMED, clear=True):
            setup_roles()  # runs on every container start, so it runs under the new labels too

            assert set(Group.objects.values_list("name", flat=True)) == self.stored
            assert set(User.objects.get(pk=self.user.pk).groups.values_list("name", flat=True)) == self.held

    def _gates(self):
        user = User.objects.get(pk=self.user.pk)  # fresh, so no permissions are cached
        return {
            "is_business_manager": is_business_manager(user),
            "is_staff_member": is_staff_member(user),
            "may_view_role_matrix": may_view_role_matrix(user),
            "may_grant": {role: may_grant(user, role) for role in ROLE_LABELS},
        }

    def test_renaming_every_label_leaves_every_gate_where_it_was(self):
        """The gates ask the key, so none of them notices.

        The expected answers are spelled out as well as compared: a gate that
        asked the label instead would be wrong before and after the rename alike,
        and comparing it only with itself would call that unmoved.
        """
        expected = {
            "is_business_manager": True,  # setUp gave the holder this role
            "is_staff_member": False,  # the address list holds a different address
            "may_view_role_matrix": True,  # through view_user, which the role carries
            "may_grant": dict.fromkeys(ROLE_LABELS, True) | {ROLE_STAFF: False},
        }
        assert self._gates() == expected

        with patch.dict(ROLE_LABELS, self.RENAMED, clear=True):
            assert self._gates() == expected

    def test_the_screen_follows_the_label_though(self):
        """Otherwise the rename would cost nothing because it did nothing."""
        with patch.dict(ROLE_LABELS, self.RENAMED, clear=True):
            assert [role_label(key) for key in self.RENAMED] == list(self.RENAMED.values())

    def test_no_migration_names_a_label_this_round_renamed(self):
        """A migration is frozen in time, so it spells the group name of its own day.
        Both names this round moved were already keys by then, so no migration may
        mention either: one that did would be rewriting history to match a screen.
        """
        renamed_this_round = ("Gebruikersbeheerder", "Applicatiebeheerder")
        for path in sorted((Path(settings.BASE_DIR) / "wies").glob("*/migrations/*.py")):
            body = path.read_text(encoding="utf-8")
            for name in renamed_this_round:
                with self.subTest(migration=path.name, label=name):
                    assert name not in body


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
