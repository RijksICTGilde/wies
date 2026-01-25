from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Ministry, Placement, Service, User


class AssignmentEditAttributeTest(TestCase):
    """Tests for assignment inline editing feature"""

    def setUp(self):
        """Create test data"""
        self.client = Client()

        # Create ministry (required for assignment)
        self.ministry = Ministry.objects.create(
            name="Test Ministry",
            abbreviation="TM",
        )

        # Create users
        self.user_with_permission = User.objects.create(
            username="user_with_perm",
            email="perm@example.com",
            first_name="User",
            last_name="WithPerm",
        )
        change_permission = Permission.objects.get(codename="change_assignment")
        self.user_with_permission.user_permissions.add(change_permission)

        self.owner_user = User.objects.create(
            username="owner_user",
            email="owner@example.com",
            first_name="Owner",
            last_name="User",
        )

        self.assigned_user = User.objects.create(
            username="assigned_user",
            email="assigned@example.com",
            first_name="Assigned",
            last_name="User",
        )

        self.unrelated_user = User.objects.create(
            username="unrelated_user",
            email="unrelated@example.com",
            first_name="Unrelated",
            last_name="User",
        )

        # Create colleagues
        self.owner_colleague = Colleague.objects.create(
            user=self.owner_user,
            name="Owner Colleague",
            email="owner@example.com",
            source="wies",
        )

        self.assigned_colleague = Colleague.objects.create(
            user=self.assigned_user,
            name="Assigned Colleague",
            email="assigned@example.com",
            source="wies",
        )

        # Create assignment with long extra_info (>300 chars for foldable testing)
        self.assignment = Assignment.objects.create(
            name="Test Assignment",
            ministry=self.ministry,
            owner=self.owner_colleague,
            extra_info="Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10,  # Long text
        )

        # Create service linked to assignment
        self.service = Service.objects.create(
            description="Test Service",
            assignment=self.assignment,
            source="wies",
        )

        # Create placement (linking assigned_colleague to service)
        self.placement = Placement.objects.create(
            colleague=self.assigned_colleague,
            service=self.service,
        )

    # ========== Authentication & Authorization Tests ==========

    def test_assignment_edit_requires_login(self):
        """Test that unauthenticated users cannot edit assignments"""
        response = self.client.get(reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]))
        # Should redirect to login or return 403
        assert response.status_code in [302, 403]

    def test_assignment_edit_with_change_assignment_permission(self):
        """Test that user with change_assignment permission can edit"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]), {"name": "Updated Assignment Name"}
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Updated Assignment Name"

    def test_assignment_edit_as_owner_without_permission(self):
        """Test that assignment owner (BDM) can edit without explicit permission"""
        self.client.force_login(self.owner_user)

        response = self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]), {"name": "Owner Updated Name"}
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Owner Updated Name"

    def test_assignment_edit_as_assigned_colleague_without_permission(self):
        """Test that assigned colleague can edit without explicit permission"""
        self.client.force_login(self.assigned_user)

        response = self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]), {"name": "Colleague Updated Name"}
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Colleague Updated Name"

    def test_assignment_edit_as_unrelated_user_denied(self):
        """Test that unrelated user without permission cannot edit"""
        self.client.force_login(self.unrelated_user)

        response = self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]), {"name": "Unauthorized Update"}
        )

        assert response.status_code == 403
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Test Assignment"  # Should not change

    # ========== Name Field Validation Tests ==========

    def test_assignment_name_edit_success(self):
        """Test successful name edit with valid input"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]), {"name": "Valid New Name"}
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Valid New Name"

    def test_assignment_name_validation(self):
        """Test that empty name returns validation error"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]), {"name": ""}
        )

        assert response.status_code == 200
        self.assertContains(response, "Opdracht naam is verplicht")  # Error message
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Test Assignment"  # Should not change

    # ========== HTMX Workflow Tests ==========

    def test_assignment_edit_get_returns_edit_form(self):
        """Test that GET request returns edit form HTML"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]))

        assert response.status_code == 200
        self.assertContains(response, "<form")  # Form element
        self.assertContains(response, "Test Assignment")  # Current value in form
        self.assertContains(response, 'name="name"')  # Input name attribute

    def test_assignment_edit_post_returns_display_view(self):
        """Test that POST request with valid data returns display view"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]), {"name": "Updated Name"}
        )

        assert response.status_code == 200
        self.assertContains(response, "Updated Name")
        # Should return display template, not form
        self.assertNotContains(response, "<form")

    def test_assignment_edit_get_with_cancel_returns_display_view(self):
        """Test that GET with ?cancel=true returns display view without saving"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]) + "?cancel=true"
        )

        assert response.status_code == 200
        self.assertContains(response, "Test Assignment")  # Original value
        # Should return display template, not form
        self.assertNotContains(response, "<input")

    def test_assignment_edit_validation_error_returns_form_with_errors(self):
        """Test that POST with invalid data returns form with error messages"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]),
            {"name": ""},  # Empty (invalid)
        )

        assert response.status_code == 200
        # Should return form template
        self.assertContains(response, "<form")
        # Should contain error message
        self.assertContains(response, "Opdracht naam is verplicht")

    # ========== Extra Info Client-Side Toggle Tests ==========

    def test_assignment_extra_info_long_text_has_toggle(self):
        """Test that long descriptions have both truncated and full text with toggle link"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "extra_info"]) + "?cancel=true"
        )

        assert response.status_code == 200

        # Should contain "Toon meer" link for long text
        self.assertContains(response, "Toon meer")

        # Should contain truncated text class
        self.assertContains(response, 'class="truncated-text"')

        # Should contain full text class (hidden initially)
        self.assertContains(response, 'class="full-text"')

        # Should contain the beginning of the text in truncated version
        self.assertContains(response, "Lorem ipsum dolor sit amet")

        # The full text should be present in the DOM (even if hidden)
        # This allows client-side toggle without backend call
        self.assertContains(response, "display: none", count=1)  # Full text is hidden

    def test_assignment_extra_info_short_text_no_toggle(self):
        """Test that short descriptions don't have toggle functionality"""
        self.client.force_login(self.user_with_permission)

        # Update assignment with short text
        self.assignment.extra_info = "Short description"
        self.assignment.save()

        response = self.client.get(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "extra_info"]) + "?cancel=true"
        )

        assert response.status_code == 200

        # Should NOT contain "Toon meer" link for short text
        self.assertNotContains(response, "Toon meer")

        # Should NOT contain truncated/full text classes
        self.assertNotContains(response, "truncated-text")
        self.assertNotContains(response, "full-text")

        # Should contain the full text directly
        self.assertContains(response, "Short description")

    # ========== Edge Case Tests ==========

    def test_assignment_edit_invalid_attribute_returns_404(self):
        """Test that invalid attribute name returns 404"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(reverse("assignment-edit-attribute", args=[self.assignment.id, "invalid_field"]))

        assert response.status_code == 404

    def test_assignment_edit_nonexistent_assignment_returns_404(self):
        """Test that nonexistent assignment ID returns 404"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(reverse("assignment-edit-attribute", args=[99999, "name"]))

        assert response.status_code == 404
