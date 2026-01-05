from wies.core.models import Event


SUPPORTED_EVENT_NAMES = {
    'User.create',
    'User.update',
    'User.delete',
    'Login.success'
}

def create_event(user_id, name, context: dict = None):

    if not name in SUPPORTED_EVENT_NAMES:
        raise ValueError(f"Unsupported event name: {name}")

    if not context:
        context = {}
    Event.objects.create(user_id=user_id, name=name, context=context)
