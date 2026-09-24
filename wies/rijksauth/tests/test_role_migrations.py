"""Tests for the role data migrations: the Opdrachtbeheer backfill (0009), the
Beheerder -> Gebruikersbeheer rename (0010) and the move to role keys (0011)."""

import os
from unittest.mock import patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TransactionTestCase

APP = "rijksauth"
BEFORE_BACKFILL = "0008_user_public_id"
BACKFILL = "0009_backfill_assignment_admin"
RENAME = "0010_rename_beheerder_group"
KEYS = "0011_role_keys"


class _MigrationTestCase(TransactionTestCase):
    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([(APP, target)])
        executor.loader.build_graph()

    def _apps_at(self, target):
        return MigrationExecutor(connection).loader.project_state((APP, target)).apps

    def _migrate_to_latest(self):
        # Resolved from the graph, never hardcoded: migrating to a named target
        # that is already applied puts the executor in backwards mode and would
        # roll back every migration added after it.
        self._migrate(MigrationLoader(connection).graph.leaf_nodes(APP)[0][1])

    def tearDown(self):
        self._migrate_to_latest()


class BackfillAssignmentAdminMigrationTest(_MigrationTestCase):
    def setUp(self):
        self._migrate(BEFORE_BACKFILL)
        user_model = self._apps_at(BEFORE_BACKFILL).get_model(APP, "User")
        self.staff_id = user_model.objects.create(email="Staff@Rijksoverheid.nl").pk
        self.other_id = user_model.objects.create(email="other@rijksoverheid.nl").pk

    def _groups_of(self, user_id):
        user_model = self._apps_at(BACKFILL).get_model(APP, "User")
        return set(user_model.objects.get(pk=user_id).groups.values_list("name", flat=True))

    def _backfill_with(self, **env):
        """Runs the backfill with only ``env`` configured: the address key is emptied
        first, so an address set in the surrounding environment cannot answer for the
        test."""
        with patch.dict(os.environ, {"STAFF_EMAILS": "", **env}):
            self._migrate(BACKFILL)

    def test_staff_emails_receive_assignment_admin(self):
        """The set is exact: user administration was never on this address list, so the
        backfill may not hand it out. The role still carries its pre-0011 name here."""
        self._backfill_with(STAFF_EMAILS=" staff@rijksoverheid.nl , nobody@rijksoverheid.nl")

        assert self._groups_of(self.staff_id) == {"Opdrachtbeheer"}
        assert self._groups_of(self.other_id) == set()

    def test_group_is_created_without_configured_addresses(self):
        self._backfill_with()

        group_model = self._apps_at(BACKFILL).get_model("auth", "Group")
        assert group_model.objects.filter(name="Opdrachtbeheer").exists()
        assert self._groups_of(self.staff_id) == set()


class RenameUserAdminGroupMigrationTest(_MigrationTestCase):
    def setUp(self):
        self._migrate(BACKFILL)
        apps = self._apps_at(BACKFILL)
        self.group_model = apps.get_model("auth", "Group")
        self.permission_model = apps.get_model("auth", "Permission")
        user_model = apps.get_model(APP, "User")
        self.user_id = user_model.objects.create(email="beheer@rijksoverheid.nl").pk
        self.permission = self.permission_model.objects.get(codename="change_user")
        old = self.group_model.objects.create(name="Beheerder")
        old.permissions.add(self.permission)
        old.user_set.add(self.user_id)

    def _group(self, target, name):
        return self._apps_at(target).get_model("auth", "Group").objects.filter(name=name).first()

    def _assert_carries_members_and_permissions(self, group):
        assert group is not None
        assert list(group.user_set.values_list("pk", flat=True)) == [self.user_id]
        assert list(group.permissions.values_list("codename", flat=True)) == ["change_user"]

    def test_group_is_renamed_with_members_and_permissions(self):
        self._migrate(RENAME)

        assert self._group(RENAME, "Beheerder") is None
        self._assert_carries_members_and_permissions(self._group(RENAME, "Gebruikersbeheer"))

    def test_existing_target_group_is_merged(self):
        self.group_model.objects.create(name="Gebruikersbeheer")

        self._migrate(RENAME)

        assert self._group(RENAME, "Beheerder") is None
        self._assert_carries_members_and_permissions(self._group(RENAME, "Gebruikersbeheer"))

    def test_rename_is_reversible(self):
        self._migrate(RENAME)
        self._migrate(BACKFILL)

        assert self._group(BACKFILL, "Gebruikersbeheer") is None
        self._assert_carries_members_and_permissions(self._group(BACKFILL, "Beheerder"))


class RoleKeyMigrationTest(_MigrationTestCase):
    """0011 turns ``Group.name`` into a key, so a later rename is a label change."""

    def setUp(self):
        self._migrate(RENAME)
        apps = self._apps_at(RENAME)
        self.group_model = apps.get_model("auth", "Group")
        self.permission_model = apps.get_model("auth", "Permission")
        user_model = apps.get_model(APP, "User")
        self.user_id = user_model.objects.create(email="office@rijksoverheid.nl").pk
        # All four spelled out: 0009's Opdrachtbeheer row is gone once an earlier
        # TransactionTestCase has flushed the database.
        for name in ("Consultant", "Business Development Manager", "Gebruikersbeheer", "Opdrachtbeheer"):
            self.group_model.objects.get_or_create(name=name)
        office = self.group_model.objects.get(name="Gebruikersbeheer")
        office.permissions.add(self.permission_model.objects.get(codename="change_user"))
        office.user_set.add(self.user_id)

    def _names(self, target):
        return set(self._apps_at(target).get_model("auth", "Group").objects.values_list("name", flat=True))

    def _group(self, target, name):
        return self._apps_at(target).get_model("auth", "Group").objects.filter(name=name).first()

    def _assert_carries_members_and_permissions(self, group):
        assert group is not None
        assert list(group.user_set.values_list("pk", flat=True)) == [self.user_id]
        assert list(group.permissions.values_list("codename", flat=True)) == ["change_user"]

    def test_every_role_group_is_renamed_to_its_key(self):
        self._migrate(KEYS)

        assert {"consultant", "bdm", "office_assistant", "assignment_admin"} <= self._names(KEYS)
        assert not {"Consultant", "Business Development Manager", "Gebruikersbeheer", "Opdrachtbeheer"} & self._names(
            KEYS
        )

    def test_members_and_permissions_survive_the_rename(self):
        self._migrate(KEYS)

        self._assert_carries_members_and_permissions(self._group(KEYS, "office_assistant"))

    def test_existing_key_group_is_merged(self):
        """``setup_roles()`` creates the groups by key on every start, so the key
        may already be there when the migration runs."""
        self.group_model.objects.create(name="office_assistant")

        self._migrate(KEYS)

        assert self._group(KEYS, "Gebruikersbeheer") is None
        self._assert_carries_members_and_permissions(self._group(KEYS, "office_assistant"))

    def test_the_rename_is_reversible(self):
        self._migrate(KEYS)
        self._migrate(RENAME)

        assert self._group(RENAME, "office_assistant") is None
        self._assert_carries_members_and_permissions(self._group(RENAME, "Gebruikersbeheer"))
