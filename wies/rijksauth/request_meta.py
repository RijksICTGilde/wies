"""Best-effort request metadata extraction for audit/auth event logging.

IP and User-Agent together approximate "het gebruikte apparaat" (the device
used) required by BIO. A web app cannot identify a physical device, so this is
the realistic best effort. Extraction is best-effort: any failure returns an
empty string so it never breaks event creation.
"""

import ipaddress

from django.conf import settings


def _valid_ip(value: str) -> str:
    """Return ``value`` normalised as a bare IP address suitable for a
    ``GenericIPAddressField`` (Postgres ``inet``), or ``""`` if it holds no
    valid IPv4/IPv6 address.

    A trailing port is stripped rather than rejected, so a load balancer that
    emits ``1.2.3.4:56789`` or ``[::1]:443`` still yields the useful address
    (``1.2.3.4`` / ``::1``) instead of dropping the evidence entirely.
    """
    value = value.strip()
    # Try the bare literal first: this is the common case and, crucially, keeps
    # un-bracketed IPv6 (``2001:db8::1``, which is full of colons) from being
    # mistaken for a host:port pair below.
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    # Bracketed IPv6 with optional port: [::1] or [::1]:443 -> ::1
    if value.startswith("["):
        value = value[1:].split("]", 1)[0]
    # Bare IPv4 with a port: 1.2.3.4:56789 -> 1.2.3.4. A single colon means a
    # v4:port pair; multiple colons is bare IPv6, already handled above.
    elif value.count(":") == 1:
        value = value.split(":", 1)[0]
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return ""


def _get_client_ip(request) -> str:
    """Return the derived client IP, trusting exactly ``settings.TRUSTED_PROXY_HOPS``
    proxy hops.

    Reads the ``X-Forwarded-For`` entry at position ``-TRUSTED_PROXY_HOPS``
    (rightmost-minus-(N-1)), i.e. the address the trusted proxy itself added,
    so a client-supplied leftmost value cannot spoof it. Falls back to
    ``REMOTE_ADDR`` when hops is 0 or the header is missing/too short. The
    result is validated/normalised as a bare IP (port stripped), so it is safe
    to store directly; returns ``""`` on any failure or an unusable value —
    callers must never break event creation.
    """
    try:
        hops = settings.TRUSTED_PROXY_HOPS
        if hops > 0:
            xff = request.headers.get("x-forwarded-for", "")
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if len(parts) >= hops:
                return _valid_ip(parts[-hops])
        return _valid_ip(request.META.get("REMOTE_ADDR", "") or "")
    except Exception:  # noqa: BLE001 (blind except) — best-effort, must never fail the event
        return ""


def _get_remote_addr(request) -> str:
    """Return the raw TCP peer address (``REMOTE_ADDR``), validated/normalised as
    a bare IP (port stripped) so it is safe to store directly. ``""`` on failure
    or an unusable value — callers must never break event creation.
    """
    try:
        return _valid_ip(request.META.get("REMOTE_ADDR", "") or "")
    except Exception:  # noqa: BLE001 (blind except) — best-effort, must never fail the event
        return ""


def _get_user_agent(request) -> str:
    """Return the User-Agent header, truncated to 512 chars. ``""`` on failure."""
    try:
        return request.headers.get("user-agent", "")[:512]
    except Exception:  # noqa: BLE001 (blind except) — best-effort, must never fail the event
        return ""


def get_request_metadata(request) -> dict:
    """Return all audit metadata from a single request, best-effort.

    Keys:
    - ``ip`` — the derived client IP (trusts ``TRUSTED_PROXY_HOPS`` proxy hops).
      The best guess; spoofable once traffic bypasses the expected ingress.
    - ``forwarded_for`` — the raw, unprocessed ``X-Forwarded-For`` header
      (truncated to 512). Evidence; spoofable and may contain junk.
    - ``remote_addr`` — the TCP peer address (``REMOTE_ADDR``). The only
      non-spoofable element and the tell-tale for traffic bypassing the ingress.
    - ``user_agent`` — the User-Agent header (truncated to 512).

    ``request is None`` yields empty/None values. Every extraction is
    best-effort and never raises, so it can never break event creation.
    """
    if request is None:
        return {"ip": None, "forwarded_for": "", "remote_addr": None, "user_agent": ""}
    try:
        forwarded_for = request.headers.get("x-forwarded-for", "")[:512]
    except Exception:  # noqa: BLE001 (blind except) — best-effort, must never fail the event
        forwarded_for = ""
    # ip and remote_addr land in GenericIPAddressField (inet); their extractors
    # already validate/normalise, returning "" for anything un-storable, so map
    # empty to None here.
    return {
        "ip": _get_client_ip(request) or None,  # derived, trusted hop
        "forwarded_for": forwarded_for,  # raw evidence, unvalidated by design
        "remote_addr": _get_remote_addr(request) or None,  # non-spoofable TCP peer
        "user_agent": _get_user_agent(request),
    }
