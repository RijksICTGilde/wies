"""Minimal Mattermost bot client for posting notifications.

Slimmed down from the exploratory `scripts/mattermost_bot_test.py`: only the
post-a-message path production needs, authenticating with a bot token.
"""

from urllib.parse import urljoin

import requests

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
