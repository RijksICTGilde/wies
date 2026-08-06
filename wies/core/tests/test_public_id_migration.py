"""Tests for the 0012 migration that adds public_id to the URL-exposed models.

Every existing row must come out with its own value: a single AddField with a
callable default would hand them all the same one, and the unique constraint
would then reject the column.
"""

import uuid

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TransactionTestCase

APP = "core"
MIGRATE_FROM = "0011_suborganization_colleague_suborganization"
MIGRATE_TO = "0012_public_ids"


class PublicIdBackfillMigrationTest(TransactionTestCase):
    """Drive the backfill through the real migration executor."""

    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([(APP, target)])
        executor.loader.build_graph()  # reload state after applying

    def _apps_at(self, target):
        return MigrationExecutor(connection).loader.project_state((APP, target)).apps

    def _migrate_to_latest(self):
        # Resolved from the graph, never hardcoded: migrating to a named target
        # that is already applied puts the executor in backwards mode, so a fixed
        # name would silently roll back every migration added after it and leave
        # the rest of the suite on an outdated schema.
        self._migrate(MigrationLoader(connection).graph.leaf_nodes(APP)[0][1])

    def setUp(self):
        # Roll back to the state just before the column exists, and fill it with
        # rows that the migration has to backfill.
        self._migrate(MIGRATE_FROM)
        assignment_model = self._apps_at(MIGRATE_FROM).get_model(APP, "Assignment")
        self.assignment_ids = [
            assignment_model.objects.create(name=f"Opdracht {i}", source="wies").pk for i in range(3)
        ]

    def tearDown(self):
        # Leave the DB at the latest migration for the rest of the suite.
        self._migrate_to_latest()

    def test_every_existing_row_gets_its_own_public_id(self):
        self._migrate(MIGRATE_TO)

        assignment_model = self._apps_at(MIGRATE_TO).get_model(APP, "Assignment")
        public_ids = [a.public_id for a in assignment_model.objects.filter(pk__in=self.assignment_ids)]

        assert len(public_ids) == len(self.assignment_ids)
        assert all(isinstance(public_id, uuid.UUID) for public_id in public_ids)
        assert len(set(public_ids)) == len(public_ids)
