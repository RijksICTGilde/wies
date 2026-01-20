from wies.core.models import Event

SUPPORTED_EVENT_NAMES = {
    "User.create",
    "User.update",
    "User.delete",
    "Login.success",
    "Login.fail",
}


def create_event(user_email, name, context: dict | None = None):
    if name not in SUPPORTED_EVENT_NAMES:
        msg = f"Unsupported event name: {name}"
        raise ValueError(msg)

    if not context:
        context = {}
    Event.objects.create(user_email=user_email, name=name, context=context)
