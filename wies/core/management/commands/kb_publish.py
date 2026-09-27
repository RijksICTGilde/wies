"""Publish the latest built knowledge-base site from GitHub to MinIO.

Runs on the db_worker as a background Task (enqueued by the staff-gated button on
the KB portal). Lives under wies.core because the worker resolves task commands
against the ``wies.core`` app label (see wies/core/management/commands/db_worker.py).
The actual work lives in wies.kb.publish; this is just the TaskCommand shell.
"""

from dataclasses import asdict

from wies.core.management.task import TaskCommand
from wies.kb.publish import publish_latest


class Command(TaskCommand):
    help = "Download the latest KB release artifact and publish it to MinIO"
    task_label = "Kennisbank publiceren"

    def run_task(self, *args, **options):
        # Error handling (logging + failure result) is centralised in TaskCommand.
        return asdict(publish_latest())
