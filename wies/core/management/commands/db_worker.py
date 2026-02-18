import logging
import signal
import time

from django.core import management
from django.core.management.base import BaseCommand
from django.utils import timezone

from wies.core.models import Task
from wies.core.services.tasks import mark_expired_tasks_as_failed

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Monitor task table and execute long running jobs"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shutdown = False

    def handle_sigterm(self, signum, frame):
        logger.info("Received shutdown signal, finishing current work...")
        self.shutdown = True

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_true",
            help="Do not prompt for confirmation",
        )

    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        signal.signal(signal.SIGINT, self.handle_sigterm)

        logger.info("DB worker started, monitoring for tasks...")

        while not self.shutdown:
            time.sleep(1)

            # Mark any expired running tasks as failed
            expired_count = mark_expired_tasks_as_failed()
            if expired_count > 0:
                logger.warning("Marked %s expired task(s) as failed", expired_count)

            # Fetch the oldest pending task
            task = Task.objects.filter(status="pending").order_by("created_at").first()

            if task:
                logger.info("Processing task %s: %s", task.id, task.command)

                # Mark task as running
                task.status = "running"
                task.started_at = timezone.now()
                task.save(update_fields=["status", "started_at"])

                # Instantiate and execute the management command for this task
                # wrapped in try, except for extra protection. worker should not stop
                try:
                    command = management.load_command_class("wies.core", task.command)
                    command.run_from_argv(["manage.py", task.command])
                except Exception:
                    # shouldnt happen, but worker should not crash
                    logger.exception("Unpected error running task")
                else:
                    # Get result from command instance
                    result = getattr(command, "result", None)

                    # Check if command succeeded or failed
                    if result and isinstance(result, dict) and result.get("success"):
                        # Command succeeded
                        task.status = "completed"
                        task.result = result.get("result", {})
                        task.completed_at = timezone.now()
                        task.save(update_fields=["status", "result", "completed_at"])
                        logger.info("Task %s completed successfully", task.id)
                    else:
                        # Command failed or returned unexpected result
                        task.status = "failed"
                        if result and isinstance(result, dict):
                            task.error_message = result.get("error", "Command returned failure")
                        else:
                            task.error_message = "Command returned unexpected result format"
                        task.completed_at = timezone.now()
                        task.save(update_fields=["status", "error_message", "completed_at"])
                        logger.error("Task %s failed: %s", task.id, task.error_message)

        logger.info("DB worker shut down gracefully.")
