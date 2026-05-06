import logging
import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Event, Label, Placement, Service

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
                specific_end_date=today - timedelta(days=60),
                source="wies",
            )
            placement_count += 1
            break

    logger.info("Created %d placements for initial colleague", placement_count)

    # Claim "Rijke historie" assignment (has event history for testing the timeline)
    rijke_historie = Assignment.objects.filter(name="Rijke historie").first()
    if rijke_historie and rijke_historie.owner_id != colleague.id:
        rijke_historie.owner = colleague
        rijke_historie.save(update_fields=["owner"])
        logger.info("Set colleague as BM on 'Rijke historie'")

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


def _link_users_to_colleagues():
    """Create User accounts for fixture colleagues that don't have one, so events can reference them."""
    linked = 0
    for colleague in Colleague.objects.filter(user__isnull=True).exclude(email=""):
        user, created = User.objects.get_or_create(
            email=colleague.email,
            defaults={
                "first_name": colleague.name.split()[0] if colleague.name else "",
                "last_name": " ".join(colleague.name.split()[1:]) if colleague.name else "",
            },
        )
        colleague.user = user
        colleague.save(update_fields=["user"])
        if created:
            linked += 1
    if linked:
        logger.info("Created %d users for fixture colleagues", linked)


def _link_events_to_users():
    """Back-fill user FK on events that have a user_email matching an existing user."""
    updated = (
        Event.objects.filter(user__isnull=True)
        .exclude(user_email="")
        .update(user=models.Subquery(User.objects.filter(email=models.OuterRef("user_email")).values("pk")[:1]))
    )
    if updated:
        logger.info("Linked %d events to users", updated)


def _setup_dev_profile(colleague):
    """Populate the initial user's colleague with labels and placements for dev.

    Group/permission membership for the dev user is handled by
    ``ensure_initial_user`` (it adds the user to all groups). The dev
    user is also a Django superuser, which bypasses every rule via the
    ``has_permission`` engine's short-circuit.
    """
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
            _link_users_to_colleagues()
            _link_events_to_users()
