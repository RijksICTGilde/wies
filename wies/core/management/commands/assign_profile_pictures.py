"""Assign profile pictures to colleagues that have none.

Reads images from profile_pictures/ folder and assigns them to colleagues
without a profile picture. Used after loading fixture data (base_dummy_data.json).

Usage:
    python manage.py assign_profile_pictures
"""

import logging

from django.core.management.base import BaseCommand

from wies.core.management.commands.download_profile_pictures import PROFILE_PICTURES_DIR
from wies.core.models import Colleague
from wies.core.services.images import process_profile_picture

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Assign profile pictures to colleagues that have no picture"

    def handle(self, *args, **options):
        colleagues = list(Colleague.objects.filter(profile_picture__isnull=True).order_by("pk"))
        if not colleagues:
            self.stdout.write("No colleagues without profile pictures found")
            return

        if not PROFILE_PICTURES_DIR.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No profile_pictures/ folder found — run 'python manage.py download_profile_pictures' first"
                )
            )
            return

        assigned = 0
        for i, colleague in enumerate(colleagues, start=1):
            picture_path = PROFILE_PICTURES_DIR / f"{i:03d}.jpg"
            if not picture_path.exists():
                continue

            image_bytes, content_type, image_hash = process_profile_picture(picture_path.read_bytes())
            colleague.profile_picture = image_bytes
            colleague.profile_picture_content_type = content_type
            colleague.profile_picture_hash = image_hash
            colleague.save(update_fields=["profile_picture", "profile_picture_content_type", "profile_picture_hash"])
            assigned += 1

        self.stdout.write(f"Assigned profile pictures to {assigned} colleagues")
