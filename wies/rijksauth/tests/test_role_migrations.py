"""Tests for the role data migration (0009): screen labels to keys, and both beheer
roles for the STAFF_EMAILS addresses once."""

import os
from unittest.mock import patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TransactionTestCase

APP = "rijksauth"
BEFORE = "0008_user_public_id"
ROLE_KEYS = "0009_role_keys"

#: (label before the migration, key after)
RENAMES = [
    ("Consultant", "consultant"),
    ("Business Development Manager", "business_manager"),
    ("Beheerder", "user_admin"),
]
STAFF = "applicatiebeheer@rijksoverheid.nl"
STAFF_ROLES = {"business_manager", "user_admin"}


class _MigrationTestCase(TransactionTestCase):
    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([(APP, target)])
        executor.loader.build_graph()

    def _apps_at(self, target):
        return MigrationExecutor(connection).loader.project_state((APP, target)).apps

    def _leaf(self):
        # Resolved from the graph, never hardcoded: migrating to a named target
        # that is already applied puts the executor in backwards mode and would
        # roll back every migration added after it.
        return MigrationLoader(connection).graph.leaf_nodes(APP)[0][1]

    def tearDown(self):
        self._migrate(self._leaf())

    def _migrate_with(self, target, staff_emails=""):
        """Runs with only ``staff_emails`` configured, so an address set in the
        surrounding environment cannot answer for the test."""
        with patch.dict(os.environ, {"STAFF_EMAILS": staff_emails}):
            self._migrate(target)

    def _group(self, target, name):
        return self._apps_at(target).get_model("auth", "Group").objects.filter(name=name).first()

    def _group_names(self, target):
        return set(self._apps_at(target).get_model("auth", "Group").objects.values_list("name", flat=True))

    def _roles_of(self, target, user_id):
        user = self._apps_at(target).get_model(APP, "User").objects.get(pk=user_id)
        return set(user.groups.values_list("name", flat=True))


class RoleKeysRenameTest(_MigrationTestCase):
    def setUp(self):
        self._migrate(BEFORE)
        apps = self._apps_at(BEFORE)
        self.group_model = apps.get_model("auth", "Group")
        permission = apps.get_model("auth", "Permission").objects.get(codename="change_user")
        user_model = apps.get_model(APP, "User")
        self.member_ids = {}
        for label, _key in RENAMES:
            member_id = user_model.objects.create(email=f"{label.split()[0].lower()}@rijksoverheid.nl").pk
            group = self.group_model.objects.create(name=label)
            group.permissions.add(permission)
            group.user_set.add(member_id)
            self.member_ids[label] = member_id

    def _assert_carries(self, target, name, label):
        group = self._group(target, name)
        assert group is not None
        assert list(group.user_set.values_list("pk", flat=True)) == [self.member_ids[label]]
        assert list(group.permissions.values_list("codename", flat=True)) == ["change_user"]

    def test_every_label_becomes_its_key(self):
        self._migrate_with(ROLE_KEYS)

        names = self._group_names(ROLE_KEYS)
        assert {key for _label, key in RENAMES} <= names
        assert not {label for label, _key in RENAMES} & names

    def test_members_and_permissions_survive_the_rename(self):
        self._migrate_with(ROLE_KEYS)

        for label, key in RENAMES:
            with self.subTest(group=label):
                self._assert_carries(ROLE_KEYS, key, label)

    def test_an_existing_key_group_is_merged(self):
        """``setup_roles()`` creates the groups by key on every start, so the key
        may already be there when the migration runs."""
        for _label, key in RENAMES:
            self.group_model.objects.create(name=key)

        self._migrate_with(ROLE_KEYS)

        for label, key in RENAMES:
            with self.subTest(group=label):
                assert self._group(ROLE_KEYS, label) is None
                self._assert_carries(ROLE_KEYS, key, label)
        # One group per key: a merge that created a second row would leave the
        # app matching on only one of them.
        names = list(self._apps_at(ROLE_KEYS).get_model("auth", "Group").objects.values_list("name", flat=True))
        assert len(names) == len(set(names))

    def test_the_rename_is_reversible(self):
        self._migrate_with(ROLE_KEYS)
        self._migrate_with(BEFORE)

        for label, key in RENAMES:
            with self.subTest(group=label):
                assert self._group(BEFORE, key) is None
                self._assert_carries(BEFORE, label, label)


class StaffEmailsBackfillTest(_MigrationTestCase):
    def setUp(self):
        self._migrate(BEFORE)
        user_model = self._apps_at(BEFORE).get_model(APP, "User")
        self.staff_id = user_model.objects.create(email="Applicatiebeheer@Rijksoverheid.nl").pk
        self.other_id = user_model.objects.create(email="ander@rijksoverheid.nl").pk

    def test_staff_emails_receive_both_beheer_roles(self):
        self._migrate_with(ROLE_KEYS, f" {STAFF} , nobody@rijksoverheid.nl")

        assert self._roles_of(ROLE_KEYS, self.staff_id) == STAFF_ROLES

    def test_an_address_outside_the_list_is_left_alone(self):
        self._migrate_with(ROLE_KEYS, STAFF)

        assert self._roles_of(ROLE_KEYS, self.other_id) == set()

    def test_without_configured_addresses_nobody_is_granted_anything(self):
        self._migrate_with(ROLE_KEYS)

        assert self._roles_of(ROLE_KEYS, self.staff_id) == set()

    def test_the_grant_lands_in_groups_the_app_created_first(self):
        """A container that ran ``setup_roles()`` before migrating already has the
        key groups with members on them; both sides keep their role."""
        apps = self._apps_at(BEFORE)
        group_model = apps.get_model("auth", "Group")
        early_id = apps.get_model(APP, "User").objects.create(email="vroeg@rijksoverheid.nl").pk
        for name in sorted(STAFF_ROLES):
            group_model.objects.create(name=name).user_set.add(early_id)

        self._migrate_with(ROLE_KEYS, STAFF)

        assert self._roles_of(ROLE_KEYS, early_id) == STAFF_ROLES
        assert self._roles_of(ROLE_KEYS, self.staff_id) == STAFF_ROLES

    def test_backwards_and_forwards_again(self):
        """Backwards renames the keys back to labels and takes no grant away;
        forwards again lands on the keys."""
        with patch.dict(os.environ, {"STAFF_EMAILS": STAFF}):
            self._migrate(ROLE_KEYS)
            self._migrate(BEFORE)

            assert self._roles_of(BEFORE, self.staff_id) == {"Business Development Manager", "Beheerder"}

            self._migrate(ROLE_KEYS)

        assert self._roles_of(ROLE_KEYS, self.staff_id) == STAFF_ROLES
