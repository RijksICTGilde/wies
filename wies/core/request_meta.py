"""Best-effort request metadata extraction for audit/auth event logging.

IP and User-Agent together approximate "het gebruikte apparaat" (the device
used) required by BIO. A web app cannot identify a physical device, so this is
the realistic best effort. Extraction is best-effort: any failure returns an
empty string so it never breaks event creation.
"""

from django.conf import settings


def get_client_ip(request) -> str:
    """Return the client IP, trusting exactly ``settings.TRUSTED_PROXY_HOPS``
    proxy hops.

    Reads the ``X-Forwarded-For`` entry at position ``-TRUSTED_PROXY_HOPS``
    (rightmost-minus-(N-1)), i.e. the address the trusted proxy itself added,
    so a client-supplied leftmost value cannot spoof it. Falls back to
    ``REMOTE_ADDR`` when hops is 0 or the header is missing/too short. Returns
    ``""`` on any failure — callers must never break event creation.
    """
    try:
        hops = settings.TRUSTED_PROXY_HOPS
        if hops > 0:
            xff = request.headers.get("x-forwarded-for", "")
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if len(parts) >= hops:
                return parts[-hops]
        return request.META.get("REMOTE_ADDR", "") or ""
    except Exception:  # noqa: BLE001 (blind except) — best-effort, must never fail the event
        return ""


def get_user_agent(request) -> str:
    """Return the User-Agent header, truncated to 512 chars. ``""`` on failure."""
    try:
        return request.headers.get("user-agent", "")[:512]
    except Exception:  # noqa: BLE001 (blind except) — best-effort, must never fail the event
        return ""
