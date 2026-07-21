"""Tests for the error monitoring handler (wies.core.monitoring)."""

import logging
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from wies.core.models import ErrorEvent
from wies.core.monitoring.handler import ErrorReportingHandler
from wies.core.services import mattermost

User = get_user_model()

MATTERMOST_SETTINGS = {
    "MATTERMOST_TOKEN": "bot-token",
    "MATTERMOST_WIES_OPS_CHANNEL_URL": "https://mm.example.org/chat/odi/channels/wies-team",
    "SITE_BASE_URL": "https://wies.example.org",
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
        self.user = User.objects.create_user(email="user@rijksoverheid.nl", first_name="Test", last_name="User")

        # Never resolve the channel id over the network; return a fixed id. Also
        # clear the module cache so resolutions don't leak between tests.
        mattermost.clear_channel_id_cache()
        self.addCleanup(mattermost.clear_channel_id_cache)
        resolver = patch.object(mattermost.MattermostClient, "resolve_channel_id", return_value="chan123")
        resolver.start()
        self.addCleanup(resolver.stop)

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
        assert event.exception_type == "ValueError"
        assert "invalid literal" in event.exception_message
        assert "ValueError" in event.traceback

        mock_post.assert_called_once()
        channel_id, message = mock_post.call_args.args
        assert channel_id == "chan123"
        assert "ValueError" in message
        assert "/kaboom/" in message
        # Links to the detail page instead of dumping the traceback in chat.
        assert f"https://wies.example.org/beheer/statistieken/fout/{event.pk}/" in message
        assert "Traceback (most recent" not in message

    @override_settings(MATTERMOST_TOKEN="", MATTERMOST_WIES_OPS_CHANNEL_URL="")
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

    @override_settings(**MATTERMOST_SETTINGS)
    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    def test_task_failure_message_shows_type_and_logger_location(self, mock_post):
        # A background-task failure: no request, so the location is the logger name.
        record = logging.LogRecord(
            name="wies.core.management.commands.db_worker",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="kapot",
            args=(),
            exc_info=value_error_exc_info(),
        )

        self.handler.emit(record)

        message = mock_post.call_args.args[1]
        assert "ValueError" in message  # headline is the exception type
        assert "`wies.core.management.commands.db_worker`" in message  # location fallback
        assert "Traceback (most recent" not in message  # traceback stays behind login


@override_settings(**MATTERMOST_SETTINGS, ERROR_THROTTLE_MINUTES=5)
class ErrorThrottleTest(TestCase):
    """The (exception_type, path) throttle: one row + one post per window."""

    def setUp(self):
        self.handler = ErrorReportingHandler()
        mattermost.clear_channel_id_cache()
        self.addCleanup(mattermost.clear_channel_id_cache)
        resolver = patch.object(mattermost.MattermostClient, "resolve_channel_id", return_value="chan123")
        resolver.start()
        self.addCleanup(resolver.stop)

    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    def test_repeat_within_window_is_dropped(self, mock_post):
        exc = value_error_exc_info()
        self.handler.emit(make_record(exc_info=exc))
        self.handler.emit(make_record(exc_info=exc))

        # Same (exception_type, path): only the first is persisted and posted.
        assert ErrorEvent.objects.count() == 1
        mock_post.assert_called_once()

    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    def test_different_keys_each_pass(self, mock_post):
        # Different path → different key → not throttled against each other.
        self.handler.emit(make_record(exc_info=value_error_exc_info(), request=FakeRequest(user=None)))
        other = FakeRequest(user=None)
        other.path = "/other/"
        self.handler.emit(make_record(exc_info=value_error_exc_info(), request=other))

        assert ErrorEvent.objects.count() == 2
        assert mock_post.call_count == 2

    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    def test_passes_again_once_window_has_elapsed(self, mock_post):
        exc = value_error_exc_info()
        self.handler.emit(make_record(exc_info=exc))

        # Age the existing row past the window so the next one is not throttled.
        stale = timezone.now() - timedelta(minutes=6)
        ErrorEvent.objects.update(timestamp=stale)

        self.handler.emit(make_record(exc_info=exc))

        assert ErrorEvent.objects.count() == 2
        assert mock_post.call_count == 2

    @override_settings(ERROR_THROTTLE_MINUTES=0)
    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    def test_throttle_disabled_records_every_time(self, mock_post):
        exc = value_error_exc_info()
        self.handler.emit(make_record(exc_info=exc))
        self.handler.emit(make_record(exc_info=exc))

        assert ErrorEvent.objects.count() == 2
        assert mock_post.call_count == 2


class MattermostChannelUrlTest(TestCase):
    def test_parse_channel_url_with_subpath(self):
        base_url, team, channel = mattermost.parse_channel_url(
            "https://digilab.overheid.nl/chat/odi/channels/wies-team"
        )
        assert base_url == "https://digilab.overheid.nl/chat"
        assert team == "odi"
        assert channel == "wies-team"

    def test_parse_channel_url_without_subpath(self):
        base_url, team, channel = mattermost.parse_channel_url("https://mm.example.org/odi/channels/wies-team")
        assert base_url == "https://mm.example.org"
        assert team == "odi"
        assert channel == "wies-team"

    def test_parse_channel_url_rejects_non_channel_link(self):
        with self.assertRaises(ValueError):  # noqa: PT027 - TestCase style matches this file
            mattermost.parse_channel_url("https://digilab.overheid.nl/chat/odi/messages/foo")

    @override_settings(
        MATTERMOST_TOKEN="bot-token",
        MATTERMOST_WIES_OPS_CHANNEL_URL="https://mm.example.org/chat/odi/channels/wies-team",
    )
    @patch("wies.core.services.mattermost.MattermostClient.post_message")
    @patch("wies.core.services.mattermost.MattermostClient.resolve_channel_id", return_value="chan123")
    def test_send_resolves_channel_id_once_and_caches(self, mock_resolve, mock_post):
        mattermost.clear_channel_id_cache()
        self.addCleanup(mattermost.clear_channel_id_cache)

        assert mattermost.send_ops_message("een") is True
        assert mattermost.send_ops_message("twee") is True

        # Resolution happens once (cached); both messages post to the resolved id.
        mock_resolve.assert_called_once_with("odi", "wies-team")
        assert mock_post.call_count == 2
        assert all(call.args[0] == "chan123" for call in mock_post.call_args_list)

    @override_settings(MATTERMOST_TOKEN="", MATTERMOST_WIES_OPS_CHANNEL_URL="")
    def test_send_noop_when_unconfigured(self):
        assert mattermost.send_ops_message("hallo") is False
