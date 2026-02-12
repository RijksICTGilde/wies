import datetime
from pathlib import Path

import pytest
from django.test import TestCase

from wies.core.models import Assignment, Colleague, OrganizationUnit, Placement, Service, Skill
from wies.core.services.placements import create_assignments_from_csv, parse_date_dmy


class ParseDateDmyTest(TestCase):
    """Tests for parse_date_dmy helper function"""

    def test_valid_date(self):
        """Test parsing a valid DD-MM-YYYY date"""
        result = parse_date_dmy("15-03-2025")
        assert result == datetime.date(2025, 3, 15)

    def test_single_digit_day_month(self):
        """Test parsing date with single digit day and month"""
        result = parse_date_dmy("1-2-2025")
        assert result == datetime.date(2025, 2, 1)

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError"""
        with pytest.raises(ValueError, match=r"not enough values to unpack"):
            parse_date_dmy("15-03")  # Missing year

    def test_invalid_date_raises_error(self):
        """Test that invalid date raises ValueError"""
        with pytest.raises(ValueError, match=r"day is out of range"):
            parse_date_dmy("31-02-2025")  # February 31st doesn't exist


class CreateFromCSVTest(TestCase):
    def test_sample_csv_success(self):
        sample_csv_path = Path(__file__).parent.parent / "static" / "example_assignment_import.csv"
        with sample_csv_path.open() as f:
            csv_content = f.read()

        result = create_assignments_from_csv(csv_content)
        assert result["success"]

    # Critical Bug Exposure Tests
    def test_invalid_date_format(self):
        """Test that invalid date format causes ValueError"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Description,Owner Name,owner@rijksoverheid.nl,,2025-01-01,28-02-2025,Python,John Doe,john@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert not result["success"]
        assert len(result["errors"]) > 0
        # Verify the error message mentions a date-related issue
        error_message = result["errors"][0].lower()
        assert (
            "time data" in error_message
            or "format" in error_message
            or "match" in error_message
            or "day is out of range" in error_message
        )

    # Core Validation Tests
    def test_missing_required_columns(self):
        """Test that missing required columns returns error"""
        csv_content = """assignment_name,assignment_description,placement_colleague_name
Test,Description,John Doe"""

        result = create_assignments_from_csv(csv_content)
        assert not result["success"]
        assert len(result["errors"]) > 0
        assert "CSV mist kolommen:" in result["errors"][0]

    def test_empty_csv_no_data_rows(self):
        """Test that CSV with only headers succeeds with zero creates"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]
        assert result["assignments_created"] == 0
        assert result["services_created"] == 0
        assert result["placements_created"] == 0

    def test_invalid_email_format(self):
        """Test that invalid email format fails on model validation"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,John,invalid-email-no-at,,"""

        result = create_assignments_from_csv(csv_content)
        assert not result["success"]
        assert len(result["errors"]) > 0

    def test_empty_organization_abbreviation(self):
        """Test that empty organization_abbreviation is handled correctly"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,John,john@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]
        assert result["organizations_linked"] == 0

    # Business Logic Tests
    def test_multiple_services_per_assignment(self):
        """Test that multiple rows with same assignment name create multiple services"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Same Assignment,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,John,john@rijksoverheid.nl,,
Same Assignment,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Java,Jane,jane@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]
        assert result["assignments_created"] == 1  # Only one assignment
        assert result["services_created"] == 2  # But two services
        assert result["placements_created"] == 2

    def test_colleague_email_reuse(self):
        """Test that same colleague email across rows reuses the Colleague object"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Assignment 1,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,John Doe,john@rijksoverheid.nl,,
Assignment 2,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Java,John Doe,john@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]
        # Should only create one colleague even though email appears twice
        colleague_count = Colleague.objects.filter(email="john@rijksoverheid.nl").count()
        assert colleague_count == 1

    def test_assignment_name_reuse(self):
        """Test that same assignment name reuses assignment but creates new services"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Shared Assignment,First description,Owner A,ownerA@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,John,john@rijksoverheid.nl,,
