"""Management command to sync organizations from organisaties.overheid.nl."""

from dataclasses import asdict

from wies.core.management.task import TaskCommand
from wies.core.services.organizations import sync_organizations


class Command(TaskCommand):
    help = "Sync organizations from organisaties.overheid.nl"

    def add_arguments(self, parser):
        parser.add_argument("--url", type=str, help="Custom XML URL (e.g. a dated archive)")

    def run_task(self, *args, **options):
        # Error handling (logging + failure result) is centralised in TaskCommand.
        return asdict(sync_organizations(url=options.get("url")))
