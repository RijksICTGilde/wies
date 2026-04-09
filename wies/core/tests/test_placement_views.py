from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
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
)
from wies.core.services.organizations import get_org_descendant_ids
from wies.core.views import PlacementListView, _build_assignment_panel_data, _get_colleague_assignments

User = get_user_model()


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
        self.auth_user = User.objects.create_user(
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
        self.no_perm_user = User.objects.create_user(
            email="noperm@rijksoverheid.nl",
            first_name="No",
            last_name="Permission",
        )

        # Create user with only some permissions (missing add_service)
        self.partial_perm_user = User.objects.create_user(
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
        self.auth_user = User.objects.create_user(
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
        self.auth_user = User.objects.create_user(
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
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Test Service",
            skill=self.skill,
            source="wies",
        )

        # Create historical placement (ended yesterday)
        Placement.objects.create(
            colleague=self.colleague1,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),  # Yesterday
            source="wies",
        )

        # Create current placement (ending tomorrow)
        Placement.objects.create(
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

        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        # Verify only current placement's colleague is in current members
        current = [m for m in panel_data["team_members"] if not m["historical"] and not m["is_vacancy"]]
        colleague_ids = [m["colleague"].id for m in current]
        assert len(colleague_ids) == 1, "Panel should contain only 1 (current) team member"
        assert self.colleague2.id in colleague_ids, "Current placement's colleague should be in panel"
        assert self.colleague1.id not in colleague_ids, "Historical placement's colleague should be excluded"

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
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment,
            description="Test Service",
            skill=self.skill,
            source="wies",
        )

        # Create placement ending today
        Placement.objects.create(
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

        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        # Verify placement ending today is included in current members
        current = [m for m in panel_data["team_members"] if not m["historical"] and not m["is_vacancy"]]
        colleague_ids = [m["colleague"].id for m in current]
        assert len(colleague_ids) == 1, "Panel should contain the team member ending today"
        assert self.colleague1.id in colleague_ids, "Colleague with placement ending today should be included"


class AssignmentSidePanelHistoricalVisibilityTest(TestCase):
    """Tests for historical placement visibility rules in assignment sidepanel.

    Privacy-critical: historical placements must only be visible to the
    consultant themselves or the assignment's Business Manager.
    """

    def setUp(self):
        self.list_url = reverse("home")
        self.skill = Skill.objects.create(name="Python Developer")

        # Users and their linked colleagues
        self.user_alice = User.objects.create_user(email="alice@rijksoverheid.nl")
        self.colleague_alice = Colleague.objects.create(
            name="Alice",
            email="alice@rijksoverheid.nl",
            source="wies",
            user=self.user_alice,
        )
        self.user_bob = User.objects.create_user(email="bob@rijksoverheid.nl")
        self.colleague_bob = Colleague.objects.create(
            name="Bob",
            email="bob@rijksoverheid.nl",
            source="wies",
            user=self.user_bob,
        )
        self.user_unrelated = User.objects.create_user(email="unrelated@rijksoverheid.nl")
        self.colleague_unrelated = Colleague.objects.create(
            name="Unrelated",
            email="unrelated@rijksoverheid.nl",
            source="wies",
            user=self.user_unrelated,
        )

    def _make_request(self, user):
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = user
        return request

    @patch("wies.core.views.timezone")
    def test_historical_placements_visible_to_own_user(self, mock_timezone):
        """User sees their own historical placements in the panel."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(name="Test Assignment", source="wies")
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_alice)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        historical = [m for m in panel_data["team_members"] if m["historical"]]
        ids = [m["colleague"].id for m in historical]
        assert self.colleague_alice.id in ids

    @patch("wies.core.views.timezone")
    def test_historical_placements_visible_to_bm(self, mock_timezone):
        """BM sees all historical placements on their assignment."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(
            name="Test Assignment",
            source="wies",
            owner=self.colleague_bob,
        )
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_bob)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        historical = [m for m in panel_data["team_members"] if m["historical"]]
        ids = [m["colleague"].id for m in historical]
        assert self.colleague_alice.id in ids

    @patch("wies.core.views.timezone")
    def test_historical_placements_hidden_from_unrelated_user(self, mock_timezone):
        """Unrelated user must NOT see historical placements."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(
            name="Test Assignment",
            source="wies",
            owner=self.colleague_bob,
        )
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_unrelated)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        historical = [m for m in panel_data["team_members"] if m["historical"]]
        assert historical == []

    @patch("wies.core.views.timezone")
    def test_historical_and_current_placements_separated(self, mock_timezone):
        """Current placements are not historical, historical ones are flagged."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(name="Test Assignment", source="wies")
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")

        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",  # historical (ended yesterday)
        )
        Placement.objects.create(
            colleague=self.colleague_bob,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),
            source="wies",
        )

        request = self._make_request(self.user_alice)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        current_ids = [
            m["colleague"].id for m in panel_data["team_members"] if not m["historical"] and not m["is_vacancy"]
        ]
        historical_ids = [m["colleague"].id for m in panel_data["team_members"] if m["historical"]]

        assert self.colleague_bob.id in current_ids
        assert self.colleague_alice.id not in current_ids
        assert self.colleague_alice.id in historical_ids
        assert self.colleague_bob.id not in historical_ids

    @patch("wies.core.views.timezone")
    def test_same_colleague_appears_in_both_current_and_historical(self, mock_timezone):
        """Colleague with one active and one ended service appears in both tiles."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        skill_active = Skill.objects.create(name="Active Skill")
        skill_ended = Skill.objects.create(name="Ended Skill")

        assignment = Assignment.objects.create(name="Mixed Services", source="wies")
        service_active = Service.objects.create(
            assignment=assignment,
            description="s",
            skill=skill_active,
            source="wies",
        )
        service_ended = Service.objects.create(
            assignment=assignment,
            description="s",
            skill=skill_ended,
            source="wies",
        )

        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service_active,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),
            source="wies",
        )
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service_ended,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_alice)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        current = {
            m["colleague"].id: m["skills"]
            for m in panel_data["team_members"]
            if not m["historical"] and not m["is_vacancy"]
        }
        historical = {m["colleague"].id: m["skills"] for m in panel_data["team_members"] if m["historical"]}

        assert self.colleague_alice.id in current, "Should appear in current team"
        assert [s["name"] for s in current[self.colleague_alice.id]] == ["Active Skill"]
        assert self.colleague_alice.id in historical, "Should also appear in historical team"
        assert [s["name"] for s in historical[self.colleague_alice.id]] == ["Ended Skill"]

    @patch("wies.core.views.timezone")
    def test_no_crash_for_user_without_colleague(self, mock_timezone):
        """User without a linked Colleague must not crash and must not see historical data."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        user_no_colleague = User.objects.create_user(email="admin@rijksoverheid.nl")

        assignment = Assignment.objects.create(name="Ended Assignment", source="wies")
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(user_no_colleague)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        historical = [m for m in panel_data["team_members"] if m["historical"]]
        assert historical == [], "User without colleague should not see historical placements"

    @patch("wies.core.views.timezone")
    def test_active_placements_visible_to_unrelated_user(self, mock_timezone):
        """Unrelated user can see active placements (no over-filtering)."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(name="Active Assignment", source="wies")
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),
            source="wies",
        )

        request = self._make_request(self.user_unrelated)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        current = [m for m in panel_data["team_members"] if not m["historical"] and not m["is_vacancy"]]
        ids = [m["colleague"].id for m in current]
        assert self.colleague_alice.id in ids, "Unrelated user should see active placements"

    @patch("wies.core.views.timezone")
    def test_privacy_warning_text_for_consultant_viewer(self, mock_timezone):
        """Consultant viewing own historical placement sees BM privacy text."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(name="Test Assignment", source="wies", owner=self.colleague_bob)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_alice)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        historical = [m for m in panel_data["team_members"] if m["historical"]]
        assert len(historical) == 1
        assert historical[0]["privacy_warning_text"] == "Alleen zichtbaar voor jou en de Business Manager"

    @patch("wies.core.views.timezone")
    def test_privacy_warning_text_for_bm_viewer(self, mock_timezone):
        """BM viewing historical placement sees consultant privacy text."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(name="Test Assignment", source="wies", owner=self.colleague_bob)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_bob)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        historical = [m for m in panel_data["team_members"] if m["historical"]]
        assert len(historical) == 1
        assert historical[0]["privacy_warning_text"] == "Alleen zichtbaar voor jou en de consultant"

    @patch("wies.core.views.timezone")
    def test_privacy_warning_text_absent_on_current_members(self, mock_timezone):
        """Current team members must not have privacy warning text."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(name="Test Assignment", source="wies")
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),
            source="wies",
        )

        request = self._make_request(self.user_alice)
        panel_data = _build_assignment_panel_data(assignment, request, request.path)

        current = [m for m in panel_data["team_members"] if not m["historical"] and not m["is_vacancy"]]
        assert len(current) == 1
        assert current[0]["privacy_warning_text"] is None