Shared Assignment,Different description,Owner B,ownerB@rijksoverheid.nl,,01-03-2025,30-04-2025,Java,Jane,jane@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]
        assert result["assignments_created"] == 1
        # Verify that first version of assignment details are kept
        assignment = Assignment.objects.get(name="Shared Assignment", source="wies")
        assert assignment.extra_info == "First description"
        assert assignment.owner.email == "ownerA@rijksoverheid.nl"

    def test_owner_equals_placement_colleague(self):
        """Test that same email for owner and colleague creates one Colleague for both roles"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Description,John Doe,john@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,John Doe,john@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]
        # Should only create one colleague
        colleague_count = Colleague.objects.filter(email="john@rijksoverheid.nl").count()
        assert colleague_count == 1
        # Assignment owner and placement colleague should be the same object
        assignment = Assignment.objects.get(name="Test Assignment", source="wies")
        placement = Placement.objects.get(service__assignment=assignment)
        assert assignment.owner == placement.colleague

    # Edge Case Tests
    def test_empty_optional_fields(self):
        """Test that empty optional fields (owner email, organization_abbreviation, dates, skill) are handled as None"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Description,Owner Name,,,,,,John Doe,john@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]
        assignment = Assignment.objects.get(name="Test Assignment", source="wies")
        assert assignment.owner is None
        assert assignment.start_date is None
        assert assignment.end_date is None

    def test_skill_case_and_whitespace_sensitivity(self):
        """Test that skills with different case/whitespace create different Skill objects"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Assignment 1,Description,Owner,owner@rijksoverheid.nl,,,,Python,John,john@rijksoverheid.nl,,
Assignment 2,Description,Owner,owner@rijksoverheid.nl,,,, Python ,Jane,jane@rijksoverheid.nl,,
Assignment 3,Description,Owner,owner@rijksoverheid.nl,,,,python,Bob,bob@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]
        # Should create 3 different skills due to case/whitespace differences
        python_skills = Skill.objects.filter(name__icontains="python").count()
        assert python_skills == 3

    def test_date_validation_start_after_end(self):
        """Test that dates where start is after end are not validated (business logic issue)"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Description,Owner,owner@rijksoverheid.nl,,31-12-2025,01-01-2025,Python,John,john@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        # Currently no validation - this should succeed but creates invalid data
        assert result["success"]
        assignment = Assignment.objects.get(name="Test Assignment", source="wies")
        # Start date is after end date - this is a business logic bug
        assert assignment.start_date > assignment.end_date

    # Data Integrity Tests
    def test_verify_return_counts_match_database(self):
        """Test that returned counts match actual objects created in database"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Assignment 1,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,John,john@rijksoverheid.nl,,
Assignment 2,Description,Owner,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Java,Jane,jane@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]

        # Verify counts in result match database
        assignments_in_db = Assignment.objects.filter(source="wies").count()
        services_in_db = Service.objects.filter(source="wies").count()
        placements_in_db = Placement.objects.filter(source="wies").count()

        assert result["assignments_created"] == assignments_in_db
        assert result["services_created"] == services_in_db
        assert result["placements_created"] == placements_in_db

    def test_verify_relationships_established(self):
        """Test that all relationships between objects are correctly established"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Description,Owner Name,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Python Developer,John Doe,john@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]

        # Verify Assignment -> Owner relationship
        assignment = Assignment.objects.get(name="Test Assignment", source="wies")
        assert assignment.owner is not None
        assert assignment.owner.email == "owner@rijksoverheid.nl"

        # Verify Service -> Assignment relationship
        service = Service.objects.get(assignment=assignment)
        assert service.assignment == assignment

        # Verify Service -> Skill relationship
        assert service.skill is not None
        assert service.skill.name == "Python Developer"

        # Verify Placement -> Service relationship
        placement = Placement.objects.get(service=service)
        assert placement.service == service

        # Verify Placement -> Colleague relationship
        assert placement.colleague is not None
        assert placement.colleague.email == "john@rijksoverheid.nl"

    def test_assignment_status_is_ingevuld(self):
        """Test that assignments created from CSV have status INGEVULD since they have placements"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment,Description,Owner Name,owner@rijksoverheid.nl,,01-01-2025,28-02-2025,Python,John Doe,john@rijksoverheid.nl,,"""

        result = create_assignments_from_csv(csv_content)
        assert result["success"]

        assignment = Assignment.objects.get(name="Test Assignment", source="wies")
        assert assignment.status == "INGEVULD"

    def test_organization_abbreviation_case_insensitive(self):
        """Test that organization abbreviation matching is case-insensitive"""

        # Create a test organization with abbreviation "BZK"
        org = OrganizationUnit.objects.create(
            name="Test Ministry",
            abbreviations=["BZK"],
            tooi_identifier="https://identifier.overheid.nl/tooi/id/test/12345",
        )

        # Test with lowercase
        csv_content_lower = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment 1,Description,Owner,owner@test.nl,bzk,01-01-2025,28-02-2025,Python,John,john@test.nl,,"""

        result = create_assignments_from_csv(csv_content_lower)
        assert result["success"]
        assert result["organizations_linked"] == 1

        assignment = Assignment.objects.get(name="Test Assignment 1", source="wies")
        assert org in assignment.organizations.all()

        # Test with mixed case
        csv_content_mixed = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_abbreviation,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email,owner_brand,colleague_brand
Test Assignment 2,Description,Owner,owner@test.nl,Bzk,01-01-2025,28-02-2025,Java,Jane,jane@test.nl,,"""

        result = create_assignments_from_csv(csv_content_mixed)
        assert result["success"]
        assert result["organizations_linked"] == 1

        assignment2 = Assignment.objects.get(name="Test Assignment 2", source="wies")
        assert org in assignment2.organizations.all()
