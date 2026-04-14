import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Label, Placement, Service

logger = logging.getLogger(__name__)

User = get_user_model()


def _assign_dev_labels(colleague):
    """Give the dev colleague a handful of labels across categories."""
    label_names = {
        "Expertise": ["AI", "Architectuur en technologie", "Cloud en platform technologie"],
        "Merk": ["Rijks ICT Gilde"],
        "Thema": ["Artificiële intelligentie", "Digitale weerbaarheid"],
    }
    for category_name, names in label_names.items():
        labels = Label.objects.filter(category__name=category_name, name__in=names)
        colleague.labels.add(*labels)
    logger.info("Assigned %d labels to initial colleague", colleague.labels.count())


def _create_dev_placements(colleague):
    """Create a mix of current, historical, and split-tile placements for dev."""
    today = timezone.now().date()

    # Find one service per distinct active assignment
    current_services: list[Service] = []
    seen_assignments: set[int] = set()
    for service in (
        Service.objects.filter(assignment__end_date__gte=today)
        .select_related("assignment")
        .order_by("assignment__name")
    ):
        if service.assignment_id not in seen_assignments:
            current_services.append(service)
            seen_assignments.add(service.assignment_id)
        if len(current_services) == 3:  # noqa: PLR2004
            break

    # Find services from completed/historical assignments
    historical_services = list(
        Service.objects.filter(assignment__end_date__lt=today)
        .select_related("assignment")
        .order_by("-assignment__end_date")[:2]
    )

    placement_count = 0
    for service in current_services + historical_services:
        Placement.objects.create(
            colleague=colleague,
            service=service,
            period_source="SERVICE",
            source="wies",
        )
        placement_count += 1

    # Ensure one assignment has both an active and an ended placement for this colleague.
    # Find a sibling service (different skill) on one of the active assignments and create
    # an already-ended placement on it, giving the "split tile" scenario.
    placed_service_ids = {s.pk for s in current_services}
    for service in current_services:
        sibling = (
            Service.objects.filter(assignment=service.assignment)
            .exclude(pk__in=placed_service_ids)
            .select_related("skill")
            .first()
        )
        if sibling:
            Placement.objects.create(
                colleague=colleague,
                service=sibling,
                period_source="PLACEMENT",
                specific_start_date=today.replace(year=today.year - 1),
                specific_end_date=today.replace(month=max(today.month - 2, 1)),
                source="wies",
            )
            placement_count += 1
            break

    logger.info("Created %d placements for initial colleague", placement_count)

    # Make colleague the BM (owner) on one active and one finished assignment
    active_assignment = (
        Assignment.objects.filter(end_date__gte=today).exclude(services__placements__colleague=colleague).first()
    )
    if active_assignment:
        active_assignment.owner = colleague
        active_assignment.save(update_fields=["owner"])
        logger.info("Set colleague as BM on active assignment: %s", active_assignment.name)

    finished_assignment = (
        Assignment.objects.filter(end_date__lt=today).exclude(services__placements__colleague=colleague).first()
    )
    if finished_assignment:
        finished_assignment.owner = colleague
        finished_assignment.save(update_fields=["owner"])
        logger.info("Set colleague as BM on finished assignment: %s", finished_assignment.name)


def _setup_dev_profile(colleague):
    """Populate the initial user's colleague with labels and placements for dev."""
    if not colleague.labels.exists():
        _assign_dev_labels(colleague)
    else:
        logger.info("Colleague already has labels, skipping dev profile setup")

    if not colleague.placements.exists():
        _create_dev_placements(colleague)


class Command(BaseCommand):
    help = (
        "Set up the initial user's Colleague profile with dev data. "
        "Reads INITIAL_USER_EMAIL from environment. "
        "Creates Colleague if needed, populates labels and placements in DEBUG mode."
    )

    def handle(self, *args, **options):
        email = os.environ.get("INITIAL_USER_EMAIL", "")

        if not email:
            logger.info("INITIAL_USER_EMAIL not set, skipping")
            return

        user = User.objects.filter(email=email).first()
        if not user:
            logger.info("User %s not found, skipping (run ensure_initial_user first)", email)
            return

        # Ensure Colleague exists (needed before dev profile setup)
        colleague, created = Colleague.objects.get_or_create(
            email=email,
            source="wies",
            defaults={
                "name": f"{user.first_name} {user.last_name}".strip() or email,
                "user": user,
            },
        )
        if created:
            logger.info("Created initial colleague: %s", email)
        elif colleague.user_id != user.id:
            colleague.user = user
            colleague.save(update_fields=["user"])

        if settings.DEBUG:
            _setup_dev_profile(colleague)
