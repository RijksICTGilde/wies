#!/usr/bin/env python3
"""
Standalone script to test the Mattermost bot integration.

Does two things:
  1. Fetches the email addresses of all members of a team.
  2. Posts a message to a channel.

Usage:
    export MATTERMOST_URL="https://mattermost.example.org"
    export MATTERMOST_TOKEN="xxx-bot-access-token-xxx"
    uv run --with requests python scripts/mattermost_bot_test.py \
        --team "rijks-ict-gilde" \
        --channel-team "rijks-ict-gilde" \
        --channel "rig-opdrachten" \
        --message "Hallo vanuit de wies-bot 👋"

Team/channel names are the URL-style names (lowercase, dashes), not display names.
"""

from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import urljoin

import requests


class MattermostClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _get(self, path: str, **kwargs) -> requests.Response:
        url = urljoin(self.base_url, path.lstrip("/"))
        r = self.session.get(url, **kwargs)
        r.raise_for_status()
        return r

    def _post(self, path: str, json: dict) -> requests.Response:
        url = urljoin(self.base_url, path.lstrip("/"))
        r = self.session.post(url, json=json)
        r.raise_for_status()
        return r

    def get_team_by_name(self, name: str) -> dict:
        return self._get(f"api/v4/teams/name/{name}").json()

    def get_channel_by_name(self, team_id: str, channel_name: str) -> dict:
        return self._get(f"api/v4/teams/{team_id}/channels/name/{channel_name}").json()

    def get_team_member_emails(self, team_id: str, page_size: int = 200) -> list[str]:
        emails: list[str] = []
        page = 0
        while True:
            users = self._get(
                "api/v4/users",
                params={"in_team": team_id, "page": page, "per_page": page_size},
            ).json()

            print(users)

            if not users:
                break
            for u in users:
                email = u.get("email")
                if email:
                    emails.append(email)
            if len(users) < page_size:
                break
            page += 1
        return emails

    def post_message(self, channel_id: str, message: str) -> dict:
        return self._post("api/v4/posts", json={"channel_id": channel_id, "message": message}).json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--team",
        required=True,
        help="Team URL-name to fetch members from (e.g. 'rijks-ict-gilde').",
    )
    parser.add_argument(
        "--channel-team",
        required=True,
        help="Team URL-name that owns the channel to post in.",
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Channel URL-name to post in (e.g. 'rig-opdrachten').",
    )
    parser.add_argument(
        "--message",
        default="Test bericht van de wies-bot.",
        help="Message to post.",
    )
    args = parser.parse_args()

    base_url = os.environ.get("MATTERMOST_URL")
    token = os.environ.get("MATTERMOST_TOKEN")
    if not base_url or not token:
        print(
            "ERROR: set MATTERMOST_URL and MATTERMOST_TOKEN environment variables.",
            file=sys.stderr,
        )
        return 1

    client = MattermostClient(base_url, token)

    print(f"Fetching team '{args.team}'...")
    team = client.get_team_by_name(args.team)
    print(f"  -> team id = {team['id']}")

    print(f"Fetching member emails for team '{args.team}'...")
    emails = client.get_team_member_emails(team["id"])
    print(f"  -> {len(emails)} email addresses found")
    for email in emails:
        print(f"     {email}")
    if not emails:
        print("  (no emails returned — check 'Show Email Address' setting or that the bot has permission to read them)")

    print(f"\nResolving channel '{args.channel}' in team '{args.channel_team}'...")
    channel_team = team if args.channel_team == args.team else client.get_team_by_name(args.channel_team)
    channel = client.get_channel_by_name(channel_team["id"], args.channel)
    print(f"  -> channel id = {channel['id']}")

    # print(f"Posting message to '{args.channel}'...")
    # post = client.post_message(channel["id"], args.message)
    # print(f"  -> post id = {post['id']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
