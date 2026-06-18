"""Client for the Rijksprofielservice PoC.

Handles client-credentials token retrieval (with a tiny in-process cache that
respects the token's `expires_in`) and the batch profile fetch. The token
endpoint is the Rijksprofielservice's own OAuth Authorization Server
(django-oauth-toolkit) — see `RIJKSPROFIELSERVICE_TOKEN_URL`.
"""

import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_token_cache: dict = {"token": None, "expires_at": 0.0}

SESSION_KEY = "rijksprofielservice_profile"


def get_m2m_token() -> str:
    """Fetch a client-credentials token, cached until ~30s before expiry."""
    if _token_cache["token"] and _token_cache["expires_at"] > time.time() + 30:
        return _token_cache["token"]

    headers = {}
    # Local-dev: host.docker.internal als netwerk-route, maar de profielservice'
    # ALLOWED_HOSTS accepteert alleen "localhost" — Host-header overschrijven.
    if settings.RIJKSPROFIELSERVICE_API_HOST_HEADER:
        headers["Host"] = settings.RIJKSPROFIELSERVICE_API_HOST_HEADER

    response = requests.post(
        settings.RIJKSPROFIELSERVICE_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "scope": "read_profile",
            "client_id": settings.RIJKSPROFIELSERVICE_M2M_CLIENT_ID,
            "client_secret": settings.RIJKSPROFIELSERVICE_CLIENT_SECRET,
        },
        headers=headers,
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"]
    return data["access_token"]


def fetch_profiles(subject_ids: list[str]) -> dict[str, dict | None]:
    """Fetch multiple profiles in one call.

    Returns a mapping `{subject_id: profile_dict | None}`. `None` means
    the user has not consented for this app, or the subject is unknown.
    """
    headers = {"Authorization": f"Bearer {get_m2m_token()}"}
    # Local-dev hack: when the API is reached via host.docker.internal, the
    # profile service's ALLOWED_HOSTS only accepts "localhost", so override the
    # Host header to keep its DEBUG-page 400 response from biting us.
    if settings.RIJKSPROFIELSERVICE_API_HOST_HEADER:
        headers["Host"] = settings.RIJKSPROFIELSERVICE_API_HOST_HEADER

    response = requests.post(
        f"{settings.RIJKSPROFIELSERVICE_API_URL}/api/v1/profiles/batch",
        json={"subject_ids": subject_ids},
        headers=headers,
        timeout=5,
    )
    if not response.ok:
        logger.error("Rijksprofielservice batch returned %s: %s", response.status_code, response.text[:500])
    response.raise_for_status()
    return response.json()["profiles"]


def fetch_profile(subject_id: str) -> dict | None:
    """Convenience wrapper for a single subject_id."""
    return fetch_profiles([subject_id]).get(subject_id)


def get_cached_profile(request) -> dict | None:
    """Return the cached profielservice-profiel from the session, or None."""
    return request.session.get(SESSION_KEY)


def refresh_session_profile(request) -> dict | None:
    """Fetch the profile fresh from the service and cache it in the session.

    Returns the existing cached value on transient service errors so the
    menubar doesn't flap when the service is briefly down.
    """
    user = request.user
    sub = getattr(user, "rijksprofielservice_sub", None)
    if not sub:
        request.session.pop(SESSION_KEY, None)
        return None
    try:
        profile = fetch_profile(str(sub))
    except requests.RequestException:
        logger.exception("Failed to refresh Rijksprofielservice profile in session")
        return request.session.get(SESSION_KEY)
    request.session[SESSION_KEY] = profile
    return profile
