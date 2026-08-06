"""Tests for the 0010 data migration that backfills Colleague.suborganization
from the legacy 'Merk' label category.

Backfill rules (see migrations/0010_suborganization_colleague_suborganization.py):
- exactly one merk label  -> set suborganization to a Suborganization with that name
- zero merk labels         -> leave suborganization null
- two or more merk labels  -> leave suborganization null (logged for an admin)
- fresh install (no 'Merk' category) -> no-op
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TransactionTestCase

APP = "core"
MIGRATE_FROM = "0010_event_ip_event_user_agent"
MIGRATE_TO = "0011_suborganization_colleague_suborganization"


class SuborganizationBackfillMigrationTest(TransactionTestCase):
    """Drive the 0011 backfill through the real migration executor."""

    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([(APP, target)])
        executor.loader.build_graph()  # reload state after applying
        return executor

    def _apps_at(self, target):
        return MigrationExecutor(connection).loader.project_state((APP, target)).apps

    def _migrate_to_latest(self):
        # Resolved from the graph, never hardcoded: migrating to a named target
        # that is already applied puts the executor in backwards mode, so a fixed
        # name would silently roll back every migration added after it and leave
        # the rest of the suite on an outdated schema.
        self._migrate(MigrationLoader(connection).graph.leaf_nodes(APP)[0][1])

    def setUp(self):
        # Roll back to the state just before the backfill migration.
        self._migrate(MIGRATE_FROM)
        old_apps = self._apps_at(MIGRATE_FROM)

        self.LabelCategory = old_apps.get_model(APP, "LabelCategory")
        self.Label = old_apps.get_model(APP, "Label")
        self.Colleague = old_apps.get_model(APP, "Colleague")

    def tearDown(self):
        # Leave the DB at the latest migration for the rest of the suite.
        self._migrate_to_latest()

    def _make_colleague(self, name, email):
        return self.Colleague.objects.create(name=name, email=email, source="wies")

    def test_backfill_single_label_sets_suborganization(self):
        category = self.LabelCategory.objects.create(name="Merk", color="#DCE3EA")
        rig = self.Label.objects.create(name="Rijks ICT Gilde", category=category)
        colleague = self._make_colleague("Solo", "solo@rijksoverheid.nl")
        colleague.labels.add(rig)

        self._migrate(MIGRATE_TO)

        new_apps = self._apps_at(MIGRATE_TO)
        Colleague = new_apps.get_model(APP, "Colleague")
        Suborganization = new_apps.get_model(APP, "Suborganization")

        migrated = Colleague.objects.get(pk=colleague.pk)
        assert migrated.suborganization is not None
        assert migrated.suborganization.name == "Rijks ICT Gilde"
        assert Suborganization.objects.filter(name="Rijks ICT Gilde").count() == 1

    def test_backfill_creates_suborganization_for_unused_merk_label(self):
        # A Merk label that no colleague carries must still become a Suborganization.
        category = self.LabelCategory.objects.create(name="Merk", color="#DCE3EA")
        rig = self.Label.objects.create(name="Rijks ICT Gilde", category=category)  # used below
        self.Label.objects.create(name="Ongebruikt Merk", category=category)  # zero colleagues
        used = self._make_colleague("User", "user@rijksoverheid.nl")
        used.labels.add(rig)

        self._migrate(MIGRATE_TO)

        new_apps = self._apps_at(MIGRATE_TO)
        Suborganization = new_apps.get_model(APP, "Suborganization")
        # Every merk label -> a Suborganization row, even the unused one.
        assert Suborganization.objects.filter(name="Ongebruikt Merk").exists()
        assert Suborganization.objects.filter(name="Rijks ICT Gilde").exists()
        assert Suborganization.objects.count() == 2

    def test_backfill_zero_labels_leaves_null(self):
        # Category exists (so the migration runs), but this colleague has no merk label.
        self.LabelCategory.objects.create(name="Merk", color="#DCE3EA")
        colleague = self._make_colleague("Empty", "empty@rijksoverheid.nl")

        self._migrate(MIGRATE_TO)

        new_apps = self._apps_at(MIGRATE_TO)
        Colleague = new_apps.get_model(APP, "Colleague")
        assert Colleague.objects.get(pk=colleague.pk).suborganization_id is None

    def test_backfill_multiple_labels_leaves_null(self):
        category = self.LabelCategory.objects.create(name="Merk", color="#DCE3EA")
        rig = self.Label.objects.create(name="Rijks ICT Gilde", category=category)
        rc = self.Label.objects.create(name="Rijksconsultants", category=category)
        colleague = self._make_colleague("Ambiguous", "ambiguous@rijksoverheid.nl")
        colleague.labels.add(rig, rc)

        self._migrate(MIGRATE_TO)

        new_apps = self._apps_at(MIGRATE_TO)
        Colleague = new_apps.get_model(APP, "Colleague")
        Suborganization = new_apps.get_model(APP, "Suborganization")

        migrated = Colleague.objects.get(pk=colleague.pk)
        # The ambiguous colleague itself is left unassigned...
        assert migrated.suborganization_id is None
        # ...but every merk label still becomes a Suborganization (all merken are migrated).
        assert Suborganization.objects.filter(name="Rijks ICT Gilde").exists()
        assert Suborganization.objects.filter(name="Rijksconsultants").exists()

    def test_backfill_dedupes_suborganization_across_colleagues(self):
        category = self.LabelCategory.objects.create(name="Merk", color="#DCE3EA")
        rig = self.Label.objects.create(name="Rijks ICT Gilde", category=category)
        c1 = self._make_colleague("One", "one@rijksoverheid.nl")
        c2 = self._make_colleague("Two", "two@rijksoverheid.nl")
        c1.labels.add(rig)
        c2.labels.add(rig)

        self._migrate(MIGRATE_TO)

        new_apps = self._apps_at(MIGRATE_TO)
        Colleague = new_apps.get_model(APP, "Colleague")
        Suborganization = new_apps.get_model(APP, "Suborganization")

        # Both colleagues point at the same single Suborganization row.
        assert Suborganization.objects.filter(name="Rijks ICT Gilde").count() == 1
        suborg = Suborganization.objects.get(name="Rijks ICT Gilde")
        assert Colleague.objects.get(pk=c1.pk).suborganization_id == suborg.pk
        assert Colleague.objects.get(pk=c2.pk).suborganization_id == suborg.pk

    def test_backfill_ignores_labels_from_other_categories(self):
        # Only 'Merk' labels should be considered. A label in another category
        # must not become a suborganization.
        merk = self.LabelCategory.objects.create(name="Merk", color="#DCE3EA")
        expertise = self.LabelCategory.objects.create(name="Expertise", color="#B3D7EE")
        rig = self.Label.objects.create(name="Rijks ICT Gilde", category=merk)
        ai = self.Label.objects.create(name="AI", category=expertise)
        colleague = self._make_colleague("Mixed", "mixed@rijksoverheid.nl")
        colleague.labels.add(rig, ai)

        self._migrate(MIGRATE_TO)

        new_apps = self._apps_at(MIGRATE_TO)
        Colleague = new_apps.get_model(APP, "Colleague")
        Suborganization = new_apps.get_model(APP, "Suborganization")

        migrated = Colleague.objects.get(pk=colleague.pk)
        # Exactly one *merk* label -> set from that one; the Expertise label is ignored.
        assert migrated.suborganization is not None
        assert migrated.suborganization.name == "Rijks ICT Gilde"
        assert not Suborganization.objects.filter(name="AI").exists()

    def test_backfill_noop_on_fresh_install(self):
        # No 'Merk' category at all: migration returns early, nothing created.
        colleague = self._make_colleague("Fresh", "fresh@rijksoverheid.nl")

        self._migrate(MIGRATE_TO)

        new_apps = self._apps_at(MIGRATE_TO)
        Colleague = new_apps.get_model(APP, "Colleague")
        Suborganization = new_apps.get_model(APP, "Suborganization")

        assert Colleague.objects.get(pk=colleague.pk).suborganization_id is None
        assert Suborganization.objects.count() == 0
