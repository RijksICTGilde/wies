"""Tests for the backfill in the 0015 migration that backfills OrganizationUnit.main_type.

Backfill rules (see migrations/0015_organizationunit_main_type.py):
- one type          -> that type
- several types     -> the type with the lowest pk (what .first() returns)
- no types          -> stays null
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TransactionTestCase

APP = "core"
MIGRATE_FROM = "0014_contractperiod_service_hours"
MIGRATE_TO = "0015_organizationunit_main_type"


class MainTypeBackfillMigrationTest(TransactionTestCase):
    """Drive the 0015 backfill through the real migration executor."""

    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([(APP, target)])
        executor.loader.build_graph()  # reload state after applying
        return executor

    def _apps_at(self, target):
        return MigrationExecutor(connection).loader.project_state((APP, target)).apps

    def _migrate_to_latest(self):
        # Resolved from the graph, never hardcoded: migrating to an applied target
        # runs backwards and would leave the suite on an outdated schema.
        self._migrate(MigrationLoader(connection).graph.leaf_nodes(APP)[0][1])

    def setUp(self):
        self._migrate(MIGRATE_FROM)
        old_apps = self._apps_at(MIGRATE_FROM)
        self.OrganizationType = old_apps.get_model(APP, "OrganizationType")
        self.OrganizationUnit = old_apps.get_model(APP, "OrganizationUnit")
        self.inspectie = self.OrganizationType.objects.create(name="Inspectie", label="Inspectie")
        self.zbo = self.OrganizationType.objects.create(
            name="Zelfstandig bestuursorgaan", label="Zelfstandig bestuursorgaan"
        )

    def tearDown(self):
        self._migrate_to_latest()

    def _unit(self, name, *types):
        unit = self.OrganizationUnit.objects.create(name=name)
        unit.organization_types.set(types)
        return unit

    def _main_type_id_after_migration(self, unit):
        self._migrate(MIGRATE_TO)
        migrated_unit_model = self._apps_at(MIGRATE_TO).get_model(APP, "OrganizationUnit")
        return migrated_unit_model.objects.get(pk=unit.pk).main_type_id

    def test_single_type_becomes_main_type(self):
        unit = self._unit("ODI", self.zbo)
        assert self._main_type_id_after_migration(unit) == self.zbo.pk

    def test_multi_type_takes_lowest_pk(self):
        unit = self._unit("ANVS", self.zbo, self.inspectie)
        assert self._main_type_id_after_migration(unit) == self.inspectie.pk

    def test_untyped_unit_stays_null(self):
        unit = self._unit("Zonder type")
        assert self._main_type_id_after_migration(unit) is None
