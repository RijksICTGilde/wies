"""Generate dummy data with a chosen size profile.

    python manage.py load_dummy_data --profile base   # small, offline
    python manage.py load_dummy_data --profile full   # large, network sync

The generation itself lives in ``load_full_data.generate`` so the two entry
points share one implementation. See that module's docstring for the profiles.
"""

from django.core.management.base import BaseCommand

from wies.core.management.commands.load_full_data import PROFILES, generate


class Command(BaseCommand):
    help = "Generate dummy data for a size profile (base = small/offline, full = large/network sync)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            choices=sorted(PROFILES),
            default="base",
            help="Which size profile to generate (default: base).",
        )

    def handle(self, *args, **options):
        generate(PROFILES[options["profile"]], write=self.stdout.write)
        self.stdout.write(self.style.SUCCESS("Done!"))
