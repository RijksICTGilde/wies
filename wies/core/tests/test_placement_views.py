from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Placement, Service, Skill, User
from wies.core.views import PlacementListView


class PlacementImportTest(TestCase):
    """Tests for CSV placement import view functionality"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.import_url = reverse("assignment-import-csv")

        # Create test groups
        self.admin_group = Group.objects.create(name="Beheerder")
        self.consultant_group = Group.objects.create(name="Consultant")
        self.bdm_group = Group.objects.create(name="Business Development Manager")

        # Create authenticated user with all required permissions
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@rijksoverheid.nl",
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
            email="noperm@rijksoverheid.nl",
            first_name="No",
            last_name="Permission",
        )

        # Create user with only some permissions (missing add_service)
        self.partial_perm_user = User.objects.create(
            username="partialuser",
            email="partial@rijksoverheid.nl",
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
        """Test that import requires all four add permissions (assignment, service, placement, colleague)"""
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
        assert "example_assignment_import.csv" in content

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

    @patch("wies.core.views.create_assignments_from_csv")
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
        csv_content = """assignment_name,assignment_description,assignment_owner,assignment_owner_email,assignment_organization_tooi,assignment_start_date,assignment_end_date,service_skill,placement_colleague_name,placement_colleague_email
Test Assignment,Test Description,John Owner,john@rijksoverheid.nl,,01-01-2024,31-12-2024,Python,Jane Colleague,jane@rijksoverheid.nl"""
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

    @patch("wies.core.views.create_assignments_from_csv")
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


class PlacementListHistoricalFilterTest(TestCase):
    """Tests for historical placement filtering in PlacementListView"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.list_url = reverse("home")

        # Create authenticated user
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )

        # Create test ministry

        # Create test colleague
        self.colleague = Colleague.objects.create(
            name="Test Colleague",
            email="colleague@rijksoverheid.nl",
            source="wies",
        )

        # Create test skill
        self.skill = Skill.objects.create(name="Python Developer")

    def _create_placement_with_end_date(self, end_date):
        """Helper to create a placement with specific end date at placement level"""
        assignment = Assignment.objects.create(
            name=f"Test Assignment {end_date}",
            status="INGEVULD",
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Test Service",
            skill=self.skill,
            source="wies",
        )
        return Placement.objects.create(
            colleague=self.colleague,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=end_date,
            source="wies",
        )

    @patch("wies.core.views.timezone")
    def test_historical_placements_excluded(self, mock_timezone):
        """Test that placements ending before today are excluded from list"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create placement ending yesterday (2024-06-14)
        placement = self._create_placement_with_end_date(date(2024, 6, 14))

        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        qs = view.get_queryset()

        # Verify placement is NOT in queryset
        assert placement not in qs, "Historical placement should be excluded"

    @patch("wies.core.views.timezone")
    def test_current_placements_included(self, mock_timezone):
        """Test that placements ending today are included (boundary test)"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create placement ending today (2024-06-15)
        placement = self._create_placement_with_end_date(date(2024, 6, 15))

        # Get queryset from view directly
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        qs = view.get_queryset()

        # Verify placement IS in queryset
        assert placement in qs, "Placement ending today should be included"

    @patch("wies.core.views.timezone")
    def test_future_placements_included(self, mock_timezone):
        """Test that placements ending in the future are included"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create placement ending tomorrow (2024-06-16)
        placement = self._create_placement_with_end_date(date(2024, 6, 16))

        # Get queryset from view directly
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        qs = view.get_queryset()

        # Verify placement IS in queryset
        assert placement in qs, "Future placement should be included"

    @patch("wies.core.views.timezone")
    def test_hierarchical_date_inheritance_service_level(self, mock_timezone):
        """Test that filtering uses service dates when period_source='SERVICE'"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create assignment and service with service-specific dates
        assignment = Assignment.objects.create(
            name="Test Assignment Service Level",
            status="INGEVULD",
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Test Service",
            skill=self.skill,
            period_source="SERVICE",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),  # Ends yesterday
            source="wies",
        )
        placement = Placement.objects.create(
            colleague=self.colleague,
            service=service,
            period_source="SERVICE",  # Inherits from service
            source="wies",
        )

        # Get queryset from view directly
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        qs = view.get_queryset()

        # Verify placement is NOT in queryset (service ended yesterday)
        assert placement not in qs, "Placement with service ending yesterday should be excluded"

    @patch("wies.core.views.timezone")
    def test_hierarchical_date_inheritance_assignment_level(self, mock_timezone):
        """Test that filtering uses assignment dates when service uses period_source='ASSIGNMENT'"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create assignment with dates in the past
        assignment = Assignment.objects.create(
            name="Test Assignment Level",
            status="INGEVULD",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 14),  # Ends yesterday
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Test Service",
            skill=self.skill,
            period_source="ASSIGNMENT",  # Inherits from assignment
            source="wies",
        )
        placement = Placement.objects.create(
            colleague=self.colleague,
            service=service,
            period_source="SERVICE",  # Inherits from service, which inherits from assignment
            source="wies",
        )

        # Get queryset from view directly
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        qs = view.get_queryset()

        # Verify placement is NOT in queryset (assignment ended yesterday)
        assert placement not in qs, "Placement with assignment ending yesterday should be excluded"


class AssignmentSidePanelHistoricalFilterTest(TestCase):
    """Tests for historical placement filtering in assignment sidepanel"""

    def setUp(self):
        """Create test data"""
        self.list_url = reverse("home")

        # Create authenticated user
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )

        # Create test ministry

        # Create test colleagues
        self.colleague1 = Colleague.objects.create(
            name="Test Colleague 1",
            email="colleague1@rijksoverheid.nl",
            source="wies",
        )
        self.colleague2 = Colleague.objects.create(
            name="Test Colleague 2",
            email="colleague2@rijksoverheid.nl",
            source="wies",
        )

        # Create test skill
        self.skill = Skill.objects.create(name="Python Developer")

    @patch("wies.core.views.timezone")
    def test_assignment_panel_excludes_historical_placements(self, mock_timezone):
        """Test that assignment panel filters out placements ending before today"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create assignment
        assignment = Assignment.objects.create(
            name="Test Assignment with Mixed Placements",
            status="INGEVULD",
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Test Service",
            skill=self.skill,
            source="wies",
        )

        # Create historical placement (ended yesterday)
        historical_placement = Placement.objects.create(
            colleague=self.colleague1,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),  # Yesterday
            source="wies",
        )

        # Create current placement (ending tomorrow)
        current_placement = Placement.objects.create(
            colleague=self.colleague2,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),  # Tomorrow
            source="wies",
        )

        # Get panel data using view method
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        panel_data = view._get_assignment_panel_data(assignment, self.colleague1)  # noqa: SLF001 (private member access)

        # Verify only current placement is in panel data
        placement_ids = [p.id for p in panel_data["placements"]]
        assert len(placement_ids) == 1, "Panel should contain only 1 (current) placement"
        assert current_placement.id in placement_ids, "Current placement should be in panel"
        assert historical_placement.id not in placement_ids, "Historical placement should be excluded"

    @patch("wies.core.views.timezone")
    def test_assignment_panel_includes_current_placements(self, mock_timezone):
        """Test that assignment panel includes placements ending today (boundary test)"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create assignment
        assignment = Assignment.objects.create(
            name="Test Assignment with Current Placement",
            status="INGEVULD",
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Test Service",
            skill=self.skill,
            source="wies",
        )

        # Create placement ending today
        placement = Placement.objects.create(
            colleague=self.colleague1,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 15),  # Today
            source="wies",
        )

        # Get panel data using view method
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        panel_data = view._get_assignment_panel_data(assignment, self.colleague1)  # noqa: SLF001 (private member access)

        # Verify placement ending today is included
        placement_ids = [p.id for p in panel_data["placements"]]
        assert len(placement_ids) == 1, "Panel should contain the placement ending today"
        assert placement.id in placement_ids, "Placement ending today should be included"


class ColleagueSidePanelHistoricalFilterTest(TestCase):
    """Tests for historical placement filtering in colleague sidepanel"""

    def setUp(self):
        """Create test data"""
        self.list_url = reverse("home")

        # Create authenticated user
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )

        # Create test ministry

        # Create test colleague
        self.colleague = Colleague.objects.create(
            name="Test Colleague",
            email="colleague@rijksoverheid.nl",
            source="wies",
        )

        # Create test skill
        self.skill = Skill.objects.create(name="Python Developer")

    @patch("wies.core.views.timezone")
    def test_colleague_panel_excludes_historical_placements(self, mock_timezone):
        """Test that colleague panel filters out placements ending before today"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create assignment A with historical placement
        assignment_a = Assignment.objects.create(
            name="Test Assignment A (Historical)",
            status="INGEVULD",
            source="wies",
        )
        service_a = Service.objects.create(
            assignment=assignment_a,
            description="Test Service A",
            skill=self.skill,
            source="wies",
        )
        Placement.objects.create(  # historical_placement
            colleague=self.colleague,
            service=service_a,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),  # Yesterday
            source="wies",
        )

        # Create assignment B with current placement
        assignment_b = Assignment.objects.create(
            name="Test Assignment B (Current)",
            status="INGEVULD",
            source="wies",
        )
        service_b = Service.objects.create(
            assignment=assignment_b,
            description="Test Service B",
            skill=self.skill,
            source="wies",
        )
        Placement.objects.create(  # current_placement
            colleague=self.colleague,
            service=service_b,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),  # Tomorrow
            source="wies",
        )

        # Get panel data using view method
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        panel_data = view._get_colleague_panel_data(self.colleague)  # noqa: SLF001 (private member access)

        # Verify only current assignment is in panel data
        assignment_list = panel_data["assignment_list"]
        assignment_ids = [a["id"] for a in assignment_list]
        assert len(assignment_ids) == 1, "Panel should contain only 1 (current) assignment"
        assert assignment_b.id in assignment_ids, "Current assignment should be in panel"
        assert assignment_a.id not in assignment_ids, "Historical assignment should be excluded"

    @patch("wies.core.views.timezone")
    def test_colleague_panel_includes_current_placements(self, mock_timezone):
        """Test that colleague panel includes placements ending today (boundary test)"""
        # Mock today as 2024-06-15
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Create assignment with placement ending today
        assignment = Assignment.objects.create(
            name="Test Assignment Ending Today",
            status="INGEVULD",
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Test Service",
            skill=self.skill,
            source="wies",
        )
        Placement.objects.create(
            colleague=self.colleague,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 15),  # Today
            source="wies",
        )

        # Get panel data using view method
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        view = PlacementListView()
        view.request = request
        panel_data = view._get_colleague_panel_data(self.colleague)  # noqa: SLF001 (private member access)

        # Verify assignment ending today is included
        assignment_list = panel_data["assignment_list"]
        assignment_ids = [a["id"] for a in assignment_list]
        assert len(assignment_ids) == 1, "Panel should contain the assignment with placement ending today"
        assert assignment.id in assignment_ids, "Assignment with placement ending today should be included"
