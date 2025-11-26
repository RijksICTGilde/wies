from pathlib import Path

from django.test import TestCase, override_settings

from wies.core.models import Ministry, Assignment, Colleague, Service, Placement, Skill
from wies.core.services.placements import create_placements_from_csv

@override_settings(
    # Use simple static files storage for tests
    # Because tests are not running with debug True, you would otherise need to run
    # collectstatic before running the test
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class CreateFromCSVTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        Ministry.objects.create(name='Ministerie van Binnenlandse Zaken', abbreviation='BZK')

    def test_sample_csv_success(self):
        sample_csv_path = Path(__file__).parent.parent / 'static' / 'example_placement_import.csv'
        with open(sample_csv_path) as f:
            csv_content = f.read()

        result = create_placements_from_csv(csv_content)
        self.assertEqual(result['success'], True)

    # Critical Bug Exposure Tests
    def test_invalid_date_format(self):
        """Test that invalid date format causes ValueError"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Description,Owner Name,owner@test.com,Test Org,BZK,2025-01-01,28-02-2025,Python,John Doe,john@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertFalse(result['success'])
        self.assertGreater(len(result['errors']), 0)
        # Verify the error message mentions the date format issue
        error_message = result['errors'][0].lower()
        self.assertTrue('time data' in error_message or 'format' in error_message or 'match' in error_message)

    # Core Validation Tests
    def test_missing_required_columns(self):
        """Test that missing required columns returns error"""
        csv_content = """assignment_name,assignment_description,placement_colleague_name
Test,Description,John Doe"""

        result = create_placements_from_csv(csv_content)
        self.assertFalse(result['success'])
        self.assertGreater(len(result['errors']), 0)
        self.assertIn('CSV misses columns:', result['errors'][0])

    def test_empty_csv_no_data_rows(self):
        """Test that CSV with only headers succeeds with zero creates"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])
        self.assertEqual(result['assignments_created'], 0)
        self.assertEqual(result['services_created'], 0)
        self.assertEqual(result['placements_created'], 0)

    def test_invalid_email_format(self):
        """Test that invalid email format fails on model validation"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Description,Owner,owner@test.com,Org,BZK,01-01-2025,28-02-2025,Python,John,invalid-email-no-at"""

        result = create_placements_from_csv(csv_content)
        self.assertFalse(result['success'])
        self.assertGreater(len(result['errors']), 0)

    def test_non_existent_ministry(self):
        """Test that non-existent ministry abbreviation fails"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Description,Owner,owner@test.com,Org,NONEXISTENT,01-01-2025,28-02-2025,Python,John,john@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertFalse(result['success'])
        self.assertGreater(len(result['errors']), 0)

    # Business Logic Tests
    def test_multiple_services_per_assignment(self):
        """Test that multiple rows with same assignment name create multiple services"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Same Assignment,Description,Owner,owner@test.com,Org,BZK,01-01-2025,28-02-2025,Python,John,john@test.com
Same Assignment,Description,Owner,owner@test.com,Org,BZK,01-01-2025,28-02-2025,Java,Jane,jane@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])
        self.assertEqual(result['assignments_created'], 1)  # Only one assignment
        self.assertEqual(result['services_created'], 2)  # But two services
        self.assertEqual(result['placements_created'], 2)

    def test_colleague_email_reuse(self):
        """Test that same colleague email across rows reuses the Colleague object"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Assignment 1,Description,Owner,owner@test.com,Org,BZK,01-01-2025,28-02-2025,Python,John Doe,john@test.com
Assignment 2,Description,Owner,owner@test.com,Org,BZK,01-01-2025,28-02-2025,Java,John Doe,john@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])
        # Should only create one colleague even though email appears twice
        colleague_count = Colleague.objects.filter(email='john@test.com').count()
        self.assertEqual(colleague_count, 1)

    def test_assignment_name_reuse(self):
        """Test that same assignment name reuses assignment but creates new services"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Shared Assignment,First description,Owner A,ownerA@test.com,Org A,BZK,01-01-2025,28-02-2025,Python,John,john@test.com
