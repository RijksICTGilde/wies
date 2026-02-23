"""Service functions for managing background tasks."""

from django.db.models import QuerySet
from django.utils import timezone

from wies.core.models import Task, User


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
        created_by=created_by,
        timeout_minutes=timeout_minutes,
        parameters=parameters,
        status="pending",
    )


def get_latest_tasks(limit: int = 3) -> QuerySet[Task]:
    """
    Fetch the most recent tasks.

    Args:
        limit: Maximum number of tasks to return

    Returns:
        QuerySet of Task objects ordered by creation date (newest first)
    """
    return Task.objects.select_related("created_by").order_by("-created_at")[:limit]


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
