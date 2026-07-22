import json
import re
from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from wies.core.editables.assignment import _services_display_context, _services_initial
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
from wies.core.views import (
    PlacementListView,
    _build_assignment_panel_data,
    _get_colleague_assignments,
    _resolve_placement_panel,
)

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
        call_args = mock_create_placements.call_args[0][1]
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

    @patch("wies.core.views.create_assignments_from_csv")
    def test_import_strips_utf8_bom(self, mock_create_placements):
        """Test that a UTF-8 BOM at the start of the file is stripped before parsing"""
        mock_create_placements.return_value = {
            "success": True,
            "colleagues_created": 0,
            "assignments_created": 0,
            "services_created": 0,
            "skills_created": 0,
            "placements_created": 0,
            "errors": [],
        }

        self.client.force_login(self.auth_user)
        csv_content = "assignment_name,assignment_description\nTest,Desc"
        csv_file = SimpleUploadedFile(
            "placements.csv", b"\xef\xbb\xbf" + csv_content.encode("utf-8"), content_type="text/csv"
        )

        response = self.client.post(self.import_url, {"csv_file": csv_file})

        assert response.status_code == 200
        mock_create_placements.assert_called_once()
        passed_content = mock_create_placements.call_args[0][1]
        assert passed_content.startswith("assignment_name")


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