Shared Assignment,Different description,Owner B,ownerB@test.com,Org B,BZK,01-03-2025,30-04-2025,Java,Jane,jane@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])
        self.assertEqual(result['assignments_created'], 1)
        # Verify that first version of assignment details are kept
        assignment = Assignment.objects.get(name='Shared Assignment', source='wies')
        self.assertEqual(assignment.extra_info, 'First description')
        self.assertEqual(assignment.owner.email, 'ownerA@test.com')

    def test_owner_equals_placement_colleague(self):
        """Test that same email for owner and colleague creates one Colleague for both roles"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Description,John Doe,john@test.com,Org,BZK,01-01-2025,28-02-2025,Python,John Doe,john@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])
        # Should only create one colleague
        colleague_count = Colleague.objects.filter(email='john@test.com').count()
        self.assertEqual(colleague_count, 1)
        # Assignment owner and placement colleague should be the same object
        assignment = Assignment.objects.get(name='Test Assignment', source='wies')
        placement = Placement.objects.get(service__assignment=assignment)
        self.assertEqual(assignment.owner, placement.colleague)

    # Edge Case Tests
    def test_empty_optional_fields(self):
        """Test that empty optional fields (owner email, ministry, dates, skill) are handled as None"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Description,Owner Name,,Org,,,,,John Doe,john@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])
        assignment = Assignment.objects.get(name='Test Assignment', source='wies')
        self.assertIsNone(assignment.owner)
        self.assertIsNone(assignment.ministry)
        self.assertIsNone(assignment.start_date)
        self.assertIsNone(assignment.end_date)

    def test_skill_case_and_whitespace_sensitivity(self):
        """Test that skills with different case/whitespace create different Skill objects"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Assignment 1,Description,Owner,owner@test.com,Org,BZK,,,Python,John,john@test.com
Assignment 2,Description,Owner,owner@test.com,Org,BZK,,, Python ,Jane,jane@test.com
Assignment 3,Description,Owner,owner@test.com,Org,BZK,,,python,Bob,bob@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])
        # Should create 3 different skills due to case/whitespace differences
        python_skills = Skill.objects.filter(name__icontains='python').count()
        self.assertEqual(python_skills, 3)

    def test_date_validation_start_after_end(self):
        """Test that dates where start is after end are not validated (business logic issue)"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Description,Owner,owner@test.com,Org,BZK,31-12-2025,01-01-2025,Python,John,john@test.com"""

        result = create_placements_from_csv(csv_content)
        # Currently no validation - this should succeed but creates invalid data
        self.assertTrue(result['success'])
        assignment = Assignment.objects.get(name='Test Assignment', source='wies')
        # Start date is after end date - this is a business logic bug
        self.assertGreater(assignment.start_date, assignment.end_date)

    # Data Integrity Tests
    def test_verify_return_counts_match_database(self):
        """Test that returned counts match actual objects created in database"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Assignment 1,Description,Owner,owner@test.com,Org,BZK,01-01-2025,28-02-2025,Python,John,john@test.com
Assignment 2,Description,Owner,owner@test.com,Org,BZK,01-01-2025,28-02-2025,Java,Jane,jane@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])

        # Verify counts in result match database
        assignments_in_db = Assignment.objects.filter(source='wies').count()
        services_in_db = Service.objects.filter(source='wies').count()
        placements_in_db = Placement.objects.filter(source='wies').count()

        self.assertEqual(result['assignments_created'], assignments_in_db)
        self.assertEqual(result['services_created'], services_in_db)
        self.assertEqual(result['placements_created'], placements_in_db)

    def test_verify_relationships_established(self):
        """Test that all relationships between objects are correctly established"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Description,Owner Name,owner@test.com,Test Org,BZK,01-01-2025,28-02-2025,Python Developer,John Doe,john@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])

        # Verify Assignment -> Owner relationship
        assignment = Assignment.objects.get(name='Test Assignment', source='wies')
        self.assertIsNotNone(assignment.owner)
        self.assertEqual(assignment.owner.email, 'owner@test.com')

        # Verify Assignment -> Ministry relationship
        self.assertIsNotNone(assignment.ministry)
        self.assertEqual(assignment.ministry.abbreviation, 'BZK')

        # Verify Service -> Assignment relationship
        service = Service.objects.get(assignment=assignment)
        self.assertEqual(service.assignment, assignment)

        # Verify Service -> Skill relationship
        self.assertIsNotNone(service.skill)
        self.assertEqual(service.skill.name, 'Python Developer')

        # Verify Placement -> Service relationship
        placement = Placement.objects.get(service=service)
        self.assertEqual(placement.service, service)

        # Verify Placement -> Colleague relationship
        self.assertIsNotNone(placement.colleague)
        self.assertEqual(placement.colleague.email, 'john@test.com')

    def test_assignment_status_is_ingevuld(self):
        """Test that assignments created from CSV have status INGEVULD since they have placements"""
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Description,Owner Name,owner@test.com,Test Org,BZK,01-01-2025,28-02-2025,Python,John Doe,john@test.com"""

        result = create_placements_from_csv(csv_content)
        self.assertTrue(result['success'])

        assignment = Assignment.objects.get(name='Test Assignment', source='wies')
        self.assertEqual(assignment.status, 'INGEVULD')
