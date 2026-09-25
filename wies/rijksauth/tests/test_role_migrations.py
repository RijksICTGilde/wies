"""Tests for the role data migrations: the Opdrachtbeheer backfill (0009), the
Beheerder -> Gebruikersbeheer rename (0010), the move to role keys (0011) and
dropping Opdrachtbeheer for the roles that replace it (0012)."""

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
DROP = "0012_drop_assignment_admin_group"


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
        # Spelled out: 0009's Opdrachtbeheer row is gone once an earlier
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

        assert {"consultant", "bdm", "office_assistant"} <= self._names(KEYS)
        assert not {"Consultant", "Business Development Manager", "Gebruikersbeheer"} & self._names(KEYS)

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


class DropAssignmentAdminMigrationTest(_MigrationTestCase):
    """0012 removes Opdrachtbeheer and hands its addresses the roles that replace it."""

    STAFF = "applicatiebeheer@rijksoverheid.nl"

    def setUp(self):
        self._migrate(KEYS)
        apps = self._apps_at(KEYS)
        self.group_model = apps.get_model("auth", "Group")
        user_model = apps.get_model(APP, "User")
        self.staff_id = user_model.objects.create(email=self.STAFF).pk
        self.other_id = user_model.objects.create(email="ander@rijksoverheid.nl").pk
        self.group_model.objects.get_or_create(name="assignment_admin")

    def _names(self, target, user_id):
        apps = self._apps_at(target)
        user = apps.get_model(APP, "User").objects.get(pk=user_id)
        return set(user.groups.values_list("name", flat=True))

    def _migrate_with_staff(self):
        with patch.dict(os.environ, {"STAFF_EMAILS": self.STAFF}):
            self._migrate(DROP)

    def test_the_group_is_gone(self):
        self._migrate_with_staff()

        groups = self._apps_at(DROP).get_model("auth", "Group").objects
        assert not groups.filter(name__in=("assignment_admin", "Opdrachtbeheer")).exists()

    def test_staff_emails_receive_the_replacing_roles(self):
        self._migrate_with_staff()

        assert self._names(DROP, self.staff_id) == {"bdm", "office_assistant"}

    def test_an_address_outside_the_list_is_left_alone(self):
        self._migrate_with_staff()

        assert self._names(DROP, self.other_id) == set()

    def test_without_configured_addresses_nobody_is_granted_anything(self):
        with patch.dict(os.environ, {"STAFF_EMAILS": ""}):
            self._migrate(DROP)

        assert self._names(DROP, self.staff_id) == set()


class DropAssignmentAdminMembersTest(_MigrationTestCase):
    """The members of the group that goes, as opposed to the address list.

    0009 is not the only way into Opdrachtbeheer: the roles screen hands it out
    too, so an environment that ran the earlier chain can have members no address
    list names. Deleting the group takes their rights with it, which is a silent
    loss and the reason 0012 reads the group and not only ``STAFF_EMAILS``.
    """

    def setUp(self):
        self._migrate(KEYS)
        apps = self._apps_at(KEYS)
        self.group_model = apps.get_model("auth", "Group")
        user_model = apps.get_model(APP, "User")
        self.member_id = user_model.objects.create(email="opdrachtbeheer@rijksoverheid.nl").pk
        group, _ = self.group_model.objects.get_or_create(name="Opdrachtbeheer")
        group.user_set.add(self.member_id)

    def _names(self, user_id):
        user = self._apps_at(DROP).get_model(APP, "User").objects.get(pk=user_id)
        return set(user.groups.values_list("name", flat=True))

    def test_a_member_outside_the_address_list_keeps_the_opdracht_rights_as_bdm(self):
        with patch.dict(os.environ, {"STAFF_EMAILS": ""}):
            self._migrate(DROP)

        assert self._names(self.member_id) == {"bdm"}

    def test_a_member_gains_no_user_administration(self):
        """BDM and nothing else: user administration is what Opdrachtbeheer never
        carried, so inheriting it would widen the rights of whoever held it."""
        with patch.dict(os.environ, {"STAFF_EMAILS": ""}):
            self._migrate(DROP)

        assert "office_assistant" not in self._names(self.member_id)


class RoleMigrationChainTest(_MigrationTestCase):
    """The chain as a deploy runs it, and as a rollback runs it.

    The three starting points that exist: a fresh database (0008 up), one that
    already has the earlier chain (0011 up, covered by the tests above), and
    backwards to where the chain began.
    """

    STAFF = "applicatiebeheer@rijksoverheid.nl"

    def setUp(self):
        self._migrate(BEFORE_BACKFILL)
        user_model = self._apps_at(BEFORE_BACKFILL).get_model(APP, "User")
        self.staff_id = user_model.objects.create(email=self.STAFF).pk

    def _names(self, target, user_id):
        user = self._apps_at(target).get_model(APP, "User").objects.get(pk=user_id)
        return set(user.groups.values_list("name", flat=True))

    def _group_names(self, target):
        return set(self._apps_at(target).get_model("auth", "Group").objects.values_list("name", flat=True))

    def test_a_fresh_database_ends_on_the_keys_and_no_gone_group(self):
        with patch.dict(os.environ, {"STAFF_EMAILS": self.STAFF}):
            self._migrate(DROP)

        assert self._names(DROP, self.staff_id) == {"bdm", "office_assistant"}
        assert not {"Opdrachtbeheer", "assignment_admin"} & self._group_names(DROP)

    def test_the_whole_chain_runs_backwards_and_forwards_again(self):
        """Backwards is where a hardcoded target bites: every step declares its own
        reverse, and the two renames put the labels back. The backfills are noop
        both ways, so what they granted stays granted."""
        with patch.dict(os.environ, {"STAFF_EMAILS": self.STAFF}):
            self._migrate(DROP)
            self._migrate(BEFORE_BACKFILL)

            assert not {"office_assistant", "bdm", "consultant"} & self._group_names(BEFORE_BACKFILL)

            self._migrate(DROP)

        assert self._names(DROP, self.staff_id) == {"bdm", "office_assistant"}
