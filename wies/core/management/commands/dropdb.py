from django.core import management
from django.core.management.base import BaseCommand


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
        self.stdout.write("Flushing database (clearing all data)...")

        management.call_command(
            "flush",
            interactive=not options["noinput"],
            verbosity=options.get("verbosity", 1),
        )

        self.stdout.write(self.style.SUCCESS("Database flushed successfully"))
