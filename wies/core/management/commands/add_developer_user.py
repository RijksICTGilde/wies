import os
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from wies.core.services.users import create_user


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create user from values in .env file such that developer can login with SSO'

    def handle(self, *args, **options):
        
        first_name = os.environ.get('DEV_FIRSTNAME', '')
        last_name = os.environ.get('DEV_LASTNAME', '')
        email = os.environ.get("DEV_EMAIL", '')

        if '' in (first_name, last_name, email):
            logger.warning('Developer user not added: missing DEV_FIRSTNAME, DEV_LASTNAME or DEV_EMAIL')
            return
        
        user = create_user(first_name, last_name, email)
        admin_group = Group.objects.get(name='Beheerder')
        user.groups.add(admin_group)
        logger.info("Successfully added developer user")
