"""Tests for the error monitoring handler (wies.core.monitoring)."""

import logging
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from wies.core.models import ErrorEvent
from wies.core.monitoring.handler import ErrorReportingHandler

User = get_user_model()

MATTERMOST_SETTINGS = {
    "MATTERMOST_URL": "https://mm.example.org",
    "MATTERMOST_TOKEN": "bot-token",
    "MATTERMOST_CHANNEL_ID": "chan123",
}


def value_error_exc_info():
    """Return a real exc_info triple for a ValueError, without an inline raise."""
    try:
        int("not-a-number")
    except ValueError:
        import sys  # noqa: PLC0415 (import not at top level) — only needed inside this helper

        return sys.exc_info()


def make_record(*, exc_info=None, request=None):
    record = logging.LogRecord(
        name="django.request",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Boom on %s",
        args=("/kaboom/",),
        exc_info=exc_info,
    )
    if request is not None:
        record.request = request
    return record


class FakeRequest:
    """Minimal stand-in for an HttpRequest with an authenticated user."""

    method = "GET"
    path = "/kaboom/"

    def __init__(self, user):
        self.user = user


class ErrorReportingHandlerTest(TestCase):
    def setUp(self):
        self.handler = ErrorReportingHandler()
        self.user = User.objects.create_user(
            email="user@rijksoverheid.nl", first_name="Test", last_name="User"
        )

    @override_settings(**MATTERMOST_SETTINGS)
    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    def test_emit_persists_row_and_posts(self, mock_post):
        record = make_record(exc_info=value_error_exc_info(), request=FakeRequest(self.user))

        self.handler.emit(record)

        assert ErrorEvent.objects.count() == 1
        event = ErrorEvent.objects.get()
        assert event.level == "ERROR"
        assert event.logger_name == "django.request"
        assert event.message == "Boom on /kaboom/"
        assert event.method == "GET"
        assert event.path == "/kaboom/"
        assert event.user_email == "user@rijksoverheid.nl"
        assert "ValueError" in event.traceback

        mock_post.assert_called_once()
        channel_id, message = mock_post.call_args.args
        assert channel_id == "chan123"
        assert "ValueError" in message
        assert "/kaboom/" in message

    @override_settings(MATTERMOST_URL="", MATTERMOST_TOKEN="", MATTERMOST_CHANNEL_ID="")
    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    def test_emit_persists_but_skips_post_when_unconfigured(self, mock_post):
        self.handler.emit(make_record())

        assert ErrorEvent.objects.count() == 1
        mock_post.assert_not_called()

    @override_settings(**MATTERMOST_SETTINGS)
    @patch("wies.core.services.mattermost.MattermostClient.post_message", side_effect=RuntimeError("mm down"))
    def test_post_failure_is_swallowed(self, mock_post):
        # Row is still written; the Mattermost failure must not escape emit().
        self.handler.emit(make_record())

        assert ErrorEvent.objects.count() == 1
        mock_post.assert_called_once()

    @override_settings(**MATTERMOST_SETTINGS)
    @patch("wies.core.monitoring.handler.ErrorReportingHandler._persist", side_effect=RuntimeError("db down"))
    def test_persist_failure_is_swallowed(self, mock_persist):
        # A DB write failure must not escape emit() and break the request being logged.
        self.handler.emit(make_record())  # must not raise

        assert ErrorEvent.objects.count() == 0
        mock_persist.assert_called_once()

    @override_settings(**MATTERMOST_SETTINGS)
    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    def test_emit_without_request_still_records(self, mock_post):
        # Worker/task failures have no request attached.
        self.handler.emit(make_record())

        event = ErrorEvent.objects.get()
        assert event.path == ""
        assert event.user is None
        assert event.user_email == ""
        mock_post.assert_called_once()
