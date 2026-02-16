"""Management command to sync organizations from organisaties.overheid.nl."""

import logging
from dataclasses import asdict

from django.core.management.base import BaseCommand

from wies.core.services.organizations import sync_organizations

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync organizations from organisaties.overheid.nl. Can be used as task"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = None

    def handle(self, *args, **options):
        """Execute organization sync and store result in self.result."""
        try:
            result = sync_organizations()
        except Exception as e:
            logger.exception("Sync failed")

            self.result = {
                "success": False,
                "error": str(e),
            }
        else:
            self.result = {
                "success": True,
                "result": asdict(result),
            }
