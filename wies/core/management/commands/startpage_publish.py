"""Publish the latest built ODI start page site from GitHub to MinIO.

Runs on the db_worker as a background Task (enqueued by the staff-gated button on
the Database admin page). Lives under wies.core because the worker resolves task
commands against the ``wies.core`` app label (see wies/core/management/commands/db_worker.py).
The actual work lives in wies.startpage.publish; this is just the TaskCommand shell.
"""

from dataclasses import asdict

from wies.core.management.task import TaskCommand
from wies.startpage.publish import publish_latest


class Command(TaskCommand):
    help = "Download the latest start page release artifact and publish it to MinIO"
    task_label = "ODI startpagina publiceren"

    def run_task(self, *args, **options):
        # Error handling (logging + failure result) is centralised in TaskCommand.
        return asdict(publish_latest())

    def summarize_result(self, result: dict) -> str:
        published = f"{result.get('objects', 0)} bestanden gepubliceerd"
        # The release tag is the only part that can be absent (a publish of an
        # untagged artifact), and "Release" without one reads as truncated.
        release = result.get("release")
        return f"Release {release}, {published}" if release else published
