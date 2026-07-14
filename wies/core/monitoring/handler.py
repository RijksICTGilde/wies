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


class ErrorReportingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            traceback_text = self._format_traceback(record)
            error_event = self._persist(record, traceback_text)
            self._notify(record, error_event)
        except Exception:  # noqa: BLE001 - a logging handler must never raise
            self.handleError(record)

    def _format_traceback(self, record: logging.LogRecord) -> str:
        if not record.exc_info:
            return ""
        return logging.Formatter().formatException(record.exc_info)

    def _persist(self, record: logging.LogRecord, traceback_text: str):
        from wies.core.models import ErrorEvent  # noqa: PLC0415 - avoids AppRegistryNotReady at startup
        from wies.core.services.version import get_app_version  # noqa: PLC0415 - deferred with the models import above

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

        exception_type = ""
        exception_message = ""
        if record.exc_info:
            exc_type, exc_value = record.exc_info[0], record.exc_info[1]
            if exc_type is not None:
                exception_type = exc_type.__name__
            if exc_value is not None:
                exception_message = str(exc_value)

        return ErrorEvent.objects.create(
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            exception_type=exception_type,
            exception_message=exception_message,
            traceback=traceback_text,
            method=method,
            path=path[:512],
            user=user,
            user_email=user_email,
            app_version=get_app_version(),
        )

    def _notify(self, record: logging.LogRecord, error_event) -> None:
        # DB row is the source of truth; posting is best-effort and no-ops when
        # Mattermost is not configured.
        from wies.core.services.mattermost import send_ops_message  # noqa: PLC0415 - deferred until an error is logged

        send_ops_message(self._build_message(record, error_event))

    def _build_message(self, record: logging.LogRecord, error_event) -> str:
        from django.conf import settings  # noqa: PLC0415 - deferred until an error is logged
        from django.urls import reverse  # noqa: PLC0415 - deferred until an error is logged

        headline = error_event.short_description or record.levelname
        lines = [f"🔴 **{headline}** (v{error_event.app_version})"]
        # Location: the request path for web errors, else the logger name (e.g. for
        # background-task failures), mirroring how the URL shows for web errors.
        where = f"{error_event.method} {error_event.path}".strip() or error_event.logger_name
        if where:
            lines.append(f"`{where}`")

        base_url = getattr(settings, "SITE_BASE_URL", "")
        if base_url:
            detail_url = f"{base_url}{reverse('error-detail', args=[error_event.pk])}"
            lines.append(f"[Bekijk details]({detail_url})")

        return "\n".join(lines)
