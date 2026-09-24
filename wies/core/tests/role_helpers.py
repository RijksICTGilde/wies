"""Helpers for provisioning role-carrying users in tests.

Ownership only grants assignment edit rights combined with the BDM role, and
ended/future placements are visible to privileged viewers only (the BDM role or
Opdrachtbeheer), so most tests that exercise an owner's rights or
restricted-visibility rows need a BDM or Opdrachtbeheer user. One helper instead of a
hand-rolled group block per test class, so a change in how the role is
provisioned lands in one place.
"""

from django.contrib.auth.models import Group

from wies.core.roles import ROLE_ASSIGNMENT_ADMIN, ROLE_BDM, ROLE_CONSULTANT

# Application administration is email-based (``settings.STAFF_EMAILS``), not
# a group. A test using ``make_staff_user`` must also apply
# ``@override_settings(STAFF_EMAILS=[STAFF_EMAIL])`` so the email actually counts.
STAFF_EMAIL = "staff@rijksoverheid.nl"


def grant_bdm(user):
    """Puts ``user`` in the BDM group (creating the group on first use)."""
    group, _created = Group.objects.get_or_create(name=ROLE_BDM)
    user.groups.add(group)
    return user


def grant_consultant(user):
    """Puts ``user`` in the Consultant group (creating the group on first use)."""
    group, _created = Group.objects.get_or_create(name=ROLE_CONSULTANT)
    user.groups.add(group)
    return user


def grant_assignment_admin(user):
    """Puts ``user`` in the Opdrachtbeheer group (creating the group on first use)."""
    group, _created = Group.objects.get_or_create(name=ROLE_ASSIGNMENT_ADMIN)
    user.groups.add(group)
    return user


def make_assignment_admin_user(email="opdrachtbeheer@rijksoverheid.nl", name="Opdrachtbeheer"):
    """An Opdrachtbeheer user with a linked colleague, ready for ``force_login``."""
    from wies.core.models import Colleague  # noqa: PLC0415 (import not at top level), see make_bdm_user
    from wies.rijksauth.models import User  # noqa: PLC0415 (import not at top level), see make_bdm_user

    user = User.objects.create_user(email=email)
    Colleague.objects.create(name=name, email=email, source="wies", user=user)
    return grant_assignment_admin(user)


def make_bdm_user(email="bdm@rijksoverheid.nl", name="Bdm"):
    """A BDM user with a linked colleague, ready for ``force_login``."""
    # Local imports: keep the helper importable before Django app setup.
    from wies.core.models import Colleague  # noqa: PLC0415 (import not at top level) — see above
    from wies.rijksauth.models import User  # noqa: PLC0415 (import not at top level) — see above

    user = User.objects.create_user(email=email)
    Colleague.objects.create(name=name, email=email, source="wies", user=user)
    return grant_bdm(user)


def make_staff_user(email=STAFF_EMAIL, name="Staff"):
    """An application-administration user with a linked colleague, ready for ``force_login``.

    Needs ``@override_settings(STAFF_EMAILS=[email])`` as well, see the note
    at ``STAFF_EMAIL``.
    """
    from wies.core.models import Colleague  # noqa: PLC0415 (import not at top level) — see above
    from wies.rijksauth.models import User  # noqa: PLC0415 (import not at top level) — see above

    user = User.objects.create_user(email=email)
    Colleague.objects.create(name=name, email=email, source="wies", user=user)
    return user
