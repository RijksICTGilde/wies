"""
Tests covering case-insensitive email handling across the codebase.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.auth.signals import user_logged_in
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase

from wies.core.models import Colleague
from wies.core.services.placements import create_assignments_from_csv
from wies.core.services.users import create_users_from_csv
from wies.rijksauth.auth_backend import AuthBackend
from wies.rijksauth.middleware import AutoLoginMiddleware

User = get_user_model()


class AuthBackendCaseInsensitiveTest(TestCase):
    """auth_backend.authenticate must find a User regardless of email case."""

    def test_authenticate_finds_user_with_different_case(self):
        existing = User.objects.create_user(email="John.Doe@rijksoverheid.nl", first_name="John", last_name="Doe")

        result = AuthBackend().authenticate(request=None, username="sub-123", email="JOHN.DOE@RIJKSOVERHEID.NL")

        assert result == existing

    def test_authenticate_unknown_user_returns_none(self):
        result = AuthBackend().authenticate(request=None, username="sub-123", email="missing@rijksoverheid.nl")
        assert result is None


class LoginSignalCaseInsensitiveTest(TestCase):
    """Login signal must reuse an existing Colleague when only email casing differs."""

    def test_signal_reuses_colleague_with_different_case(self):
        # Pre-existing Colleague (lowercased email) and a User with mixed-case email.
        # Exercise the signal directly via user_logged_in.
        colleague = Colleague.objects.create(name="Existing", email="jane.doe@rijksoverheid.nl", source="wies")
        user = User.objects.create_user(email="Jane.Doe@rijksoverheid.nl", first_name="Jane", last_name="Doe")

        user_logged_in.send(sender=User, request=None, user=user)

        colleague.refresh_from_db()
        assert colleague.user == user
        # No duplicate Colleague was created
        assert Colleague.objects.filter(email__iexact="jane.doe@rijksoverheid.nl").count() == 1


class PlacementCSVCaseInsensitiveTest(TestCase):
    """CSV placement import reuses existing colleagues when emails differ only in case."""

    HEADER = (
        "assignment_name,assignment_description,assignment_owner,assignment_owner_email,"
        "client_1_url,assignment_start_date,assignment_end_date,service_skill,"
        "placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand"
    )

    def test_reuses_owner_with_different_case(self):
        Colleague.objects.create(name="Existing Owner", email="owner@rijksoverheid.nl", source="wies")

        csv_content = (
            f"{self.HEADER}\n"
            "Test Assignment,Description,Owner,OWNER@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,"
            "John,john@rijksoverheid.nl,,"
        )
        result = create_assignments_from_csv(None, csv_content)

        assert result["success"]
        assert Colleague.objects.filter(email__iexact="owner@rijksoverheid.nl").count() == 1

    def test_reuses_placement_colleague_with_different_case(self):
        Colleague.objects.create(name="Existing John", email="john@rijksoverheid.nl", source="wies")

        csv_content = (
            f"{self.HEADER}\n"
            "Test Assignment,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,"
            "John,JOHN@RIJKSOVERHEID.NL,,"
        )
        result = create_assignments_from_csv(None, csv_content)

        assert result["success"]
        assert Colleague.objects.filter(email__iexact="john@rijksoverheid.nl").count() == 1


class UserCSVCaseInsensitiveDuplicateTest(TestCase):
    """CSV user import detects intra-file duplicates that differ only in case."""

    def setUp(self):
        Group.objects.get_or_create(name="Beheerder")
        Group.objects.get_or_create(name="Consultant")
        Group.objects.get_or_create(name="Business Development Manager")

    def test_intra_file_case_different_duplicate_is_flagged(self):
        csv_content = (
            "first_name,last_name,email\n"
            "Jan,Jansen,jan.jansen@rijksoverheid.nl\n"
            "Jan,Jansen,Jan.Jansen@rijksoverheid.nl\n"
        )

        result = create_users_from_csv(None, csv_content)

        assert result["success"] is False
        assert any("duplicate email" in err for err in result["errors"])


class UserEmailCaseInsensitiveUniqueTest(TestCase):
    """The Lower(email) unique constraint on User rejects case-different duplicates."""

    def test_constraint_blocks_case_different_duplicate(self):
        User.objects.create_user(email="dup@rijksoverheid.nl", first_name="A", last_name="A")

        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="DUP@rijksoverheid.nl", first_name="B", last_name="B")


class AutoLoginMiddlewareCaseInsensitiveTest(TestCase):
    """AutoLoginMiddleware (dev) finds the configured INITIAL_USER_EMAIL regardless of case."""

    def test_finds_user_with_different_case(self):
        user = User.objects.create_user(email="dev@rijksoverheid.nl", first_name="Dev", last_name="User")

        def _get_response(request):
            return None

        middleware = AutoLoginMiddleware(_get_response)
        request = RequestFactory().get("/")

        # Patch login() so the test doesn't need session middleware.
        with (
            patch("wies.rijksauth.middleware.login") as mock_login,
            patch.dict("os.environ", {"INITIAL_USER_EMAIL": "DEV@RIJKSOVERHEID.NL"}),
        ):
            request.user = AnonymousUser()
            middleware(request)
            assert mock_login.called
            assert mock_login.call_args.args[1] == user
