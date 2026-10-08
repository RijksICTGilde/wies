"""Tests for the copy in the 0017 migration that seeds Service.request_description.

An open role (no placement) gets its role text as a starting vacancy text; a
filled role keeps an empty one, and the role text itself is left alone.
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TransactionTestCase

APP = "core"
MIGRATE_FROM = "0016_service_description_optional"
MIGRATE_TO = "0017_service_request_fields"


class RequestDescriptionMigrationTest(TransactionTestCase):
    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([(APP, target)])
        executor.loader.build_graph()

    def _apps_at(self, target):
        return MigrationExecutor(connection).loader.project_state((APP, target)).apps

    def setUp(self):
        self._migrate(MIGRATE_FROM)
        old_apps = self._apps_at(MIGRATE_FROM)
        Assignment = old_apps.get_model(APP, "Assignment")
        Service = old_apps.get_model(APP, "Service")
        Colleague = old_apps.get_model(APP, "Colleague")
        Placement = old_apps.get_model(APP, "Placement")
        assignment = Assignment.objects.create(name="Zaaksysteem", source="wies")
        self.open = Service.objects.create(assignment=assignment, description="Bouwt de koppeling.", source="wies")
        self.empty = Service.objects.create(assignment=assignment, description="", source="wies")
        self.filled = Service.objects.create(assignment=assignment, description="Taken van Anke.", source="wies")
        anke = Colleague.objects.create(name="Anke", email="anke@rijksoverheid.nl", source="wies")
        Placement.objects.create(colleague=anke, service=self.filled, source="wies")

    def tearDown(self):
        # Resolved from the graph, never hardcoded: migrating to an applied target
        # runs backwards and would leave the suite on an outdated schema.
        self._migrate(MigrationLoader(connection).graph.leaf_nodes(APP)[0][1])

    def _migrated(self, service):
        self._migrate(MIGRATE_TO)
        return self._apps_at(MIGRATE_TO).get_model(APP, "Service").objects.get(pk=service.pk)

    def test_an_open_role_gets_its_role_text_as_vacancy_text(self):
        migrated = self._migrated(self.open)

        assert migrated.request_description == "Bouwt de koppeling."
        assert migrated.description == "Bouwt de koppeling."

    def test_a_filled_role_gets_no_vacancy_text(self):
        assert self._migrated(self.filled).request_description == ""

    def test_an_open_role_without_text_stays_empty(self):
        assert self._migrated(self.empty).request_description == ""
