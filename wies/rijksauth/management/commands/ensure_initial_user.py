import logging
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from wies.core.roles import role_label
from wies.core.services.events import create_event

logger = logging.getLogger(__name__)

User = get_user_model()

# The variable is the switch: while it is set, every start puts the roles back.
# Removing it after the deploy is what ends that, so say so where it is noticed.
STILL_SET = (
    "INITIAL_USER_EMAIL is still set for %s; remove it and redeploy, "
    "or every start keeps restoring that account's roles"
)


class Command(BaseCommand):
    help = (
        "Ensure the initial user exists and holds every role. "
        "Reads INITIAL_USER_EMAIL (required), INITIAL_USER_FIRSTNAME and INITIAL_USER_LASTNAME (optional) "
        "from environment. Runs on every start: while the variable is set the roles are restored, which is "
        "the way back in when the last Gebruikersbeheerder is gone. Remove the variable once the deploy is done."
    )

    def handle(self, *args, **options):
        email = os.environ.get("INITIAL_USER_EMAIL", "")

        if not email:
            logger.info("Initial user not ensured: INITIAL_USER_EMAIL not set")
            return

        user = User.objects.filter(email__iexact=email).first()
        created = user is None
        if created:
            user = self._create(email)

        granted = self._grant_every_role(user)

        if created or granted:
            self._record(user, created=created, granted=granted)
        else:
            logger.warning(STILL_SET, user.email)

    def _create(self, email):
        first_name = os.environ.get("INITIAL_USER_FIRSTNAME", "")
        last_name = os.environ.get("INITIAL_USER_LASTNAME", "")

        if not first_name or not last_name:
            logger.warning(
                "INITIAL_USER_FIRSTNAME or INITIAL_USER_LASTNAME not set, creating user with empty name fields"
            )

        # Deliberately not the create_user service: that one asks
        # may_change_email, and this command is the one route that must work when
        # nobody holds a role to answer it with. No Colleague either; the
        # link_colleague_on_login signal links or creates one at first login.
        user = User.objects.create_user(email=email, first_name=first_name, last_name=last_name)
        logger.info("Created initial user: %s", email)
        return user

    def _grant_every_role(self, user) -> list[str]:
        """Gives the user every role and returns the keys that were not held yet."""
        groups = list(Group.objects.all())
        held = set(user.groups.values_list("name", flat=True))
        granted = sorted(group.name for group in groups if group.name not in held)
        if granted:
            user.groups.add(*groups)
            logger.info("Granted %s to initial user %s", ", ".join(granted), user.email)
        return granted

    def _record(self, user, *, created: bool, granted: list[str]):
        """One audit event per actual change, none for a start that changed nothing.

        No actor: the deploy did this, so the event names the variable instead of
        a person. User events are audit-only and never rendered (``docs/beheer.md``).
        """
        create_event(
            object_type="User",
            action="create" if created else "update",
            source="system",
            object_id=user.id,
            context={
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "group_names": [role_label(name) for name in granted],
                "granted_via": "INITIAL_USER_EMAIL",
            },
        )
