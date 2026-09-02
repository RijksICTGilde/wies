"""Give dummy colleagues a user account and a role, so roles are represented in
the demo data.

The fixture (base_dummy_data.json) now ships a user per colleague, so a plain
fixture load already yields the role spread this command produces — including on
environments that only run `loaddata`, such as a PR preview seeded through
/staff/. The Bezetting page lists Consultants only, and would be empty without
those users.

This command remains for colleagues that arrive without one: rows imported from
OTYS, or a fixture loaded before the users were added. It skips anyone who
already has a user, so running it after a fixture load is a no-op rather than a
duplicate-email error.

Runs after ``setup`` (which seeds the role groups) and after the fixture load;
see the ``setup`` recipe in the justfile.

Usage:
    python manage.py assign_roles_to_colleagues
"""

import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from wies.core.models import Colleague

User = get_user_model()

# Roughly: most consultants, some BDMs, a few beheerders.
ROLE_WEIGHTS = [
    ("Consultant", 80),
    ("Business Development Manager", 15),
    ("Beheerder", 5),
]


class Command(BaseCommand):
    help = "Create a user and assign a role group to colleagues that have none"

    def handle(self, *args, **options):
        rng = random.Random(42)  # noqa: S311

        groups = {name: Group.objects.get(name=name) for name, _ in ROLE_WEIGHTS}
        names = [name for name, _ in ROLE_WEIGHTS]
        weights = [weight for _, weight in ROLE_WEIGHTS]

        colleagues = list(Colleague.objects.filter(user__isnull=True))
        if not colleagues:
            self.stdout.write("No colleagues without a user found")
            return

        counts = dict.fromkeys(names, 0)
        for colleague in colleagues:
            # Reuse the colleague's email; make it unique if it already exists.
            email = colleague.email
            if User.objects.filter(email__iexact=email).exists():
                email = f"{colleague.public_id}@rijksoverheid.nl"

            first_name, _, last_name = colleague.name.partition(" ")
            user = User.objects.create(email=email, first_name=first_name, last_name=last_name)
            colleague.user = user
            colleague.save(update_fields=["user"])

            role = rng.choices(names, weights=weights, k=1)[0]
            user.groups.add(groups[role])
            counts[role] += 1

        summary = ", ".join(f"{counts[name]} {name}" for name in names)
        self.stdout.write(f"Assigned roles to {len(colleagues)} colleagues: {summary}")
