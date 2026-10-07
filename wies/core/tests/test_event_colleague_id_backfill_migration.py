"""Tests for the 0017 migration that backfills colleague_id on team audit rows.

Backfill rules (see migrations/0017_backfill_event_colleague_id.py):
- name of exactly one colleague -> that colleague's id
- name shared by colleagues     -> no id
- name nobody carries           -> no id
- carrier joined after event    -> no id
- vacancy row                   -> untouched
- entry that is not a dict      -> untouched
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TransactionTestCase
from django.utils import timezone

APP = "core"
MIGRATE_FROM = "0016_service_description_optional"
MIGRATE_TO = "0017_backfill_event_colleague_id"


class EventColleagueIdBackfillMigrationTest(TransactionTestCase):
    """Drive the 0017 backfill through the real migration executor."""

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
        self.Colleague = old_apps.get_model(APP, "Colleague")
        self.Event = old_apps.get_model(APP, "Event")

    def tearDown(self):
        self._migrate_to_latest()

    def _colleague(self, name, email, joined=None):
        """``joined`` gives the colleague an account that dates from that moment."""
        # The real user model: only core is migrated back, so the user table is
        # at its latest schema and the historical user model no longer fits it.
        user = get_user_model().objects.create_user(email=email, date_joined=joined) if joined else None
        return self.Colleague.objects.create(name=name, email=email, source="wies", user_id=user.pk if user else None)

    def _event(self, changes, **overrides):
        fields = {
            "object_type": "Assignment",
            "action": "update",
            "source": "user",
            "object_id": 1,
            "context": {"field_name": "services", "field_label": "Team", "changes": changes},
        }
        return self.Event.objects.create(**{**fields, **overrides})

    def _changes_after_migration(self, event):
        self._migrate(MIGRATE_TO)
        migrated_event_model = self._apps_at(MIGRATE_TO).get_model(APP, "Event")
        return migrated_event_model.objects.get(pk=event.pk).context["changes"]

    def test_unique_name_gets_the_colleague_id_on_both_sides(self):
        jan = self._colleague("Jan Jansen", "jan@rijksoverheid.nl")
        piet = self._colleague("Piet Pietersen", "piet@rijksoverheid.nl")
        event = self._event(
            [{"old": {"id": 1, "colleague_name": "Jan Jansen"}, "new": {"id": 1, "colleague_name": "Piet Pietersen"}}]
        )

        changes = self._changes_after_migration(event)

        assert changes[0]["old"]["colleague_id"] == jan.pk
        assert changes[0]["new"]["colleague_id"] == piet.pk

    def test_shared_name_gets_no_id(self):
        self._colleague("Jan Jansen", "jan1@rijksoverheid.nl")
        self._colleague("Jan Jansen", "jan2@rijksoverheid.nl")
        event = self._event([{"old": None, "new": {"id": 1, "colleague_name": "Jan Jansen"}}])

        changes = self._changes_after_migration(event)

        assert "colleague_id" not in changes[0]["new"]

    def test_unknown_name_gets_no_id(self):
        # The colleague has been renamed since, so the frozen name matches nobody.
        self._colleague("Jan de Vries", "jan@rijksoverheid.nl")
        event = self._event([{"old": {"id": 1, "colleague_name": "Jan Jansen"}, "new": None}])

        changes = self._changes_after_migration(event)

        assert "colleague_id" not in changes[0]["old"]

    def test_carrier_who_joined_after_the_event_gets_no_id(self):
        # Whoever carries the name now got their account after the event, so the
        # row names a predecessor: someone renamed or removed since.
        event_time = timezone.now() - timedelta(days=30)
        self._colleague("Jan Jansen", "jan@rijksoverheid.nl", joined=event_time + timedelta(days=1))
        event = self._event([{"old": None, "new": {"id": 1, "colleague_name": "Jan Jansen"}}], timestamp=event_time)

        changes = self._changes_after_migration(event)

        assert "colleague_id" not in changes[0]["new"]

    def test_carrier_who_joined_before_the_event_gets_the_id(self):
        event_time = timezone.now() - timedelta(days=30)
        jan = self._colleague("Jan Jansen", "jan@rijksoverheid.nl", joined=event_time - timedelta(days=1))
        event = self._event([{"old": None, "new": {"id": 1, "colleague_name": "Jan Jansen"}}], timestamp=event_time)

        changes = self._changes_after_migration(event)

        assert changes[0]["new"]["colleague_id"] == jan.pk

    def test_entry_that_is_not_a_dict_is_skipped(self):
        jan = self._colleague("Jan Jansen", "jan@rijksoverheid.nl")
        event = self._event(["kapot", {"old": None, "new": {"id": 1, "colleague_name": "Jan Jansen"}}])

        changes = self._changes_after_migration(event)

        assert changes[0] == "kapot"
        assert changes[1]["new"]["colleague_id"] == jan.pk

    def test_vacancy_row_is_left_alone(self):
        event = self._event([{"old": None, "new": {"id": 1, "colleague_name": None}}])

        changes = self._changes_after_migration(event)

        assert changes[0]["new"] == {"id": 1, "colleague_name": None}

    def test_existing_colleague_id_is_kept(self):
        jan = self._colleague("Jan Jansen", "jan@rijksoverheid.nl")
        other = self._colleague("Iemand Anders", "anders@rijksoverheid.nl")
        event = self._event([{"old": None, "new": {"id": 1, "colleague_name": "Jan Jansen", "colleague_id": other.pk}}])

        changes = self._changes_after_migration(event)

        assert changes[0]["new"]["colleague_id"] == other.pk
        assert changes[0]["new"]["colleague_id"] != jan.pk

    def test_other_events_are_left_alone(self):
        self._colleague("Jan Jansen", "jan@rijksoverheid.nl")
        rows = [{"old": None, "new": {"id": 1, "colleague_name": "Jan Jansen"}}]
        event = self._event(rows, object_type="Colleague")

        changes = self._changes_after_migration(event)

        assert "colleague_id" not in changes[0]["new"]
