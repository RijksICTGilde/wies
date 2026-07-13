"""Mattermost bot integration.

Slimmed down from the exploratory `scripts/mattermost_bot_test.py`: only the
post-a-message path we need, authenticating with a bot token.

`send_ops_message` is the entry point for the rest of the app — it targets the
Wies ops channel and reads all Mattermost config from settings, so callers never
handle URLs, tokens or channel ids.
"""

from urllib.parse import urljoin

import requests
from django.conf import settings

POST_TIMEOUT_SECONDS = 5


class MattermostClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

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
    (any of URL / token / ops channel id missing). Raises on an actual HTTP
    failure, so callers that must not break decide whether to swallow it.
    """
    base_url = getattr(settings, "MATTERMOST_URL", "")
    token = getattr(settings, "MATTERMOST_TOKEN", "")
    channel_id = getattr(settings, "MATTERMOST_WIES_OPS_CHANNEL_ID", "")
    if not (base_url and token and channel_id):
        return False

    MattermostClient(base_url, token).post_message(channel_id, message)
    return True
