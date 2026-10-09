"""Service functions for managing background tasks."""

from django.contrib.auth import get_user_model
from django.core import management
from django.utils import timezone

from wies.core.models import Task

User = get_user_model()


def create_task(command: str, created_by: User, timeout_minutes: int, parameters: dict | None = None) -> Task:
    """
    Create a new task for background processing.

    Args:
        command: Name of the management command to execute
        created_by: User who created the task
        timeout_minutes: Task timeout in minutes
        parameters: Optional parameters to pass to the command

    Returns:
        The created Task instance
    """
    if parameters is None:
        parameters = {}

    return Task.objects.create(
        command=command,
        label=get_task_label(command),
        created_by=created_by,
        timeout_minutes=timeout_minutes,
        parameters=parameters,
        status="pending",
    )


def get_latest_tasks(limit: int = 3) -> list[Task]:
    """
    Fetch the most recent tasks.

    Args:
        limit: Maximum number of tasks to return

    Returns:
        Task objects ordered by creation date (newest first), each carrying a
        ``result_text`` for the task list
    """
    tasks = list(Task.objects.select_related("created_by").order_by("-created_at")[:limit])
    for task in tasks:
        task.result_text = get_task_result_text(task)
    return tasks


def get_task_result_text(task: Task) -> str:
    """What a task has to show for itself in the task list; "-" when nothing yet.

    A failure shows its error message. A success is summarised by the command
    that produced the payload (``TaskCommand.summarize_result``), loaded the same
    way as in :func:`get_task_label`.
    """
    if task.status == "failed" and task.error_message:
        return task.error_message
    if task.status != "completed" or not task.result:
        return "-"
    try:
        cmd = management.load_command_class("wies.core", task.command)
        return cmd.summarize_result(task.result) or "-"
    except Exception:  # noqa: BLE001 (blind except) — a removed command or an outdated payload must not break the staff page
        return "-"


def get_task_label(command: str) -> str:
    """Human-readable label for a task command; falls back to the command name.

    Reads the ``task_label`` a TaskCommand declares for itself, loaded the same way
    the worker resolves the command (by ``wies.core`` app label).
    """
    try:
        cmd = management.load_command_class("wies.core", command)
    except Exception:  # noqa: BLE001 — an unknown/unloadable command still gets a usable label
        return command
    return getattr(cmd, "task_label", "") or command


def has_active_task(command: str) -> bool:
    """
    Check if there's an active (non-expired) task for the given command.

    Args:
        command: Management command name

    Returns:
        True if there's a pending or non-expired running task for this command
    """
    # Check for pending tasks
    pending_exists = Task.objects.filter(command=command, status="pending").exists()
    if pending_exists:
        return True

    # Check for running tasks that haven't expired
    running_tasks = Task.objects.filter(command=command, status="running")
    return any(not task.is_expired() for task in running_tasks)


def mark_expired_tasks_as_failed() -> int:
    """
    Mark all expired running tasks as failed.

    Returns:
        Number of tasks marked as failed
    """
    running_tasks = Task.objects.filter(status="running")
    count = 0

    for task in running_tasks:
        if task.is_expired():
            task.status = "failed"
            task.error_message = f"Task timed out after {task.timeout_minutes} minutes"
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "error_message", "completed_at"])
            count += 1

    return count