class AssignmentServicesDisplayVisibilityTest(TestCase):
    """Ended placements in the side-panel team list are visible only to the
    placed colleague and the BM-owner (via ``_services_display_context``)."""

    def setUp(self):
        self.list_url = reverse("home")
        self.skill = Skill.objects.create(name="Python Developer")

        self.user_alice = User.objects.create_user(email="alice@rijksoverheid.nl")
        self.colleague_alice = Colleague.objects.create(
            name="Alice", email="alice@rijksoverheid.nl", source="wies", user=self.user_alice
        )
        self.user_bob = User.objects.create_user(email="bob@rijksoverheid.nl")
        self.colleague_bob = Colleague.objects.create(
            name="Bob", email="bob@rijksoverheid.nl", source="wies", user=self.user_bob
        )
        self.user_unrelated = User.objects.create_user(email="unrelated@rijksoverheid.nl")
        self.colleague_unrelated = Colleague.objects.create(
            name="Unrelated", email="unrelated@rijksoverheid.nl", source="wies", user=self.user_unrelated
        )

    def _request(self, user):
        request = RequestFactory().get(self.list_url)
        request.user = user
        return request

    def _ended_placement_assignment(self, owner=None):
        assignment = Assignment.objects.create(name="Test Assignment", source="wies", owner=owner)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )
        return assignment

    @patch("wies.core.editables.assignment.timezone")
    def test_ended_placement_hidden_from_unrelated_viewer(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        assignment = self._ended_placement_assignment(owner=self.colleague_bob)

        rows = _services_display_context(assignment, self._request(self.user_unrelated))["value"]

        assert [r for r in rows if r["colleague"]] == [], "Unrelated viewer must not see the ended placement"

    @patch("wies.core.editables.assignment.timezone")
    def test_ended_placement_visible_to_placed_colleague(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        assignment = self._ended_placement_assignment(owner=self.colleague_bob)

        rows = _services_display_context(assignment, self._request(self.user_alice))["value"]

        visible = [r for r in rows if r["colleague"]]
        assert len(visible) == 1
        assert visible[0]["colleague"].id == self.colleague_alice.id
        assert visible[0]["historical"] is True
        assert visible[0]["privacy_warning_text"] == "Alleen zichtbaar voor jou en de Business Manager"

    @patch("wies.core.editables.assignment.timezone")
    def test_ended_placement_visible_to_bm_owner(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        assignment = self._ended_placement_assignment(owner=self.colleague_bob)

        rows = _services_display_context(assignment, self._request(self.user_bob))["value"]

        visible = [r for r in rows if r["colleague"]]
        assert len(visible) == 1
        assert visible[0]["colleague"].id == self.colleague_alice.id
        assert visible[0]["historical"] is True
        assert visible[0]["privacy_warning_text"] == "Alleen zichtbaar voor jou en de consultant"

    @patch("wies.core.editables.assignment.timezone")
    def test_active_placement_visible_to_unrelated_viewer(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        assignment = Assignment.objects.create(name="Active Assignment", source="wies", owner=self.colleague_bob)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 16),
            source="wies",
        )

        rows = _services_display_context(assignment, self._request(self.user_unrelated))["value"]

        visible = [r for r in rows if r["colleague"]]
        assert len(visible) == 1
        assert visible[0]["colleague"].id == self.colleague_alice.id
        assert not visible[0].get("historical")
        assert not visible[0].get("privacy_warning_text")

    @patch("wies.core.editables.assignment.timezone")
    def test_placement_ending_today_is_active(self, mock_timezone):
        # Boundary: a placement ending today still counts as active (visible to all).
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        assignment = Assignment.objects.create(name="Boundary", source="wies", owner=self.colleague_bob)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 15),  # ends today
            source="wies",
        )

        visible = [
            r
            for r in _services_display_context(assignment, self._request(self.user_unrelated))["value"]
            if r["colleague"]
        ]

        assert len(visible) == 1
        assert not visible[0].get("historical")

    @patch("wies.core.editables.assignment.timezone")
    def test_vacancy_always_visible(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        assignment = Assignment.objects.create(name="Vacancy Assignment", source="wies", owner=self.colleague_bob)
        Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies", status="OPEN")

        rows = _services_display_context(assignment, self._request(self.user_unrelated))["value"]

        assert len(rows) == 1
        assert rows[0]["colleague"] is None

    @patch("wies.core.editables.assignment.timezone")
    def test_no_crash_for_user_without_colleague(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        user_no_colleague = User.objects.create_user(email="admin@rijksoverheid.nl")
        assignment = self._ended_placement_assignment(owner=self.colleague_bob)

        rows = _services_display_context(assignment, self._request(user_no_colleague))["value"]

        assert [r for r in rows if r["colleague"]] == []


class AssignmentServicesFutureAndCountTest(TestCase):
    """Future placements are filtered like ended ones, and the team header count
    reflects only the rows the viewer can actually see."""

    def setUp(self):
        self.skill = Skill.objects.create(name="Python Developer")
        self.user_alice = User.objects.create_user(email="alice@rijksoverheid.nl")
        self.colleague_alice = Colleague.objects.create(
            name="Alice", email="alice@rijksoverheid.nl", source="wies", user=self.user_alice
        )
        self.user_bob = User.objects.create_user(email="bob@rijksoverheid.nl")
        self.colleague_bob = Colleague.objects.create(
            name="Bob", email="bob@rijksoverheid.nl", source="wies", user=self.user_bob
        )
        self.user_unrelated = User.objects.create_user(email="unrelated@rijksoverheid.nl")
        self.colleague_unrelated = Colleague.objects.create(
            name="Unrelated", email="unrelated@rijksoverheid.nl", source="wies", user=self.user_unrelated
        )

    def _request(self, user):
        request = RequestFactory().get(reverse("home"))
        request.user = user
        return request

    def _assignment_with_future_placement(self, owner):
        assignment = Assignment.objects.create(name="Future Assignment", source="wies", owner=owner)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2026, 8, 1),  # starts in the future
            specific_end_date=date(2026, 12, 1),
            source="wies",
        )
        return assignment

    @patch("wies.core.editables.assignment.timezone")
    def test_future_placement_hidden_from_unrelated(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        assignment = self._assignment_with_future_placement(owner=self.colleague_bob)

        rows = _services_display_context(assignment, self._request(self.user_unrelated))["value"]

        assert [r for r in rows if r["colleague"]] == []

    @patch("wies.core.editables.assignment.timezone")
    def test_future_placement_visible_to_colleague_with_gepland_label(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        assignment = self._assignment_with_future_placement(owner=self.colleague_bob)

        rows = [
            r for r in _services_display_context(assignment, self._request(self.user_alice))["value"] if r["colleague"]
        ]

        assert len(rows) == 1
        assert rows[0]["period_label"] == "Gepland"
        assert rows[0]["privacy_warning_text"] == "Alleen zichtbaar voor jou en de Business Manager"

    @patch("wies.core.editables.assignment.timezone")
    def test_future_placement_visible_to_bm(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        assignment = self._assignment_with_future_placement(owner=self.colleague_bob)

        rows = [
            r for r in _services_display_context(assignment, self._request(self.user_bob))["value"] if r["colleague"]
        ]

        assert len(rows) == 1
        assert rows[0]["period_label"] == "Gepland"
        assert rows[0]["privacy_warning_text"] == "Alleen zichtbaar voor jou en de consultant"

    @patch("wies.core.views.timezone")
    @patch("wies.core.editables.assignment.timezone")
    def test_team_count_excludes_hidden_placement(self, mock_ed_tz, mock_views_tz):
        for m in (mock_ed_tz, mock_views_tz):
            m.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        assignment = Assignment.objects.create(name="Mixed", source="wies", owner=self.colleague_bob)
        active = Service.objects.create(assignment=assignment, description="a", skill=self.skill, source="wies")
        ended = Service.objects.create(
            assignment=assignment, description="b", skill=Skill.objects.create(name="Ended skill"), source="wies"
        )
        Placement.objects.create(
            colleague=self.colleague_bob,
            service=active,
            period_source="PLACEMENT",
            specific_start_date=date(2026, 1, 1),
            specific_end_date=date(2026, 12, 1),
            source="wies",
        )
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=ended,
            period_source="PLACEMENT",
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2026, 6, 14),
            source="wies",
        )

        unrelated = _build_assignment_panel_data(assignment, self._request(self.user_unrelated))
        bm = _build_assignment_panel_data(assignment, self._request(self.user_bob))

        assert unrelated["team_count"] == 1, "hidden ended placement must not be counted"
        assert bm["team_count"] == 2, "BM sees both"


class PlacementPanelVisibilityTest(TestCase):
    """_resolve_placement_panel enforces the same rule as the team list for the
    standalone ?plaatsing=N side panel (previously reachable by guessing the URL)."""

    def setUp(self):
        self.skill = Skill.objects.create(name="Python Developer")
        self.user_alice = User.objects.create_user(email="alice@rijksoverheid.nl")
        self.colleague_alice = Colleague.objects.create(
            name="Alice", email="alice@rijksoverheid.nl", source="wies", user=self.user_alice
        )
        self.user_bob = User.objects.create_user(email="bob@rijksoverheid.nl")
        self.colleague_bob = Colleague.objects.create(
            name="Bob", email="bob@rijksoverheid.nl", source="wies", user=self.user_bob
        )
        self.user_unrelated = User.objects.create_user(email="unrelated@rijksoverheid.nl")
        self.colleague_unrelated = Colleague.objects.create(
            name="Unrelated", email="unrelated@rijksoverheid.nl", source="wies", user=self.user_unrelated
        )

    def _request(self, user):
        request = RequestFactory().get(reverse("home"))
        request.user = user
        return request

    def _placement(self, *, start, end, owner):
        assignment = Assignment.objects.create(name="Test", source="wies", owner=owner)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        return Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=start,
            specific_end_date=end,
            source="wies",
        )

    @patch("wies.core.views.timezone")
    def test_ended_placement_denied_to_unrelated(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        pl = self._placement(start=date(2024, 1, 1), end=date(2026, 6, 14), owner=self.colleague_bob)

        assert _resolve_placement_panel(self._request(self.user_unrelated), pl.id) is None

    @patch("wies.core.views.timezone")
    def test_future_placement_denied_to_unrelated(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        pl = self._placement(start=date(2026, 8, 1), end=date(2026, 12, 1), owner=self.colleague_bob)

        assert _resolve_placement_panel(self._request(self.user_unrelated), pl.id) is None

    @patch("wies.core.views.timezone")
    def test_ended_placement_shown_to_colleague_with_note(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        pl = self._placement(start=date(2024, 1, 1), end=date(2026, 6, 14), owner=self.colleague_bob)

        data = _resolve_placement_panel(self._request(self.user_alice), pl.id)

        assert data is not None
        card = data["assignment_card"]
        assert card["historical"] is True
        assert card["period_label"] == "Afgelopen"
        assert card["privacy_warning_text"] == "Alleen zichtbaar voor jou en de Business Manager"

    @patch("wies.core.views.timezone")
    def test_future_placement_shown_to_bm_with_gepland(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        pl = self._placement(start=date(2026, 8, 1), end=date(2026, 12, 1), owner=self.colleague_bob)

        data = _resolve_placement_panel(self._request(self.user_bob), pl.id)

        assert data is not None
        card = data["assignment_card"]
        assert card["period_label"] == "Gepland"
        assert card["privacy_warning_text"] == "Alleen zichtbaar voor jou en de consultant"

    @patch("wies.core.views.timezone")
    def test_active_placement_visible_to_unrelated(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        pl = self._placement(start=date(2026, 1, 1), end=date(2026, 12, 1), owner=self.colleague_bob)

        data = _resolve_placement_panel(self._request(self.user_unrelated), pl.id)

        assert data is not None
        assert data["assignment_card"]["privacy_warning_text"] is None


class ColleagueProfileFutureVisibilityTest(TestCase):
    """Own-profile / colleague-panel assignment cards filter future placements
    the same way (visible to the colleague themselves and the BM, not others)."""

    def setUp(self):
        self.skill = Skill.objects.create(name="Python Developer")
        self.user_alice = User.objects.create_user(email="alice@rijksoverheid.nl")
        self.colleague_alice = Colleague.objects.create(
            name="Alice", email="alice@rijksoverheid.nl", source="wies", user=self.user_alice
        )
        self.user_unrelated = User.objects.create_user(email="unrelated@rijksoverheid.nl")
        self.colleague_unrelated = Colleague.objects.create(
            name="Unrelated", email="unrelated@rijksoverheid.nl", source="wies", user=self.user_unrelated
        )

    def _request(self, user):
        request = RequestFactory().get(reverse("home"))
        request.user = user
        return request

    def _future_placement_for_alice(self):
        assignment = Assignment.objects.create(name="Future Assignment", source="wies")
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2026, 8, 1),
            specific_end_date=date(2026, 12, 1),
            source="wies",
        )

    @patch("wies.core.views.timezone")
    def test_future_placement_visible_on_own_profile(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        self._future_placement_for_alice()

        assignments = _get_colleague_assignments(
            self._request(self.user_alice), self.colleague_alice, self.colleague_alice
        )

        historical = [a for a in assignments if a["historical"]]
        assert len(historical) == 1
        assert historical[0]["period_label"] == "Gepland"
        assert historical[0]["privacy_warning_text"] == "Alleen zichtbaar voor jou en de Business Manager"

    @patch("wies.core.views.timezone")
    def test_future_placement_hidden_from_unrelated_profile_viewer(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        self._future_placement_for_alice()

        assignments = _get_colleague_assignments(
            self._request(self.user_unrelated), self.colleague_alice, self.colleague_unrelated
        )

        assert assignments == []


class PlacementListFutureVisibilityTest(TestCase):
    """Not-yet-started placements appear on the 'Wie zit waar?' list only for the
    placed colleague and the assignment's BM-owner, not for others."""

    def setUp(self):
        self.list_url = reverse("home")
        self.skill = Skill.objects.create(name="Python Developer")
        self.user_alice = User.objects.create_user(email="alice@rijksoverheid.nl")
        self.colleague_alice = Colleague.objects.create(
            name="Alice", email="alice@rijksoverheid.nl", source="wies", user=self.user_alice
        )
        self.user_bob = User.objects.create_user(email="bob@rijksoverheid.nl")
        self.colleague_bob = Colleague.objects.create(
            name="Bob", email="bob@rijksoverheid.nl", source="wies", user=self.user_bob
        )
        self.user_unrelated = User.objects.create_user(email="unrelated@rijksoverheid.nl")
        self.colleague_unrelated = Colleague.objects.create(
            name="Unrelated", email="unrelated@rijksoverheid.nl", source="wies", user=self.user_unrelated
        )

    def _future_placement(self, owner):
        assignment = Assignment.objects.create(name="Future", source="wies", owner=owner)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        return Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2026, 8, 1),  # not yet started
            specific_end_date=date(2026, 12, 1),
            source="wies",
        )

    def _queryset_as(self, user, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2026, 6, 15)))
        request = RequestFactory().get(self.list_url)
        request.user = user
        view = PlacementListView()
        view.request = request
        return view.get_queryset()

    @patch("wies.core.views.timezone")
    def test_future_placement_hidden_from_unrelated(self, mock_tz):
        pl = self._future_placement(owner=self.colleague_bob)
        assert pl not in self._queryset_as(self.user_unrelated, mock_tz)

    @patch("wies.core.views.timezone")
    def test_future_placement_hidden_from_user_without_colleague(self, mock_tz):
        pl = self._future_placement(owner=self.colleague_bob)
        user = User.objects.create_user(email="admin@rijksoverheid.nl")
        assert pl not in self._queryset_as(user, mock_tz)

    @patch("wies.core.views.timezone")
    def test_future_placement_visible_to_placed_colleague(self, mock_tz):
        pl = self._future_placement(owner=self.colleague_bob)
        assert pl in self._queryset_as(self.user_alice, mock_tz)

    @patch("wies.core.views.timezone")
    def test_future_placement_visible_to_bm(self, mock_tz):
        pl = self._future_placement(owner=self.colleague_bob)
        assert pl in self._queryset_as(self.user_bob, mock_tz)

    @patch("wies.core.views.timezone")
    def test_active_placement_visible_to_unrelated(self, mock_tz):
        assignment = Assignment.objects.create(name="Active", source="wies", owner=self.colleague_bob)
        service = Service.objects.create(assignment=assignment, description="s", skill=self.skill, source="wies")
        pl = Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source="PLACEMENT",
            specific_start_date=date(2026, 1, 1),
            specific_end_date=date(2026, 12, 1),
            source="wies",
        )
        assert pl in self._queryset_as(self.user_unrelated, mock_tz)


