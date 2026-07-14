"""Mattermost bot integration.

Slimmed down from the exploratory `scripts/mattermost_bot_test.py`: only the
post-a-message path we need, authenticating with a bot token.

`send_ops_message` is the entry point for the rest of the app — it targets the
Wies ops channel and reads all Mattermost config from settings, so callers never
handle URLs, tokens or channel ids.

Config is a single channel *link* (e.g.
``https://digilab.overheid.nl/chat/odi/channels/wies-team``) rather than a raw
channel id, because the link is what an admin can copy straight from the browser.
The API base, team name and channel name are parsed from it, and the numeric
channel id is resolved via the API (and cached, so it costs one extra request the
first time only).
"""

from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings

POST_TIMEOUT_SECONDS = 5

# Resolved channel ids, keyed by (base_url, team, channel). A channel's id never
# changes, so caching for the process lifetime is safe and avoids a lookup per
# error. Only successful resolutions are cached.
_channel_id_cache: dict[tuple[str, str, str], str] = {}


def clear_channel_id_cache() -> None:
    """Drop cached channel-id resolutions (used by tests)."""
    _channel_id_cache.clear()


def parse_channel_url(channel_url: str) -> tuple[str, str, str]:
    """Split a Mattermost channel link into (base_url, team_name, channel_name).

    ``https://host/chat/odi/channels/wies-team`` ->
        ("https://host/chat", "odi", "wies-team")

    The base url keeps any subpath (e.g. ``/chat``) that precedes the team
    segment, so API calls hit ``<base_url>/api/v4/...``. Raises ValueError if the
    link is not of the form ``.../<team>/channels/<channel>``.
    """
    parsed = urlparse(channel_url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 3 or parts[-2] != "channels":  # noqa: PLR2004 - <team>/channels/<channel>
        msg = f"Not a Mattermost channel URL: {channel_url!r}"
        raise ValueError(msg)

    channel_name = parts[-1]
    team_name = parts[-3]
    prefix = "/".join(parts[:-3])  # subpath before the team segment, e.g. "chat"
    base_path = f"/{prefix}" if prefix else ""
    base_url = f"{parsed.scheme}://{parsed.netloc}{base_path}"
    return base_url, team_name, channel_name


class MattermostClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _get(self, path: str) -> dict:
        response = self.session.get(urljoin(self.base_url, path), timeout=POST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()

    def resolve_channel_id(self, team_name: str, channel_name: str) -> str:
        team = self._get(f"api/v4/teams/name/{team_name}")
        channel = self._get(f"api/v4/teams/{team['id']}/channels/name/{channel_name}")
        return channel["id"]

    def post_message(self, channel_id: str, message: str) -> None:
        url = urljoin(self.base_url, "api/v4/posts")
        response = self.session.post(
            url,
            json={"channel_id": channel_id, "message": message},
            timeout=POST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()


def send_ops_message(message: str) -> bool:
    """Post a message to the Wies ops channel.

    Returns True if the message was sent, False if Mattermost is not configured
    (channel link or token missing). Raises on an actual HTTP failure, so callers
    that must not break decide whether to swallow it.
    """
    channel_url = getattr(settings, "MATTERMOST_WIES_OPS_CHANNEL_URL", "")
    token = getattr(settings, "MATTERMOST_TOKEN", "")
    if not (channel_url and token):
        return False

    base_url, team_name, channel_name = parse_channel_url(channel_url)
    client = MattermostClient(base_url, token)

    cache_key = (base_url, team_name, channel_name)
    channel_id = _channel_id_cache.get(cache_key)
    if channel_id is None:
        channel_id = client.resolve_channel_id(team_name, channel_name)
        _channel_id_cache[cache_key] = channel_id

    client.post_message(channel_id, message)
    return True
