"""Dev-only helper: put a user in the BDM group and grant them
change_assignment + change_colleague. Handy for exercising inline-edit
flows locally.

Usage::

    python manage.py grant_dev_permissions --email you@rijksoverheid.nl
    # or, if INITIAL_USER_EMAIL is set:
    python manage.py grant_dev_permissions
"""

import logging
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

User = get_user_model()


BDM_GROUP = "Business Development Manager"
GRANTED_PERMISSIONS = ["change_assignment", "change_colleague"]


class Command(BaseCommand):
    help = (
        "Grant dev permissions to a user: add to the Business Development "
        "Manager group and grant change_assignment + change_colleague."
    )

    def add_arguments(self, parser):
        """Declare the ``--email`` option (defaults to
        ``$INITIAL_USER_EMAIL``). No positional arguments are accepted.
        """
        parser.add_argument(
            "--email",
            default=os.environ.get("INITIAL_USER_EMAIL", ""),
            help="User email (falls back to $INITIAL_USER_EMAIL).",
        )

    def handle(self, *args, **options):
        """Look up the user by email, ensure the BDM group exists and
        assign it, then attach the listed change-permissions.

        Idempotent — repeated runs are no-ops. Writes a stderr line
        when the user or a permission can't be found, but does not
        abort; missing permissions are skipped individually.
        """
        email = options["email"]
        if not email:
            self.stderr.write("No email provided and INITIAL_USER_EMAIL is unset.")
            return

        user = User.objects.filter(email=email).first()
        if user is None:
            self.stderr.write(f"User {email} not found.")
            return

        bdm_group, _ = Group.objects.get_or_create(name=BDM_GROUP)
        user.groups.add(bdm_group)

        for codename in GRANTED_PERMISSIONS:
            perm = Permission.objects.filter(codename=codename).first()
            if perm is None:
                self.stderr.write(f"Permission '{codename}' not found.")
                continue
            user.user_permissions.add(perm)

        self.stdout.write(f"Granted BDM group + {GRANTED_PERMISSIONS} to {email}.")