class ColleagueAssignmentsHistoricalFilterTest(TestCase):
    """Tests for historical placement filtering in colleague assignments"""

    def setUp(self):
        """Create test data"""
        self.list_url = reverse("home")

        # Create authenticated user
        self.auth_user = User.objects.create_user(
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

        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        assignments = _get_colleague_assignments(request, self.colleague, viewer=None)

        # Verify only current assignment is in active list
        active = [a for a in assignments if not a["historical"]]
        active_ids = [a["id"] for a in active]
        assert len(active_ids) == 1, "Panel should contain only 1 (current) assignment"
        assert assignment_b.id in active_ids, "Current assignment should be in panel"
        assert assignment_a.id not in active_ids, "Historical assignment should be excluded"

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

        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = self.auth_user

        assignments = _get_colleague_assignments(request, self.colleague, viewer=None)

        # Verify assignment ending today is included
        active = [a for a in assignments if not a["historical"]]
        active_ids = [a["id"] for a in active]
        assert len(active_ids) == 1, "Panel should contain the assignment with placement ending today"
        assert assignment.id in active_ids, "Assignment with placement ending today should be included"


class ColleagueAssignmentsHistoricalVisibilityTest(TestCase):
    """Tests for historical assignment visibility rules in colleague assignments.

    Privacy-critical: historical assignments must only be visible to the
    colleague themselves or the assignment's Business Manager.
    """

    def setUp(self):
        self.list_url = reverse("home")
        self.skill = Skill.objects.create(name="Tester")

        self.user_alice = User.objects.create_user(email="cp_alice@rijksoverheid.nl")
        self.colleague_alice = Colleague.objects.create(
            name="Alice",
            email="cp_alice@rijksoverheid.nl",
            source="wies",
            user=self.user_alice,
        )
        self.user_bob = User.objects.create_user(email="cp_bob@rijksoverheid.nl")
        self.colleague_bob = Colleague.objects.create(
            name="Bob",
            email="cp_bob@rijksoverheid.nl",
            source="wies",
            user=self.user_bob,
        )
        self.user_unrelated = User.objects.create_user(email="cp_unrelated@rijksoverheid.nl")
        self.colleague_unrelated = Colleague.objects.create(
            name="Unrelated",
            email="cp_unrelated@rijksoverheid.nl",
            source="wies",
            user=self.user_unrelated,
        )

    def _make_request(self, user):
        factory = RequestFactory()
        request = factory.get(self.list_url)
        request.user = user
        return request

    @patch("wies.core.views.timezone")
    def test_historical_assignments_visible_to_colleague_themselves(self, mock_timezone):
        """Colleague sees their own historical assignments in their panel."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(name="Old Assignment", source="wies")
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_alice)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=self.colleague_alice)

        historical = [a for a in assignments if a["historical"]]
        ids = [a["id"] for a in historical]
        assert assignment.id in ids

    @patch("wies.core.views.timezone")
    def test_historical_assignments_visible_to_bm(self, mock_timezone):
        """BM sees historical assignments of colleagues on their assignment."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(
            name="Old Assignment",
            source="wies",
            owner=self.colleague_bob,
        )
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_bob)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=self.colleague_bob)

        historical = [a for a in assignments if a["historical"]]
        ids = [a["id"] for a in historical]
        assert assignment.id in ids

    @patch("wies.core.views.timezone")
    def test_historical_assignments_hidden_from_unrelated_user(self, mock_timezone):
        """Unrelated user must NOT see historical assignments."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(
            name="Old Assignment",
            source="wies",
            owner=self.colleague_bob,
        )
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_unrelated)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=self.colleague_unrelated)

        historical = [a for a in assignments if a["historical"]]
        assert historical == []

    @patch("wies.core.views.timezone")
    def test_historical_and_current_assignments_separated(self, mock_timezone):
        """Current assignments are not historical, historical ones are flagged."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        old_assignment = Assignment.objects.create(name="Old", source="wies")
        old_service = Service.objects.create(
            assignment=old_assignment, description="s", skill=self.skill, source="wies"
        )
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=old_service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        current_assignment = Assignment.objects.create(name="Current", source="wies")
        current_service = Service.objects.create(
            assignment=current_assignment, description="s", skill=self.skill, source="wies"
        )
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=current_service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),
            source="wies",
        )

        request = self._make_request(self.user_alice)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=self.colleague_alice)

        active = [a for a in assignments if not a["historical"]]
        historical = [a for a in assignments if a["historical"]]
        current_ids = [a["id"] for a in active]
        historical_ids = [a["id"] for a in historical]

        assert current_assignment.id in current_ids
        assert old_assignment.id not in current_ids
        assert old_assignment.id in historical_ids
        assert current_assignment.id not in historical_ids

    @patch("wies.core.views.timezone")
    def test_ended_bm_assignments_hidden_from_unrelated_user(self, mock_timezone):
        """Unrelated user must NOT see ended BM assignments in historical list."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Alice is BM of an ended assignment (no placements involved)
        Assignment.objects.create(
            name="Old BM Assignment",
            source="wies",
            owner=self.colleague_alice,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 14),
        )

        request = self._make_request(self.user_unrelated)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=self.colleague_unrelated)

        historical = [a for a in assignments if a["historical"]]
        assert historical == [], "Unrelated user should not see ended BM assignments"

    @patch("wies.core.views.timezone")
    def test_no_crash_for_user_without_colleague(self, mock_timezone):
        """User without a linked Colleague must not crash and must not see historical data."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        user_no_colleague = User.objects.create_user(
            email="cp_admin@rijksoverheid.nl",
        )

        assignment = Assignment.objects.create(name="Ended Assignment", source="wies")
        service = Service.objects.create(
            assignment=assignment,
            description="s",
            skill=self.skill,
            source="wies",
        )
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(user_no_colleague)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=None)

        historical = [a for a in assignments if a["historical"]]
        assert historical == [], "User without colleague should not see historical assignments"

    @patch("wies.core.views.timezone")
    def test_active_placements_visible_to_unrelated_user(self, mock_timezone):
        """Unrelated user can see active placements (no over-filtering)."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(name="Active Assignment", source="wies")
        service = Service.objects.create(
            assignment=assignment,
            description="s",
            skill=self.skill,
            source="wies",
        )
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),
            source="wies",
        )

        request = self._make_request(self.user_unrelated)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=self.colleague_unrelated)

        active = [a for a in assignments if not a["historical"]]
        active_ids = [a["id"] for a in active]
        assert assignment.id in active_ids, "Unrelated user should see active assignments"

    @patch("wies.core.views.timezone")
    def test_bm_sees_own_ended_placement_on_own_assignment(self, mock_timezone):
        """BM who also has an ended placement on their own assignment sees it in historical."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        assignment = Assignment.objects.create(
            name="Own BM Assignment",
            source="wies",
            owner=self.colleague_alice,
        )
        service = Service.objects.create(
            assignment=assignment,
            description="s",
            skill=self.skill,
            source="wies",
        )
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )

        request = self._make_request(self.user_alice)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=self.colleague_alice)

        historical = [a for a in assignments if a["historical"]]
        ids = [a["id"] for a in historical]
        assert assignment.id in ids, "BM should see their own ended placement on own assignment"

    @patch("wies.core.views.timezone")
    def test_other_bm_cannot_see_ended_bm_assignments(self, mock_timezone):
        """A BM of a different assignment must NOT see another colleague's ended BM assignments."""
        mock_now = Mock()
        mock_now.date.return_value = date(2024, 6, 15)
        mock_timezone.now.return_value = mock_now

        # Alice is BM of an ended assignment
        Assignment.objects.create(
            name="Alice BM Assignment",
            source="wies",
            owner=self.colleague_alice,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 14),
        )

        # Bob is BM of a different assignment (unrelated to Alice's)
        Assignment.objects.create(
            name="Bob BM Assignment",
            source="wies",
            owner=self.colleague_bob,
        )

        request = self._make_request(self.user_bob)
        assignments = _get_colleague_assignments(request, self.colleague_alice, viewer=self.colleague_bob)

        historical = [a for a in assignments if a["historical"]]
        assert historical == [], "BM of different assignment should not see ended BM assignments"


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
        self.auth_user = User.objects.create_user(
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
        self.auth_user = User.objects.create_user(
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

    def test_search_matches_organization_label(self):
        """Text search matches organization label."""
        p = self._create_placement(org=self.org)
        qs = self._search("RWS Hoofdkantoor")
        assert p.id in list(qs.values_list("id", flat=True))

    def test_search_does_not_match_organization_name(self):
        """Text search does not match org name field — only label is searched."""
        self._create_placement(org=self.org)
        qs = self._search("Rijkswaterstaat")
        assert not qs.exists()


class PlacementLooptAfFilterTest(TestCase):
    """Tests for the 'loopt af' end-date filter in PlacementListView."""

    def setUp(self):
        self.auth_user = User.objects.create_user(email="test@rijksoverheid.nl")
        self.skill = Skill.objects.create(name="Test Skill")
        self.colleague_counter = 0

    def _create_placement_with_assignment_end(self, end_date):
        """Create an active placement with an assignment that ends on the given date."""
        self.colleague_counter += 1
        colleague = Colleague.objects.create(
            name=f"Colleague {self.colleague_counter}",
            email=f"c{self.colleague_counter}@rijksoverheid.nl",
            source="wies",
        )
        assignment = Assignment.objects.create(
            name=f"Assignment ending {end_date}",
            start_date=date(2025, 1, 1),
            end_date=end_date,
            source="wies",
        )
        service = Service.objects.create(assignment=assignment, description="S", skill=self.skill, source="wies")
        return Placement.objects.create(colleague=colleague, service=service, period_source="ASSIGNMENT", source="wies")

    def _get_ids(self, params):
        factory = RequestFactory()
        request = factory.get("/", params)
        request.user = self.auth_user
        view = PlacementListView()
        view.request = request
        return set(view.get_queryset().values_list("id", flat=True))

    @patch("wies.core.views.timezone")
    def test_loopt_af_3m(self, mock_timezone):
        mock_now = Mock()
        mock_now.date.return_value = date(2026, 1, 1)
        mock_timezone.now.return_value = mock_now

        p_soon = self._create_placement_with_assignment_end(date(2026, 3, 1))  # within 91 days
        p_later = self._create_placement_with_assignment_end(date(2026, 6, 1))  # within 6m
        p_far = self._create_placement_with_assignment_end(date(2027, 1, 1))  # beyond 6m

        ids = self._get_ids({"loopt_af": "3m"})
        assert p_soon.id in ids
        assert p_later.id not in ids
        assert p_far.id not in ids

    @patch("wies.core.views.timezone")
    def test_loopt_af_6m(self, mock_timezone):
        mock_now = Mock()
        mock_now.date.return_value = date(2026, 1, 1)
        mock_timezone.now.return_value = mock_now

        p_soon = self._create_placement_with_assignment_end(date(2026, 3, 1))
        p_later = self._create_placement_with_assignment_end(date(2026, 6, 1))
        p_far = self._create_placement_with_assignment_end(date(2027, 1, 1))

        ids = self._get_ids({"loopt_af": "6m"})
        assert p_soon.id in ids
        assert p_later.id in ids
        assert p_far.id not in ids

    @patch("wies.core.views.timezone")
    def test_loopt_af_beyond_6m(self, mock_timezone):
        mock_now = Mock()
        mock_now.date.return_value = date(2026, 1, 1)
        mock_timezone.now.return_value = mock_now

        p_soon = self._create_placement_with_assignment_end(date(2026, 3, 1))
        p_far = self._create_placement_with_assignment_end(date(2027, 1, 1))

        ids = self._get_ids({"loopt_af": "6m+"})
        assert p_soon.id not in ids
        assert p_far.id in ids

    @patch("wies.core.views.timezone")
    def test_loopt_af_combined_3m_and_beyond(self, mock_timezone):
        """Selecting both 3m and 6m+ returns union: <=91 days OR >182 days."""
        mock_now = Mock()
        mock_now.date.return_value = date(2026, 1, 1)
        mock_timezone.now.return_value = mock_now

        p_soon = self._create_placement_with_assignment_end(date(2026, 3, 1))
        p_mid = self._create_placement_with_assignment_end(date(2026, 5, 1))  # between 3m and 6m
        p_far = self._create_placement_with_assignment_end(date(2027, 1, 1))

        ids = self._get_ids({"loopt_af": ["3m", "6m+"]})
        assert p_soon.id in ids
        assert p_mid.id not in ids
        assert p_far.id in ids

    @patch("wies.core.views.timezone")
    def test_no_loopt_af_returns_all(self, mock_timezone):
        mock_now = Mock()
        mock_now.date.return_value = date(2026, 1, 1)
        mock_timezone.now.return_value = mock_now

        p_soon = self._create_placement_with_assignment_end(date(2026, 3, 1))
        p_far = self._create_placement_with_assignment_end(date(2027, 1, 1))

        ids = self._get_ids({})
        assert p_soon.id in ids
        assert p_far.id in ids


class ClientModalCountModeTest(TestCase):
    """Tests for count_mode parameter in client_modal view."""

    def setUp(self):
        self.client = Client()
        self.auth_user = User.objects.create_user(email="test@rijksoverheid.nl")
        self.org_with_placements = OrganizationUnit.objects.create(name="OrgA", label="Org A")
        self.org_without_placements = OrganizationUnit.objects.create(name="OrgB", label="Org B")

        # Create a placement for org_with_placements
        skill = Skill.objects.create(name="TestSkill")
        colleague = Colleague.objects.create(name="C", email="c@rijksoverheid.nl", source="wies")
        assignment = Assignment.objects.create(
            name="A", source="wies", start_date=date(2025, 1, 1), end_date=date(2030, 1, 1)
        )
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=self.org_with_placements)
        service = Service.objects.create(assignment=assignment, description="S", skill=skill, source="wies")
        Placement.objects.create(colleague=colleague, service=service, period_source="ASSIGNMENT", source="wies")

    def test_count_mode_none_returns_200(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("client-modal"), {"count_mode": "none"})
        assert response.status_code == 200
        assert b"clientModal" in response.content

    def test_count_mode_none_includes_orgs_without_placements(self):
        """count_mode=none should not prune orgs with zero placements."""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("client-modal"), {"count_mode": "none"})
        content = response.content.decode()
        assert "Org B" in content

    def test_default_count_mode_prunes_empty_orgs(self):
        """Default count_mode (placements) should prune orgs with zero placements."""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("client-modal"))
        content = response.content.decode()
        assert "Org B" not in content
