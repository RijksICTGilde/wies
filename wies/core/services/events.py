from django.utils import timezone

from wies.core.models import Event, EventAction, EventSource

SUPPORTED_OBJECT_TYPES = {
    "User",
    "OrganizationUnit",
    "Assignment",
}


def create_event(*, object_type, action, source, object_id=None, user=None, context=None):
    """
    Create an audit event.
    Pass `user` for user-initiated actions (email auto-derived).
    Omit for system events (OrgSync, CSV import).
    """
    if object_type not in SUPPORTED_OBJECT_TYPES:
        msg = f"Unsupported event object_type: {object_type}"
        raise ValueError(msg)
    if action not in EventAction.values:
        msg = f"Unsupported event action: {action}"
        raise ValueError(msg)
    if source not in EventSource.values:
        msg = f"Unsupported event source: {source}"
        raise ValueError(msg)

    if not context:
        context = {}
    user_email = user.email if user else ""
    Event.objects.create(
        timestamp=timezone.now(),
        user=user,
        user_email=user_email,
        object_type=object_type,
        action=action,
        source=source,
        object_id=object_id,
        context=context,
    )
