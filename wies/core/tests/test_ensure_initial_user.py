from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from wies.core.models import Colleague, User
from wies.core.roles import setup_roles


class EnsureInitialUserTest(TestCase):
    def setUp(self):
        setup_roles()

    @patch.dict(
        "os.environ",
        {
            "INITIAL_USER_FIRSTNAME": "Admin",
            "INITIAL_USER_LASTNAME": "User",
            "INITIAL_USER_EMAIL": "admin@rijksoverheid.nl",
        },
    )
    def test_creates_user_with_all_groups(self):
        call_command("ensure_initial_user")
        user = User.objects.get(email="admin@rijksoverheid.nl")
        assert user.first_name == "Admin"
        assert user.last_name == "User"
        group_names = set(user.groups.values_list("name", flat=True))
        assert group_names == {"Beheerder", "Consultant", "Business Development Manager"}

    @patch.dict(
        "os.environ",
        {
            "INITIAL_USER_FIRSTNAME": "Admin",
            "INITIAL_USER_LASTNAME": "User",
            "INITIAL_USER_EMAIL": "admin@rijksoverheid.nl",
        },
    )
    def test_creates_colleague(self):
        call_command("ensure_initial_user")
        colleague = Colleague.objects.get(email="admin@rijksoverheid.nl")
        assert colleague.name == "Admin User"
        assert colleague.source == "wies"

    @patch.dict(
        "os.environ",
        {
            "INITIAL_USER_EMAIL": "admin@rijksoverheid.nl",
        },
        clear=True,
    )
    def test_creates_user_with_only_email(self):
        call_command("ensure_initial_user")
        user = User.objects.get(email="admin@rijksoverheid.nl")
        assert user.first_name == ""
        assert user.last_name == ""

    @patch.dict(
        "os.environ",
        {
            "INITIAL_USER_FIRSTNAME": "Admin",
            "INITIAL_USER_LASTNAME": "User",
            "INITIAL_USER_EMAIL": "admin@rijksoverheid.nl",
        },
    )
    def test_idempotent(self):
        call_command("ensure_initial_user")
        call_command("ensure_initial_user")
        assert User.objects.filter(email="admin@rijksoverheid.nl").count() == 1
        assert Colleague.objects.filter(email="admin@rijksoverheid.nl").count() == 1

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_email_no_error(self):
        call_command("ensure_initial_user")
        assert User.objects.count() == 0
