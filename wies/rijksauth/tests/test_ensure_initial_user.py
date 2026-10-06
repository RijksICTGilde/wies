from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

User = get_user_model()


class EnsureInitialUserTest(TestCase):
    def setUp(self):
        Group.objects.create(name="Admins")
        Group.objects.create(name="Editors")

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
        assert group_names == {"Admins", "Editors"}

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

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_email_no_error(self):
        call_command("ensure_initial_user")
        assert User.objects.count() == 0
