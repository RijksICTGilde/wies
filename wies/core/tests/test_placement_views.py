from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    User,
)
from wies.core.services.organizations import get_org_descendant_ids
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


class OrgDescendantHelperTest(TestCase):
    """Unit tests for get_org_descendant_ids helper function."""

    def test_returns_root_when_no_children(self):
        org = OrganizationUnit.objects.create(name="Lone Org", label="Lone Org")
        result = get_org_descendant_ids([org.id])
        assert result == {org.id}

    def test_includes_all_descendants(self):
        parent = OrganizationUnit.objects.create(name="Parent", label="Parent")
        child = OrganizationUnit.objects.create(name="Child", label="Child", parent=parent)
        grandchild = OrganizationUnit.objects.create(name="Grandchild", label="Grandchild", parent=child)
        result = get_org_descendant_ids([parent.id])
        assert result == {parent.id, child.id, grandchild.id}

    def test_multiple_roots(self):
        a = OrganizationUnit.objects.create(name="A", label="A")
        b = OrganizationUnit.objects.create(name="B", label="B")
        child_a = OrganizationUnit.objects.create(name="Child A", label="Child A", parent=a)
        result = get_org_descendant_ids([a.id, b.id])
        assert result == {a.id, b.id, child_a.id}

    def test_empty_roots(self):
        result = get_org_descendant_ids([])
        assert result == set()


class PlacementOrganizationFilterTest(TestCase):
    """Tests for organization filtering in PlacementListView."""

    def setUp(self):
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@rijksoverheid.nl",
        )
        self.skill = Skill.objects.create(name="Test Skill")

        # Build a 3-level org hierarchy: ministry -> dept -> team
        self.ministry = OrganizationUnit.objects.create(name="Ministry A", label="Ministry A")
        self.dept = OrganizationUnit.objects.create(name="Dept B", label="Dept B", parent=self.ministry)
        self.team = OrganizationUnit.objects.create(name="Team C", label="Team C", parent=self.dept)
        self.other_org = OrganizationUnit.objects.create(name="Other Org", label="Other Org")

    def _create_placement_for_org(self, org, suffix=""):
        """Create an active placement directly linked to the given org."""
        colleague = Colleague.objects.create(
            name=f"Colleague {org.name}{suffix}",
            email=f"c-{org.id}-{suffix}@rijksoverheid.nl",
            source="wies",
        )
        assignment = Assignment.objects.create(
            name=f"Assignment {org.name}{suffix}",
            status="INGEVULD",
            source="wies",
            start_date=date(2025, 1, 1),
            end_date=date(2030, 1, 1),
        )
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        service = Service.objects.create(
            assignment=assignment,
            description="Service",
            skill=self.skill,
            source="wies",
        )
        return Placement.objects.create(
            colleague=colleague,
            service=service,
            period_source="ASSIGNMENT",
            source="wies",
        )

    def _get_queryset(self, params: dict):
        factory = RequestFactory()
        request = factory.get("/", params)
        request.user = self.auth_user
        view = PlacementListView()
        view.request = request
        return view.get_queryset()

    def test_no_org_filter_returns_all(self):
        """Without org params, all active placements are returned."""
        p1 = self._create_placement_for_org(self.ministry)
        p2 = self._create_placement_for_org(self.other_org)
        qs = self._get_queryset({})
        ids = list(qs.values_list("id", flat=True))
        assert p1.id in ids
        assert p2.id in ids

    def test_org_filter_includes_descendants(self):
        """org=ministry includes placements on ministry, dept, and team."""
        p_ministry = self._create_placement_for_org(self.ministry)
        p_dept = self._create_placement_for_org(self.dept)
        p_team = self._create_placement_for_org(self.team)
        p_other = self._create_placement_for_org(self.other_org)

        qs = self._get_queryset({"org": str(self.ministry.id)})
        ids = list(qs.values_list("id", flat=True))

        assert p_ministry.id in ids, "Ministry placement should be included"
        assert p_dept.id in ids, "Dept placement should be included via descendant"
        assert p_team.id in ids, "Team placement should be included via descendant"
        assert p_other.id not in ids, "Other org placement should be excluded"

    def test_org_filter_on_middle_node(self):
        """org=dept includes dept and team but not ministry."""
        self._create_placement_for_org(self.ministry)
        p_dept = self._create_placement_for_org(self.dept)
        p_team = self._create_placement_for_org(self.team)
        p_other = self._create_placement_for_org(self.other_org)

        qs = self._get_queryset({"org": str(self.dept.id)})
        ids = list(qs.values_list("id", flat=True))

        assert p_dept.id in ids
        assert p_team.id in ids
        assert p_other.id not in ids

    def test_org_self_filter_excludes_descendants(self):
        """org_self=ministry only includes direct placements on ministry."""
        p_ministry = self._create_placement_for_org(self.ministry)
        p_dept = self._create_placement_for_org(self.dept)
        p_team = self._create_placement_for_org(self.team)

        qs = self._get_queryset({"org_self": str(self.ministry.id)})
        ids = list(qs.values_list("id", flat=True))

        assert p_ministry.id in ids, "Direct ministry placement should be included"
        assert p_dept.id not in ids, "Dept placement should be excluded for org_self"
        assert p_team.id not in ids, "Team placement should be excluded for org_self"

    def test_overlapping_org_and_org_self_no_duplicates(self):
        """org=X and org_self=X together return results without duplicates."""
        p_ministry = self._create_placement_for_org(self.ministry)
        p_dept = self._create_placement_for_org(self.dept)

        qs = self._get_queryset({"org": str(self.ministry.id), "org_self": str(self.ministry.id)})
        ids = list(qs.values_list("id", flat=True))

        # No duplicates
        assert len(ids) == len(set(ids)), "No duplicate placement rows should appear"
        assert p_ministry.id in ids
        assert p_dept.id in ids

    def test_multiple_org_params_union(self):
        """Multiple org params return the union of their trees."""
        p_ministry = self._create_placement_for_org(self.ministry)
        p_other = self._create_placement_for_org(self.other_org)

        qs = self._get_queryset({"org": [str(self.ministry.id), str(self.other_org.id)]})
        ids = list(qs.values_list("id", flat=True))

        assert p_ministry.id in ids
        assert p_other.id in ids

    def test_org_filter_combined_with_skill_filter(self):
        """org filter combined with rol filter applies both constraints."""
        other_skill = Skill.objects.create(name="Other Skill")

        p_correct = self._create_placement_for_org(self.ministry)  # skill=self.skill
        # Create a placement for ministry but with other_skill
        colleague2 = Colleague.objects.create(name="C2", email="c2@rijksoverheid.nl", source="wies")
        assignment2 = Assignment.objects.create(
            name="Assignment2",
            status="INGEVULD",
            source="wies",
            start_date=date(2025, 1, 1),
            end_date=date(2030, 1, 1),
        )
        AssignmentOrganizationUnit.objects.create(assignment=assignment2, organization=self.ministry)
        service2 = Service.objects.create(assignment=assignment2, description="S2", skill=other_skill, source="wies")
        p_wrong_skill = Placement.objects.create(
            colleague=colleague2, service=service2, period_source="ASSIGNMENT", source="wies"
        )

        qs = self._get_queryset({"org": str(self.ministry.id), "rol": str(self.skill.id)})
        ids = list(qs.values_list("id", flat=True))

        assert p_correct.id in ids, "Placement with correct org and skill should be included"
        assert p_wrong_skill.id not in ids, "Placement with wrong skill should be excluded"


