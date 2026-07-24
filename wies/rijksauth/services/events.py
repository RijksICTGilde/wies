from wies.core.request_meta import get_client_ip, get_user_agent
from wies.rijksauth.models import AuthEvent

SUPPORTED_AUTH_EVENTS = {"Login.success", "Login.fail"}


def create_auth_event(user_email, name, context=None, request=None):
    """Record a login event. Pass `request` (when available) to log the client
    IP + User-Agent for BIO device logging; extraction is best-effort."""
    if name not in SUPPORTED_AUTH_EVENTS:
        msg = f"Unsupported auth event: {name}"
        raise ValueError(msg)
    ip = (get_client_ip(request) or None) if request is not None else None
    user_agent = get_user_agent(request) if request is not None else ""
    AuthEvent.objects.create(
        user_email=user_email,
        name=name,
        ip=ip,
        user_agent=user_agent,
        context=context or {},
    )
