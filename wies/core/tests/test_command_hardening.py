"""Defense in depth around management commands (pentest prep item 5).

- the db_worker runs only allowlisted task commands, whatever a Task row says;
- the destructive commands re-check ENABLE_DESTRUCTIVE_STAFF_ACTIONS themselves;
- the organization sync only fetches from organisaties.overheid.nl.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from wies.core.management.commands.db_worker import Command as WorkerCommand
from wies.core.models import Colleague, Task
from wies.core.services.organizations import sync_organizations, validate_sync_url
from wies.core.services.tasks import create_task

User = get_user_model()


class TaskCommandAllowlistTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="staff@rijksoverheid.nl")

    def test_create_task_rejects_unlisted_command(self):
        with pytest.raises(ValueError, match="Not an allowed task command"):
            create_task(command="dropdb", created_by=self.user, timeout_minutes=5)
        assert not Task.objects.exists()

    def test_create_task_accepts_listed_command(self):
        task = create_task(command="sync_organizations", created_by=self.user, timeout_minutes=5)
        assert task.status == "pending"

    def test_worker_refuses_unlisted_command(self):
        # A row written past create_task (e.g. by a DB-write bug elsewhere).
        task = Task.objects.create(command="dropdb", status="running", timeout_minutes=5)
        with patch("django.core.management.load_command_class") as mock_load:
            WorkerCommand().run_task(task)

        mock_load.assert_not_called()
        task.refresh_from_db()
        assert task.status == "failed"
        assert task.error_message == "Command is not an allowed task command"
        assert User.objects.filter(pk=self.user.pk).exists()


@override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=False)
class DestructiveCommandGuardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="keep@rijksoverheid.nl")

    def test_dropdb_refuses_when_disabled(self):
        with pytest.raises(CommandError):
            call_command("dropdb", "--noinput", verbosity=0)
        assert User.objects.filter(pk=self.user.pk).exists()

    def test_load_dummy_data_refuses_when_disabled(self):
        with pytest.raises(CommandError):
            call_command("load_dummy_data", "--profile", "base", verbosity=0)
        assert not Colleague.objects.exists()

    def test_load_full_data_refuses_when_disabled(self):
        with (
            patch("wies.core.management.commands.load_full_data.generate") as mock_generate,
            pytest.raises(CommandError),
        ):
            call_command("load_full_data", verbosity=0)
        mock_generate.assert_not_called()

    @override_settings(ENABLE_DESTRUCTIVE_STAFF_ACTIONS=True)
    def test_load_dummy_data_runs_when_enabled(self):
        call_command("load_dummy_data", "--profile", "base", verbosity=0)
        assert Colleague.objects.exists()


class SyncUrlPinningTest(TestCase):
    def test_accepts_organisaties_overheid_urls(self):
        validate_sync_url("https://organisaties.overheid.nl/archive/exportOO.xml")
        validate_sync_url("https://organisaties.overheid.nl/archive/exportOO_2026-01-01.xml")

    def test_rejects_other_urls(self):
        for url in [
            "http://organisaties.overheid.nl/archive/exportOO.xml",  # not https
            "https://example.com/exportOO.xml",
            "https://organisaties.overheid.nl.evil.com/exportOO.xml",
            "https://evil.com@organisaties.overheid.nl.evil.com/x.xml",
            "https://organisaties.overheid.nl:8443/exportOO.xml",
            "https://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
        ]:
            with self.subTest(url=url), pytest.raises(ValueError, match="Sync URL must be"):
                validate_sync_url(url)

    def test_sync_does_not_fetch_disallowed_url(self):
        with (
            patch("wies.core.services.organizations.requests.get") as mock_get,
            pytest.raises(ValueError, match="Sync URL must be"),
        ):
            sync_organizations(url="http://internal-service/")
        mock_get.assert_not_called()
