from wies.rijksauth.models import AuthEvent
from wies.rijksauth.request_meta import get_request_metadata

SUPPORTED_AUTH_EVENTS = {"Login.success", "Login.fail", "Logout"}


def create_auth_event(user_email, name, context=None, request=None):
    """Record a login event. Pass `request` (when available) to log the client
    IP + User-Agent for BIO device logging; extraction is best-effort."""
    if name not in SUPPORTED_AUTH_EVENTS:
        msg = f"Unsupported auth event: {name}"
        raise ValueError(msg)
    meta = get_request_metadata(request)
    AuthEvent.objects.create(
        user_email=user_email,
        name=name,
        ip=meta["ip"],
        forwarded_for=meta["forwarded_for"],
        remote_addr=meta["remote_addr"],
        user_agent=meta["user_agent"],
        context=context or {},
    )
