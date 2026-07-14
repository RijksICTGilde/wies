"""Basic production error monitoring.

Captures unhandled server errors (500) and background task failures via a single
logging handler, persists them as `ErrorEvent` rows (inspectable by staff on the
statistieken page) and posts a notification to Mattermost (via
`wies.core.services.mattermost`).

Wired up in `config.settings.production` and `config.settings.local` LOGGING (local
mirrors production so the feature is testable in dev); deliberately left out of
`config.settings.test`, so it never fires during the test suite.
"""

from wies.core.monitoring.handler import ErrorReportingHandler

__all__ = ["ErrorReportingHandler"]
