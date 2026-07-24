from django.utils import timezone

from wies.core.models import Event, EventAction, EventSource
from wies.core.request_meta import get_client_ip, get_user_agent

SUPPORTED_OBJECT_TYPES = {
    "User",
    "OrganizationUnit",
    "Assignment",
}


def create_event(*, object_type, action, source, object_id=None, user=None, context=None, request=None):
    """
    Create an audit event.
    Pass `user` for user-initiated actions (email auto-derived).
    Omit for system events (OrgSync, CSV import).
    Pass `request` (when available) to record the client IP and User-Agent
    for BIO device logging; extraction is best-effort and never fails the event.
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
    ip = (get_client_ip(request) or None) if request is not None else None
    user_agent = get_user_agent(request) if request is not None else ""
    Event.objects.create(
        timestamp=timezone.now(),
        user=user,
        user_email=user_email,
        object_type=object_type,
        action=action,
        source=source,
        object_id=object_id,
        ip=ip,
        user_agent=user_agent,
        context=context,
    )
