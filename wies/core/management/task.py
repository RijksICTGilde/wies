"""Base class for management commands that run as background Tasks.

Lives outside ``commands/`` (so Django does not treat it as a runnable command).
"""

import logging

from django.core.management.base import BaseCommand


class TaskCommand(BaseCommand):
    """Base for management commands run as background Tasks by ``db_worker``.

    Subclasses implement :meth:`run_task` and return a JSON-serialisable payload.
    This base owns the success/failure result protocol and error logging, so
    neither the worker nor each command needs its own try/except:

    - success -> ``self.result = {"success": True, "result": <payload>}``
    - failure -> ``self.result = {"success": False, "error": <message>}`` and the
      exception is logged with its traceback (``logger.exception``), which the
      error-monitoring handler records as a single ErrorEvent with a traceback.

    Because ``handle`` always sets ``self.result``, a failing task is marked
    failed immediately instead of hanging in ``running`` until its timeout.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = None

    def run_task(self, *args, **options):
        """Do the work and return a JSON-serialisable success payload."""
        raise NotImplementedError

    def handle(self, *args, **options):
        try:
            payload = self.run_task(*args, **options)
        except Exception as e:
            # Log against the concrete command's module so the captured ErrorEvent's
            # location is the actual task (e.g. ...commands.sync_organizations),
            # not this base module.
            logging.getLogger(self.__class__.__module__).exception("Task command failed")
            self.result = {"success": False, "error": str(e)}
        else:
            self.result = {"success": True, "result": payload}
