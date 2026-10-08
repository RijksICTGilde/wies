"""Tests for ``ensure_initial_user``, the way into an environment and back in.

The command runs on every container start. While ``INITIAL_USER_EMAIL`` is set it
puts every role back on that account, which is what makes it a recovery and not
only a bootstrap: an environment whose last Gebruikersbeheerder is gone has no
other route, because the user sheet asks for the very role that is missing.
Removing the variable after the deploy is what ends it. See ``features/roles.md``.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from wies.core.models import Event
from wies.core.roles import ROLE_USER_ADMIN, role_label, setup_roles

User = get_user_model()

EMAIL = "admin@rijksoverheid.nl"
FULL_ENV = {
    "INITIAL_USER_FIRSTNAME": "Admin",
    "INITIAL_USER_LASTNAME": "User",
    "INITIAL_USER_EMAIL": EMAIL,
}


class EnsureInitialUserTest(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name="Admins")
        Group.objects.get_or_create(name="Editors")

    def _roles(self, user):
        return set(user.groups.values_list("name", flat=True))

    @patch.dict("os.environ", FULL_ENV)
    def test_creates_user_with_all_groups(self):
        call_command("ensure_initial_user")

        user = User.objects.get(email=EMAIL)
        assert user.first_name == "Admin"
        assert user.last_name == "User"
        # Every group, including any a data migration created.
        assert {"Admins", "Editors"} <= self._roles(user)
        assert self._roles(user) == set(Group.objects.values_list("name", flat=True))

    @patch.dict("os.environ", {"INITIAL_USER_EMAIL": EMAIL}, clear=True)
    def test_creates_user_with_only_email(self):
        """Only the address is required; the two name variables just fill it in."""
        call_command("ensure_initial_user")

        user = User.objects.get(email=EMAIL)
        assert user.first_name == ""
        assert user.last_name == ""

    @patch.dict("os.environ", FULL_ENV)
    def test_runs_twice_without_a_second_account(self):
        call_command("ensure_initial_user")
        call_command("ensure_initial_user")

        assert User.objects.filter(email=EMAIL).count() == 1

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_email_no_error(self):
        call_command("ensure_initial_user")

        assert User.objects.count() == 0


class RestoresTheRolesTest(TestCase):
    """The half that makes this a way back in: an account that already exists."""

    def setUp(self):
        # A class decorator would not reach setUp, and the bootstrap belongs here.
        self.enterContext(patch.dict("os.environ", FULL_ENV))
        setup_roles()
        call_command("ensure_initial_user")
        self.user = User.objects.get(email=EMAIL)
        Event.objects.all().delete()

    def _roles(self, user):
        return set(user.groups.values_list("name", flat=True))

    def test_a_revoked_role_comes_back_on_the_next_start(self):
        """The lockout this exists for: the last Gebruikersbeheerder takes their own
        role off, and from then on nobody can reach the user sheet to put it back."""
        self.user.groups.remove(Group.objects.get(name=ROLE_USER_ADMIN))
        assert not User.objects.filter(groups__name=ROLE_USER_ADMIN).exists()

        call_command("ensure_initial_user")

        assert ROLE_USER_ADMIN in self._roles(self.user)
        assert self._roles(self.user) == set(Group.objects.values_list("name", flat=True))

    def test_an_account_that_predates_the_variable_is_adopted(self):
        """Pointing the variable at somebody who already has an account used to do
        nothing, which is why repointing it was no way out of the lockout."""
        zittend = User.objects.create_user(email="zittend@rijksoverheid.nl", first_name="Z", last_name="C")
        with patch.dict("os.environ", {"INITIAL_USER_EMAIL": "zittend@rijksoverheid.nl"}):
            call_command("ensure_initial_user")

        assert self._roles(zittend) == set(Group.objects.values_list("name", flat=True))
        assert User.objects.filter(email__iexact="zittend@rijksoverheid.nl").count() == 1

    def test_the_address_is_matched_whatever_its_case(self):
        with patch.dict("os.environ", {"INITIAL_USER_EMAIL": EMAIL.upper()}):
            call_command("ensure_initial_user")

        assert User.objects.filter(email__iexact=EMAIL).count() == 1


class AuditTrailTest(TestCase):
    """Granting authority from a deploy leaves the same trail as granting it on the
    sheet, or the one route that works without a role would be the one route that
    is invisible (``docs/beheer.md``)."""

    def setUp(self):
        self.enterContext(patch.dict("os.environ", FULL_ENV))
        setup_roles()

    def _events(self):
        return list(Event.objects.values("object_type", "action", "source", "object_id", "user_id", "context"))

    def test_creating_the_account_is_recorded(self):
        call_command("ensure_initial_user")

        user = User.objects.get(email=EMAIL)
        (event,) = self._events()
        assert (event["object_type"], event["action"], event["source"]) == ("User", "create", "system")
        assert event["object_id"] == user.id
        # No actor: the deploy did it, so the event names the variable instead.
        assert event["user_id"] is None
        assert event["context"]["granted_via"] == "INITIAL_USER_EMAIL"
        assert event["context"]["email"] == EMAIL

    def test_restoring_a_role_is_recorded_as_an_update_naming_that_role(self):
        call_command("ensure_initial_user")
        user = User.objects.get(email=EMAIL)
        user.groups.remove(Group.objects.get(name=ROLE_USER_ADMIN))
        Event.objects.all().delete()

        call_command("ensure_initial_user")

        (event,) = self._events()
        assert (event["action"], event["source"]) == ("update", "system")
        # The label, as the sheet records it, and only what was actually added.
        assert event["context"]["group_names"] == [role_label(ROLE_USER_ADMIN)]

    def test_a_forgotten_variable_is_visible_in_the_log(self):
        """Removing the variable after the deploy is a process step with nothing
        enforcing it, so the one start that notices says so (``features/roles.md``)."""
        call_command("ensure_initial_user")

        with self.assertLogs("wies.rijksauth.management.commands.ensure_initial_user", "WARNING") as logged:
            call_command("ensure_initial_user")

        assert any("still set" in line and EMAIL in line for line in logged.output), logged.output

    def test_a_start_that_changes_nothing_records_nothing(self):
        """Otherwise every deploy writes an event saying the state is unchanged, and
        the trail stops being readable."""
        call_command("ensure_initial_user")
        Event.objects.all().delete()

        call_command("ensure_initial_user")
        call_command("ensure_initial_user")

        assert self._events() == []
