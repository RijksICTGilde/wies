from django.test import TestCase

from wies.core.models import Colleague
from wies.core.services.placements import create_assignments_from_csv

HEADERS = (
    "assignment_name,assignment_description,assignment_owner,assignment_owner_email,"
    "client_1_url,assignment_start_date,assignment_end_date,service_skill,"
    "placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand"
)


def _csv(*, owner_email="owner@rijksoverheid.nl", colleague_email="john@rijksoverheid.nl"):
    row = (
        f"Test Assignment,Test Description,Owner Name,{owner_email},,"
        f"01-01-2025,31-12-2025,Python,John Doe,{colleague_email},,"
    )
    return HEADERS + "\n" + row


class CsvImportDomainAllowlistTests(TestCase):
    """New colleagues minted from an opdracht CSV must have an allowed email
    domain, like every other colleague-creating path. Existing colleagues (e.g.
    from OTYS, with any domain) can still be referenced."""

    def test_minting_a_disallowed_domain_colleague_is_rejected(self):
        result = create_assignments_from_csv(None, _csv(colleague_email="john@test.com"))

        assert result["success"] is False
        assert result["errors"]
        assert not Colleague.objects.filter(email__iexact="john@test.com").exists()

    def test_minting_an_allowed_domain_colleague_still_works(self):
        result = create_assignments_from_csv(None, _csv(colleague_email="john@rijksoverheid.nl"))

        assert result["success"] is True
        assert Colleague.objects.filter(email__iexact="john@rijksoverheid.nl").exists()

    def test_existing_out_of_domain_colleague_is_still_referenced(self):
        Colleague.objects.create(name="Extern", email="extern@otys.example", source="otys_iir")

        result = create_assignments_from_csv(None, _csv(colleague_email="extern@otys.example"))

        assert result["success"] is True
        # No new colleague minted for that email; the existing one is reused.
        assert Colleague.objects.filter(email__iexact="extern@otys.example").count() == 1
