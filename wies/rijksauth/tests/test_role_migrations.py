"""Tests for the role data migrations: the Opdrachtbeheer backfill (0009) and
the Beheerder -> Gebruikersbeheer rename (0010)."""

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

    def test_staff_members_receive_assignment_admin(self):
        with patch.dict(os.environ, {"STAFF_EMAILS": " staff@rijksoverheid.nl , nobody@rijksoverheid.nl"}):
            self._migrate(BACKFILL)

        assert self._groups_of(self.staff_id) == {"Opdrachtbeheer"}
        assert self._groups_of(self.other_id) == set()

    def test_group_is_created_without_staff_emails(self):
        with patch.dict(os.environ, {"STAFF_EMAILS": ""}):
            self._migrate(BACKFILL)

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
