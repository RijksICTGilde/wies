import logging

from django.core.management.base import BaseCommand

from wies.core.roles import setup_roles


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Basic setup for application'

    def handle(self, *args, **options):
        
        setup_roles()
        logger.info("Successfully setup roles")
