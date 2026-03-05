"""Assign labels to colleagues that have none.

Used after loading fixture data (base_dummy_data.json) to populate labels
on colleagues, since label PKs are non-deterministic and can't be hardcoded
in the fixture.

Usage:
    python manage.py assign_random_labels_to_colleagues
"""

import logging
import random

from django.core.management.base import BaseCommand

from wies.core.models import Colleague, LabelCategory

logger = logging.getLogger(__name__)

MULTI_LABEL_PROBABILITY = 0.3
MAX_LABELS_PER_CATEGORY = 2


class Command(BaseCommand):
    help = "Assign labels to colleagues that have no labels"

    def handle(self, *args, **options):
        colleagues_without_labels = list(Colleague.objects.filter(labels__isnull=True).distinct())
        if not colleagues_without_labels:
            self.stdout.write("No colleagues without labels found")
            return

        labels_by_category = {category: list(category.labels.all()) for category in LabelCategory.objects.all()}
        labels_by_category = {k: v for k, v in labels_by_category.items() if v}

        if not labels_by_category:
            self.stdout.write(self.style.WARNING("No labels found — run 'python manage.py setup' first"))
            return

        rng = random.Random(42)  # noqa: S311

        for colleague in colleagues_without_labels:
            colleague_labels = []
            for labels in labels_by_category.values():
                has_enough = len(labels) >= MAX_LABELS_PER_CATEGORY
                n = MAX_LABELS_PER_CATEGORY if has_enough and rng.random() < MULTI_LABEL_PROBABILITY else 1
                colleague_labels.extend(rng.sample(labels, n))
            colleague.labels.set(colleague_labels)

        self.stdout.write(f"Assigned labels to {len(colleagues_without_labels)} colleagues")
