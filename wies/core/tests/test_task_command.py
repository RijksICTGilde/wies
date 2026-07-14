"""Tests for the TaskCommand base class and the sync_organizations task."""

from unittest.mock import patch

from django.test import TestCase

from wies.core.management.commands.sync_organizations import Command as SyncCommand
from wies.core.management.task import TaskCommand


class OkTask(TaskCommand):
    def run_task(self, *args, **options):
        return {"count": 3}


class FailingTask(TaskCommand):
    def run_task(self, *args, **options):
        msg = "boom"
        raise ValueError(msg)


class TaskCommandTest(TestCase):
    def test_success_sets_result(self):
        command = OkTask()
        command.handle()

        assert command.result == {"success": True, "result": {"count": 3}}

    def test_failure_is_captured_not_raised(self):
        command = FailingTask()
        command.handle()  # must not raise

        assert command.result == {"success": False, "error": "boom"}

    def test_result_is_initialised(self):
        # getattr(command, "result", None) in db_worker must be well-defined.
        assert OkTask().result is None


class SyncOrganizationsTaskTest(TestCase):
    def test_is_task_command(self):
        assert issubclass(SyncCommand, TaskCommand)

    @patch(
        "wies.core.management.commands.sync_organizations.sync_organizations",
        side_effect=RuntimeError("network down"),
    )
    def test_service_error_becomes_failed_result(self, mock_sync):
        command = SyncCommand()
        command.handle(url=None)

        assert command.result == {"success": False, "error": "network down"}
        mock_sync.assert_called_once()

    @patch(
        "wies.core.management.commands.sync_organizations.sync_organizations",
        side_effect=RuntimeError("network down"),
    )
    def test_failure_logs_against_concrete_command(self, mock_sync):
        # The error location must be the actual task, not the base module — so the
        # log record fires on the command's own module logger.
        command_module = "wies.core.management.commands.sync_organizations"
        with self.assertLogs(command_module, level="ERROR") as captured:
            SyncCommand().handle(url=None)

        mock_sync.assert_called_once()
        assert any(r.name == command_module and r.exc_info for r in captured.records)

    @patch("wies.core.management.commands.sync_organizations.sync_organizations")
    def test_success_result_wraps_service_payload(self, mock_sync):
        # asdict() needs a dataclass; a simple stand-in with __dataclass_fields__.
        from dataclasses import dataclass  # noqa: PLC0415 - local to this test

        @dataclass
        class Report:
            created: int = 2

        mock_sync.return_value = Report()
        command = SyncCommand()
        command.handle(url=None)

        assert command.result == {"success": True, "result": {"created": 2}}
