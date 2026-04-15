from wies.core.models import Event

SUPPORTED_EVENT_NAMES = {
    "User.create",
    "User.update",
    "User.delete",
    "OrgSync.create",
    "OrgSync.update",
    "OrgSync.deactivate",
    "OrgSync.delete",
    "Assignment.create",
    "Assignment.update",
}


def create_event(name, *, user=None, context=None, resource_id=None):
    """
    Create an audit event.
    Pass `user` for user-initiated actions (email auto-derived).
    Omit for system events (OrgSync, CSV import).
    """
    if name not in SUPPORTED_EVENT_NAMES:
        msg = f"Unsupported event name: {name}"
        raise ValueError(msg)

    if not context:
        context = {}
    user_email = user.email if user else ""
    Event.objects.create(
        user=user,
        user_email=user_email,
        name=name,
        context=context,
        resource_id=resource_id,
    )
