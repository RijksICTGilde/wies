"""Helpers for provisioning role-carrying users in tests.

Ownership only grants assignment edit rights combined with the BDM role, and
ended/future placements are visible to BDMs only — so most tests that exercise
an owner's rights or restricted-visibility rows need a BDM user. One helper
instead of a hand-rolled group block per test class, so a change in how the
role is provisioned lands in one place.
"""

from django.contrib.auth.models import Group

from wies.core.roles import BDM_GROUP_NAME


def grant_bdm(user):
    """Puts ``user`` in the BDM group (creating the group on first use)."""
    group, _created = Group.objects.get_or_create(name=BDM_GROUP_NAME)
    user.groups.add(group)
    return user


def make_bdm_user(email="bdm@rijksoverheid.nl", name="Bdm"):
    """A BDM user with a linked colleague, ready for ``force_login``."""
    # Local imports: keep the helper importable before Django app setup.
    from wies.core.models import Colleague  # noqa: PLC0415 (import not at top level) — see above
    from wies.rijksauth.models import User  # noqa: PLC0415 (import not at top level) — see above

    user = User.objects.create_user(email=email)
    Colleague.objects.create(name=name, email=email, source="wies", user=user)
    return grant_bdm(user)
