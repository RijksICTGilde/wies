"""Assign labels and a suborganization to colleagues that have none.

Used after loading fixture data (base_dummy_data.json) to populate labels and
a suborganization (merk) on colleagues, since their PKs are non-deterministic
and can't be hardcoded in the fixture (the same reason applies to both — they
are seeded by ``python manage.py setup``, not the fixture).

Usage:
    python manage.py assign_random_labels_to_colleagues
"""

import logging
import random

from django.core.management.base import BaseCommand

from wies.core.models import Colleague, Label, LabelCategory, Suborganization

logger = logging.getLogger(__name__)

MULTI_LABEL_PROBABILITY = 0.3
MAX_LABELS_PER_CATEGORY = 2

# Demo-only label category so the RIG subdivision can be filtered on the Bezetting
# page. Kept out of DEFAULT_LABELS on purpose: in production this category is a
# deliberate post-release action, not something that seeds automatically.
SUBGROEP_CATEGORY = "Subgroep"
SUBGROEP_COLOR = "#C4DBB7"
SUBGROEP_LABELS = ("IT gilde", "Data en AI gilde")


class Command(BaseCommand):
    help = "Assign labels and a suborganization to colleagues that have none"

    def handle(self, *args, **options):
        rng = random.Random(42)  # noqa: S311
        self._ensure_subgroep_category()
        self._assign_labels(rng)
        self._assign_suborganizations(rng)

    def _ensure_subgroep_category(self):
        """Create the demo-only 'Subgroep' category and its labels if absent."""
        category, created = LabelCategory.objects.get_or_create(
            name=SUBGROEP_CATEGORY, defaults={"color": SUBGROEP_COLOR}
        )
        for label_name in SUBGROEP_LABELS:
            Label.objects.get_or_create(name=label_name, category=category)
        if created:
            self.stdout.write(f"Created demo label category '{SUBGROEP_CATEGORY}'")

    def _assign_labels(self, rng):
        colleagues_without_labels = list(Colleague.objects.filter(labels__isnull=True).distinct())
        if not colleagues_without_labels:
            self.stdout.write("No colleagues without labels found")
            return

        labels_by_category = {category: list(category.labels.all()) for category in LabelCategory.objects.all()}
        labels_by_category = {k: v for k, v in labels_by_category.items() if v}

        if not labels_by_category:
            self.stdout.write(self.style.WARNING("No labels found — run 'python manage.py setup' first"))
            return

        for colleague in colleagues_without_labels:
            colleague_labels = []
            for labels in labels_by_category.values():
                has_enough = len(labels) >= MAX_LABELS_PER_CATEGORY
                n = MAX_LABELS_PER_CATEGORY if has_enough and rng.random() < MULTI_LABEL_PROBABILITY else 1
                colleague_labels.extend(rng.sample(labels, n))
            colleague.labels.set(colleague_labels)

        self.stdout.write(f"Assigned labels to {len(colleagues_without_labels)} colleagues")

    def _assign_suborganizations(self, rng):
        colleagues_without_suborg = list(Colleague.objects.filter(suborganization__isnull=True))
        if not colleagues_without_suborg:
            self.stdout.write("No colleagues without a suborganization found")
            return

        suborganizations = list(Suborganization.objects.all())
        if not suborganizations:
            self.stdout.write(self.style.WARNING("No suborganizations found — run 'python manage.py setup' first"))
            return

        for colleague in colleagues_without_suborg:
            colleague.suborganization = rng.choice(suborganizations)
            colleague.save(update_fields=["suborganization"])

        self.stdout.write(f"Assigned a suborganization to {len(colleagues_without_suborg)} colleagues")
