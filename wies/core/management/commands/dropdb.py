from django.core import management
from django.core.management.base import BaseCommand

from wies.core.management.task import require_destructive_actions_enabled


class Command(BaseCommand):
    help = "Clears all data from the database (wrapper around flush)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_true",
            help="Do not prompt for confirmation",
        )

    def handle(self, *args, **options):
        require_destructive_actions_enabled()
        self.stdout.write("Flushing database (clearing all data)...")

        management.call_command(
            "flush",
            interactive=not options["noinput"],
            verbosity=options.get("verbosity", 1),
        )

        self.stdout.write(self.style.SUCCESS("Database flushed successfully"))
