import os
import logging

from django.core.management.base import BaseCommand

from wies.core.services.colleagues import create_colleague


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create colleague from values in .env file such that developer can login with SSO'

    def handle(self, *args, **options):
        
        first_name = os.environ.get('DEV_FIRSTNAME', '')
        last_name = os.environ.get('DEV_LASTNAME', '')
        email = os.environ.get("DEV_EMAIL", '')

        if '' in (first_name, last_name, email):
            logger.warning('Development colleague not added: missing DEV_FIRSTNAME, DEV_LASTNAME or DEV_EMAIL')
            return
        
        create_colleague(first_name, last_name, email)
        logger.info("Successfully added development colleague")
