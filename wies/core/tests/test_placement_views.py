from unittest.mock import patch

from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import User


@override_settings(
    # Use simple static files storage for tests
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class PlacementImportTest(TestCase):
    """Tests for CSV placement import view functionality"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.import_url = reverse("placement-import-csv")

        # Get or create test groups (migration may have created them)
        self.admin_group, _ = Group.objects.get_or_create(name="Beheerder")
        self.consultant_group, _ = Group.objects.get_or_create(name="Consultant")
        self.bdm_group, _ = Group.objects.get_or_create(name="Business Development Manager")

        # Create authenticated user with all required permissions
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )
        add_assignment_perm = Permission.objects.get(codename="add_assignment")
        add_service_perm = Permission.objects.get(codename="add_service")
        add_placement_perm = Permission.objects.get(codename="add_placement")
        add_colleague_perm = Permission.objects.get(codename="add_colleague")
        self.auth_user.user_permissions.add(
            add_assignment_perm, add_service_perm, add_placement_perm, add_colleague_perm
        )

        # Create user without permissions
        self.no_perm_user = User.objects.create(
            username="nopermuser",
            email="noperm@example.com",
            first_name="No",
            last_name="Permission",
        )

        # Create user with only some permissions (missing add_service)
        self.partial_perm_user = User.objects.create(
            username="partialuser",
            email="partial@example.com",
            first_name="Partial",
            last_name="Permission",
        )
        self.partial_perm_user.user_permissions.add(add_assignment_perm, add_placement_perm, add_colleague_perm)

    def _create_csv_file(self, content):
        """Helper to create a CSV file upload"""
        return SimpleUploadedFile("placements.csv", content.encode("utf-8"), content_type="text/csv")

    def test_import_requires_login(self):
        """Test that import endpoint requires authentication"""
        response = self.client.get(self.import_url)
        assert response.status_code == 302
        assert response.url.startswith("/inloggen/")

    def test_import_requires_all_permissions(self):
        """Test that import requires all five add permissions (assignment, service, placement, colleague, ministry)"""
        # Test with no permissions
        self.client.force_login(self.no_perm_user)
        response = self.client.get(self.import_url)
        assert response.status_code == 403

        # Test with partial permissions
        self.client.force_login(self.partial_perm_user)
        response = self.client.get(self.import_url)
        assert response.status_code == 403

    def test_import_get_returns_form(self):
        """Test that GET request returns the import form"""
        self.client.force_login(self.auth_user)
        response = self.client.get(self.import_url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Plaatsingen" in content
        assert "csv_file" in content
        assert "example_placement_import.csv" in content

    def test_import_requires_file_upload(self):
        """Test that import requires a file to be uploaded"""
        self.client.force_login(self.auth_user)
        response = self.client.post(self.import_url, {})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Geen bestand geüpload" in content

    def test_import_validates_csv_file_type(self):
        """Test that import validates file is a CSV"""
        self.client.force_login(self.auth_user)
        txt_file = SimpleUploadedFile("placements.txt", b"not a csv", content_type="text/plain")

        response = self.client.post(self.import_url, {"csv_file": txt_file})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Ongeldig bestandstype" in content

    @patch("wies.core.views.create_placements_from_csv")
    def test_import_successful_result_display(self, mock_create_placements):
        """Test that successful import displays correct result information"""
        # Mock the service function to return success
        mock_create_placements.return_value = {
            "success": True,
            "colleagues_created": 2,
            "assignments_created": 1,
            "services_created": 3,
            "skills_created": 2,
            "placements_created": 3,
            "errors": ["Warning: Some optional data was missing"],
        }

        self.client.force_login(self.auth_user)
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization,assignment_ministry,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Test Description,John Owner,john@example.com,Test Org,BZK,01-01-2024,31-12-2024,Python,Jane Colleague,jane@example.com"""
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()

        # Check success message
        assert "Import geslaagd" in content

        # Check all counts are displayed
        assert "3" in content  # placements_created
        assert "2" in content  # colleagues_created
        assert "1" in content  # assignments_created

        # Check warnings are displayed
        assert "Waarschuwingen" in content
        assert "Warning: Some optional data was missing" in content

        # Verify the service function was called with CSV content
        mock_create_placements.assert_called_once()
        call_args = mock_create_placements.call_args[0][0]
        assert "Test Assignment" in call_args

    @patch("wies.core.views.create_placements_from_csv")
    def test_import_error_result_display(self, mock_create_placements):
        """Test that failed import displays error messages properly"""
        # Mock the service function to return failure
        mock_create_placements.return_value = {
            "success": False,
            "colleagues_created": 0,
            "assignments_created": 0,
            "services_created": 0,
            "skills_created": 0,
            "placements_created": 0,
            "errors": [
                "Missing required column: assignment_name",
                "Invalid email format in row 2",
            ],
        }

        self.client.force_login(self.auth_user)
        csv_content = "invalid,csv,format"
        csv_file = self._create_csv_file(csv_content)

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        content = response.content.decode()

        # Check error message
        assert "Import mislukt" in content

        # Check both error messages are displayed
        assert "Missing required column: assignment_name" in content
        assert "Invalid email format in row 2" in content

        # Verify the service function was called
        mock_create_placements.assert_called_once()