class ServicesInitialQueryCountTest(TestCase):
    """_services_initial must not run a query per service (N+1)."""

    def setUp(self):
        self._colleague = Colleague.objects.create(name="C", email="c@rijksoverheid.nl", source="wies")

    def _assignment_with_services(self, count):
        skill = Skill.objects.create(name=f"Skill-{count}")
        assignment = Assignment.objects.create(name=f"A-{count}", source="wies")
        for _ in range(count):
            service = Service.objects.create(assignment=assignment, description="s", skill=skill, source="wies")
            Placement.objects.create(colleague=self._colleague, service=service, period_source="SERVICE", source="wies")
        return assignment

    def test_query_count_is_constant(self):
        small = self._assignment_with_services(2)
        large = self._assignment_with_services(6)

        with CaptureQueriesContext(connection) as q_small:
            _services_initial(small)
        with CaptureQueriesContext(connection) as q_large:
            _services_initial(large)

        assert len(q_large) == len(q_small), f"N+1: {len(q_small)} vs {len(q_large)} queries for 2 vs 6 services"


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

    def test_count_mode_none_uses_assignment_org_modal_template(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("client-modal"), {"count_mode": "none"})
        assert response.status_code == 200
        # assignment_org_modal.html has this unique element
        assert b"assignmentOrgPickerModal" in response.content

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