class PlacementSearchTest(TestCase):
    """Tests for the 'zoek' search parameter in PlacementListView."""

    def setUp(self):
        self.auth_user = User.objects.create(
            username="testuser",
            email="test@rijksoverheid.nl",
        )
        self.skill = Skill.objects.create(name="Test Skill")
        self.org = OrganizationUnit.objects.create(
            name="Rijkswaterstaat",
            label="RWS Hoofdkantoor",
            abbreviations=["RWS"],
        )

    def _create_placement(self, colleague_name="Test Colleague", assignment_name="Test Assignment", org=None):
        """Create an active placement with the given parameters."""
        colleague = Colleague.objects.create(
            name=colleague_name,
            email=f"{colleague_name.replace(' ', '')}@rijksoverheid.nl",
            source="wies",
        )
        assignment = Assignment.objects.create(
            name=assignment_name,
            status="INGEVULD",
            source="wies",
            start_date=date(2025, 1, 1),
            end_date=date(2030, 1, 1),
        )
        if org:
            AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        service = Service.objects.create(
            assignment=assignment,
            description="Service",
            skill=self.skill,
            source="wies",
        )
        return Placement.objects.create(
            colleague=colleague,
            service=service,
            period_source="ASSIGNMENT",
            source="wies",
        )

    def _search(self, query):
        factory = RequestFactory()
        request = factory.get("/", {"zoek": query})
        request.user = self.auth_user
        view = PlacementListView()
        view.request = request
        return view.get_queryset()

    def test_search_by_colleague_name(self):
        p = self._create_placement(colleague_name="Jan de Vries")
        qs = self._search("Jan de Vries")
        assert p.id in list(qs.values_list("id", flat=True))

    def test_search_by_assignment_name(self):
        p = self._create_placement(assignment_name="Cloud Migratie Project")
        qs = self._search("Cloud Migratie")
        assert p.id in list(qs.values_list("id", flat=True))

    def test_search_by_organization_name(self):
        p = self._create_placement(org=self.org)
        other = self._create_placement(colleague_name="Andere Collega")
        qs = self._search("Rijkswaterstaat")
        ids = list(qs.values_list("id", flat=True))
        assert p.id in ids
        assert other.id not in ids

    def test_search_by_organization_label(self):
        p = self._create_placement(org=self.org)
        qs = self._search("RWS Hoofdkantoor")
        assert p.id in list(qs.values_list("id", flat=True))

    def test_search_by_organization_abbreviation(self):
        p = self._create_placement(org=self.org)
        qs = self._search("RWS")
        assert p.id in list(qs.values_list("id", flat=True))

    def test_search_by_organization_abbreviation_case_insensitive(self):
        p = self._create_placement(org=self.org)
        qs = self._search("rws")
        assert p.id in list(qs.values_list("id", flat=True))

    def test_search_no_duplicates_with_multiple_matching_orgs(self):
        """Assignment with multiple matching orgs should return the placement only once."""
        org2 = OrganizationUnit.objects.create(
            name="RWS Oost-Nederland",
            label="RWS ON",
        )
        colleague = Colleague.objects.create(
            name="Duplicate Test",
            email="dup@rijksoverheid.nl",
            source="wies",
        )
        assignment = Assignment.objects.create(
            name="Multi Org Assignment",
            status="INGEVULD",
            source="wies",
            start_date=date(2025, 1, 1),
            end_date=date(2030, 1, 1),
        )
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=self.org)
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org2)
        service = Service.objects.create(
            assignment=assignment,
            description="Service",
            skill=self.skill,
            source="wies",
        )
        p = Placement.objects.create(
            colleague=colleague,
            service=service,
            period_source="ASSIGNMENT",
            source="wies",
        )

        qs = self._search("RWS")
        ids = list(qs.values_list("id", flat=True))
        assert ids.count(p.id) == 1, "Placement should appear exactly once despite multiple matching orgs"
