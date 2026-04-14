from wies.rijksauth.models import AuthEvent

SUPPORTED_AUTH_EVENTS = {"Login.success", "Login.fail"}


def create_auth_event(user_email, name, context=None):
    if name not in SUPPORTED_AUTH_EVENTS:
        msg = f"Unsupported auth event: {name}"
        raise ValueError(msg)
    AuthEvent.objects.create(user_email=user_email, name=name, context=context or {})