def _modal_org_self_counts(response) -> dict[int, int]:
    """Extract {org_id: self placement count} from the client-modal json_script blob.

    Each org renders as a node carrying ``nr_of_placements``; a node that also has
    children emits a ``self: True`` sub-node holding its own (self) count, which is
    the precise value to compare against."""
    html = response.content.decode()
    match = re.search(r'<script id="client-data"[^>]*>(.*?)</script>', html, re.S)
    assert match, "client-data json_script not found in modal response"
    counts: dict[int, int] = {}

    def walk(nodes):
        for node in nodes:
            oid = node["id"]
            if node.get("self") or oid not in counts:
                counts[oid] = node["nr_of_placements"]
            walk(node.get("children", []))

    walk(json.loads(match.group(1)))
    return counts


class ClientModalPlacementCountVisibilityTest(TestCase):
    """Modal per-org placement counts must honour placement_visibility.

    A planned (not-yet-started) placement is private; the opdrachtgever
    (client) filter modal's per-org count must not betray it to an
    unrelated viewer, while the BM-owner's count still includes it.
    """

    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl", first_name="O", last_name="w")
        self.placed_user = User.objects.create_user(email="placed@rijksoverheid.nl", first_name="P", last_name="l")
        self.unrelated_user = User.objects.create_user(email="other@rijksoverheid.nl", first_name="U", last_name="n")

        self.owner_colleague = Colleague.objects.create(
            user=self.owner_user, name="Owner Colleague", email="owner@rijksoverheid.nl", source="wies"
        )
        self.placed_colleague = Colleague.objects.create(
            user=self.placed_user, name="Placed Colleague", email="placed@rijksoverheid.nl", source="wies"
        )
        Colleague.objects.create(
            user=self.unrelated_user, name="Unrelated Colleague", email="other@rijksoverheid.nl", source="wies"
        )

        self.org = OrganizationUnit.objects.create(name="ZZZ Geheime Opdrachtgever", label="ZZZ Geheime Opdrachtgever")
        self.assignment = Assignment.objects.create(name="DTC4NL", owner=self.owner_colleague, source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=self.org)
        skill = Skill.objects.create(name="Software Engineer")
        self.service = Service.objects.create(description="", assignment=self.assignment, skill=skill, source="wies")

    def _place(self, *, start_offset_days, end_offset_days):
        today = timezone.now().date()
        return Placement.objects.create(
            colleague=self.placed_colleague,
            service=self.service,
            specific_start_date=today + timedelta(days=start_offset_days),
            specific_end_date=today + timedelta(days=end_offset_days),
            period_source=Placement.PLACEMENT,
            source="wies",
        )

    def _modal_count_for(self, user) -> int:
        self.client.force_login(user)
        response = self.client.get(reverse("client-modal"))
        assert response.status_code == 200
        return _modal_org_self_counts(response).get(self.org.id, 0)

    def test_planned_placement_not_counted_for_unrelated_viewer(self):
        """A not-yet-started placement is private; its org count must not betray it."""
        self._place(start_offset_days=30, end_offset_days=120)

        assert self._modal_count_for(self.unrelated_user) == 0

    def test_planned_placement_counted_for_bm_owner(self):
        """The BM-owner may see the planned placement, so their count includes it."""
        self._place(start_offset_days=30, end_offset_days=120)

        assert self._modal_count_for(self.owner_user) == 1

    def test_active_placement_counted_for_everyone(self):
        """An active placement is public; the count includes it for any viewer."""
        self._place(start_offset_days=-10, end_offset_days=10)

        assert self._modal_count_for(self.unrelated_user) == 1
