import logging
import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from wies.core.models import Colleague, Label, Placement, Service, User
from wies.core.services.users import create_user

logger = logging.getLogger(__name__)


def _setup_dev_profile(colleague):
    """Populate the initial user's colleague with labels and placements for dev."""
    if colleague.labels.exists():
        logger.info("Colleague already has labels, skipping dev profile setup")
        return

    # Assign labels per category
    label_names = {
        "Expertise": ["AI", "Architectuur en technologie", "Cloud en platform technologie"],
        "Merk": ["Rijks ICT Gilde"],
        "Thema": ["Artificiële intelligentie", "Digitale weerbaarheid"],
    }
    for category_name, names in label_names.items():
        labels = Label.objects.filter(category__name=category_name, name__in=names)
        colleague.labels.add(*labels)

    assigned_count = colleague.labels.count()
    logger.info("Assigned %d labels to initial colleague", assigned_count)

    # Create placements for a mix of current and historical assignments
    if colleague.placements.exists():
        return

    today = timezone.now().date()

    # Find services from current/active assignments
    current_services = (
        Service.objects.filter(assignment__end_date__gte=today)
        .select_related("assignment")
        .order_by("assignment__name")[:3]
    )

    # Find services from completed/historical assignments
    historical_services = (
        Service.objects.filter(assignment__end_date__lt=today)
        .select_related("assignment")
        .order_by("-assignment__end_date")[:2]
    )

    placement_count = 0
    for service in list(current_services) + list(historical_services):
        Placement.objects.create(
            colleague=colleague,
            service=service,
            period_source="SERVICE",
            source="wies",
        )
        placement_count += 1

    logger.info("Created %d placements for initial colleague", placement_count)


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

        user = create_user(None, first_name, last_name, email)

        for group in Group.objects.all():
            user.groups.add(group)
        logger.info("Successfully created initial user: %s", email)

        if not Colleague.objects.filter(email=email).exists():
            Colleague.objects.create(
                name=f"{first_name} {last_name}".strip(),
                source="wies",
                email=email,
            )
            logger.info("Successfully created initial colleague: %s", email)

        # In dev, populate the profile with labels and placements
        if settings.DEBUG:
            colleague = Colleague.objects.filter(email=email).first()
            if colleague:
                _setup_dev_profile(colleague)
