import logging

from django.core.management.base import BaseCommand

from wies.core.models import DEFAULT_LABELS, DEFAULT_SUBORGANIZATIONS, Label, LabelCategory, Suborganization
from wies.core.roles import setup_roles

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Basic setup for application"

    def handle(self, *args, **options):
        setup_roles()
        logger.info("Successfully setup roles")

        # setting up label categories and labels if completely empty
        if LabelCategory.objects.count() == 0:
            for category_name, category_vals in DEFAULT_LABELS.items():
                category = LabelCategory.objects.create(name=category_name, color=category_vals["color"])
                for label_name in category_vals["labels"]:
                    Label.objects.create(name=label_name, category=category)
                logger.info("Successfully setup label categories and labels")

        # setting up suborganizations (merken) if completely empty
        if Suborganization.objects.count() == 0:
            for suborganization_name in DEFAULT_SUBORGANIZATIONS:
                Suborganization.objects.create(name=suborganization_name)
            logger.info("Successfully setup suborganizations")
