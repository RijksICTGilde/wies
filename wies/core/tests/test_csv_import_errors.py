from django.contrib.auth.models import Group
from django.test import TestCase

from wies.core.services.placements import create_assignments_from_csv
from wies.core.services.users import create_users_from_csv

HEADERS = (
    "assignment_name,assignment_description,assignment_owner,assignment_owner_email,"
    "client_1_url,assignment_start_date,assignment_end_date,service_skill,"
    "placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand"
)


def _csv(colleague_name="John Doe"):
    row = (
        f"Test Assignment,Test Description,Owner Name,owner@rijksoverheid.nl,,"
        f"01-01-2025,31-12-2025,Python,{colleague_name},john@rijksoverheid.nl,,"
    )
    return HEADERS + "\n" + row


class CsvImportGracefulErrorTests(TestCase):
    """A malformed opdracht-CSV must produce a graceful error result, never an
    uncaught exception (which surfaces as a 500)."""

    def test_value_longer_than_the_column_returns_graceful_error(self):
        # Colleague.name is max_length=200; a longer value would raise a DataError
        # at the database instead of a handled error.
        result = create_assignments_from_csv(None, _csv(colleague_name="x" * 300))

        assert result["success"] is False
        assert result["errors"]

    def test_unparseable_csv_returns_graceful_error(self):
        result = create_assignments_from_csv(None, "not-a-csv-without-any-delimiter")

        assert result["success"] is False
        assert result["errors"]

    def test_valid_csv_still_imports(self):
        result = create_assignments_from_csv(None, _csv())

        assert result["success"] is True


USER_HEADERS = "first_name,last_name,email"


def _user_csv(first_name="John"):
    return USER_HEADERS + "\n" + f"{first_name},Doe,john@rijksoverheid.nl"


class UserCsvImportGracefulErrorTests(TestCase):
    """A malformed user-CSV must produce a graceful error result, never an
    uncaught exception (which surfaces as a 500)."""

    def setUp(self):
        Group.objects.create(name="Beheerder")
        Group.objects.create(name="Consultant")
        Group.objects.create(name="Business Development Manager")

    def test_value_longer_than_the_column_returns_graceful_error(self):
        # User.first_name is max_length=150; a longer value would raise a DataError
        # at the database instead of a handled error.
        result = create_users_from_csv(None, _user_csv(first_name="x" * 300))

        assert result["success"] is False
        assert result["errors"]

    def test_valid_csv_still_imports(self):
        result = create_users_from_csv(None, _user_csv())

        assert result["success"] is True
        assert result["users_created"] == 1
