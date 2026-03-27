"""Download profile pictures from randomuser.me.

Run once to populate the profile_pictures/ folder. Other commands
(load_full_data, assign_profile_pictures) read from this folder.

Usage:
    python manage.py download_profile_pictures
    python manage.py download_profile_pictures --count 50
"""

import logging
from pathlib import Path

import requests
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

PROFILE_PICTURES_DIR = Path(__file__).resolve().parents[4] / "profile_pictures"
DEFAULT_COUNT = 100
BATCH_SIZE = 100


class Command(BaseCommand):
    help = "Download profile pictures from randomuser.me"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=DEFAULT_COUNT,
            help=f"Number of pictures to download (default: {DEFAULT_COUNT})",
        )

    def handle(self, *args, **options):
        count = options["count"]
        PROFILE_PICTURES_DIR.mkdir(exist_ok=True)

        downloaded = 0
        skipped = 0

        for batch_start in range(0, count, BATCH_SIZE):
            batch_count = min(BATCH_SIZE, count - batch_start)

            try:
                api_response = requests.get(
                    f"https://randomuser.me/api/?results={batch_count}&inc=picture",
                    timeout=30,
                )
                api_response.raise_for_status()
                results = api_response.json()["results"]
            except requests.RequestException as e:
                self.stderr.write(f"Failed to fetch batch at {batch_start}: {e}")
                continue

            for j, result in enumerate(results):
                i = batch_start + j + 1
                filepath = PROFILE_PICTURES_DIR / f"{i:03d}.jpg"

                if filepath.exists():
                    skipped += 1
                    continue

                img_url = result["picture"]["large"]
                try:
                    img_response = requests.get(img_url, timeout=10)
                    img_response.raise_for_status()
                    filepath.write_bytes(img_response.content)
                    downloaded += 1
                except requests.RequestException as e:
                    self.stderr.write(f"Failed to download {img_url}: {e}")

            self.stdout.write(f"Batch {batch_start + 1}-{batch_start + batch_count}: done")

        self.stdout.write(f"Downloaded {downloaded}, skipped {skipped} existing")
