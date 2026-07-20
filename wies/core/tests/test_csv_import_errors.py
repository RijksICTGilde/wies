from django.test import TestCase

from wies.core.services.placements import create_assignments_from_csv

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
