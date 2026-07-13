"""Basic production error monitoring.

Captures unhandled server errors (500) and background task failures via a single
logging handler, persists them as `ErrorEvent` rows (inspectable by staff on the
statistieken page) and posts a notification to Mattermost (via
`wies.core.services.mattermost`).

Wired up only in `config.settings.production` LOGGING, so it never fires in
local/test.
"""

from wies.core.monitoring.handler import ErrorReportingHandler

__all__ = ["ErrorReportingHandler"]
