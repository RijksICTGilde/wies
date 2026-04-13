import logging
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Ensure an initial admin user exists. "
        "Reads INITIAL_USER_EMAIL (required), INITIAL_USER_FIRSTNAME and INITIAL_USER_LASTNAME (optional) "
        "from environment. Idempotent: skips if user already exists."
    )

    def handle(self, *args, **options):
        email = os.environ.get("INITIAL_USER_EMAIL", "")

        if not email:
            logger.info("Initial user not created: INITIAL_USER_EMAIL not set")
            return

        if User.objects.filter(email=email).exists():
            logger.info("Initial user already exists (%s), skipping", email)
            return

        first_name = os.environ.get("INITIAL_USER_FIRSTNAME", "")
        last_name = os.environ.get("INITIAL_USER_LASTNAME", "")

        if not first_name or not last_name:
            logger.warning(
                "INITIAL_USER_FIRSTNAME or INITIAL_USER_LASTNAME not set, creating user with empty name fields"
            )

        user = User.objects.create_user(email=email, first_name=first_name, last_name=last_name)

        for group in Group.objects.all():
            user.groups.add(group)
        logger.info("Successfully created initial user: %s", email)
