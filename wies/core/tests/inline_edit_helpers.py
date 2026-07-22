"""Helpers for posting inline edits from tests.

The inline-edit endpoint checks a save against the state the edit form was
rendered from, so a save must carry the ``_concurrency_token`` of that render.
A POST without one cannot be checked and is treated as a conflict, so tests
have to fetch the form first — the same GET-then-POST the browser does.
"""

import re

_TOKEN_RE = re.compile(r'name="_concurrency_token"\s+value="([^"]*)"')


def inline_edit_token(client, url) -> str:
    """The concurrency token embedded in the edit form at ``url``.

    Returns an empty string when the form carries none (for example when the
    viewer may not edit the field and gets the denial partial instead).
    """
    response = client.get(url, {"edit": "true"})
    match = _TOKEN_RE.search(response.content.decode())
    return match.group(1) if match else ""


def post_inline_edit(client, url, data, **kwargs):
    """POST an inline edit the way the UI does: render the form, then submit
    the given data with the token from that render."""
    payload = {**data, "_concurrency_token": inline_edit_token(client, url)}
    return client.post(url, payload, **kwargs)
