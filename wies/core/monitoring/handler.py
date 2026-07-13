"""Logging handler that persists errors and notifies Mattermost.

Attached (production only) to the `django.request` and `wies` loggers at ERROR
level. For each record it always writes an `ErrorEvent` row, then posts a
notification to Mattermost. Any failure inside the handler is swallowed via the
standard `logging.Handler` contract (`handleError`) so it can never break the
request or task being logged.

It is deliberately NOT attached to the root / `requests` / `urllib3` loggers, so
a failing Mattermost/HTTP call can't log-loop back into this handler.
"""

import logging

from django.conf import settings

# Mattermost accepts ~16k chars per message; keep the traceback well under that
# so the surrounding markdown always fits.
MAX_TRACEBACK_CHARS = 6000


class ErrorReportingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            traceback_text = self._format_traceback(record)
            error_event = self._persist(record, traceback_text)
            self._notify(record, error_event, traceback_text)
        except Exception:  # noqa: BLE001 - a logging handler must never raise
            self.handleError(record)

    def _format_traceback(self, record: logging.LogRecord) -> str:
        if not record.exc_info:
            return ""
        return logging.Formatter().formatException(record.exc_info)

    def _persist(self, record: logging.LogRecord, traceback_text: str):
        # Imported lazily so importing this module never pulls in the ORM early.
        from wies.core.models import ErrorEvent  # noqa: PLC0415 - avoid import-time ORM/app-loading
        from wies.core.services.version import get_app_version  # noqa: PLC0415 - keep module import-light

        method = ""
        path = ""
        user = None
        user_email = ""
        request = getattr(record, "request", None)
        if request is not None:
            method = getattr(request, "method", "") or ""
            path = getattr(request, "path", "") or ""
            request_user = getattr(request, "user", None)
            if request_user is not None and getattr(request_user, "is_authenticated", False):
                user = request_user
                user_email = getattr(request_user, "email", "") or ""

        return ErrorEvent.objects.create(
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            traceback=traceback_text,
            method=method,
            path=path[:512],
            user=user,
            user_email=user_email,
            app_version=get_app_version(),
        )

    def _notify(self, record: logging.LogRecord, error_event, traceback_text: str) -> None:
        base_url = getattr(settings, "MATTERMOST_URL", "")
        token = getattr(settings, "MATTERMOST_TOKEN", "")
        channel_id = getattr(settings, "MATTERMOST_CHANNEL_ID", "")
        if not (base_url and token and channel_id):
            return  # DB row is the source of truth; posting is best-effort

        from wies.core.services.mattermost import MattermostClient  # noqa: PLC0415 - lazy, keeps import light

        client = MattermostClient(base_url, token)
        client.post_message(channel_id, self._build_message(record, error_event, traceback_text))

    def _build_message(self, record: logging.LogRecord, error_event, traceback_text: str) -> str:
        lines = [f"🔴 **{record.levelname}** in `{record.name}` (v{error_event.app_version})"]
        if error_event.path:
            where = f"`{error_event.method} {error_event.path}`"
            if error_event.user_email:
                where += f" — {error_event.user_email}"
            lines.append(where)
        lines.append(f"> {record.getMessage()}")
        if traceback_text:
            trimmed = traceback_text[-MAX_TRACEBACK_CHARS:]
            lines.append(f"```\n{trimmed}\n```")
        return "\n".join(lines)
