from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import Permission

from wies.core.models import User, Assignment, Colleague, Ministry, Placement, Service


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
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
        change_permission = Permission.objects.get(codename='change_assignment')
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
            source='wies',
        )

        self.assigned_colleague = Colleague.objects.create(
            user=self.assigned_user,
            name="Assigned Colleague",
            email="assigned@example.com",
            source='wies',
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
            source='wies',
        )

        # Create placement (linking assigned_colleague to service)
        self.placement = Placement.objects.create(
            colleague=self.assigned_colleague,
            service=self.service,
        )

    # ========== Authentication & Authorization Tests ==========

    def test_assignment_edit_requires_login(self):
        """Test that unauthenticated users cannot edit assignments"""
        response = self.client.get(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name'])
        )
        # Should redirect to login or return 403
        self.assertIn(response.status_code, [302, 403])

    def test_assignment_edit_with_change_assignment_permission(self):
        """Test that user with change_assignment permission can edit"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']),
            {'name': 'Updated Assignment Name'}
        )

        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.name, 'Updated Assignment Name')

    def test_assignment_edit_as_owner_without_permission(self):
        """Test that assignment owner (BDM) can edit without explicit permission"""
        self.client.force_login(self.owner_user)

        response = self.client.post(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']),
            {'name': 'Owner Updated Name'}
        )

        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.name, 'Owner Updated Name')

    def test_assignment_edit_as_assigned_colleague_without_permission(self):
        """Test that assigned colleague can edit without explicit permission"""
        self.client.force_login(self.assigned_user)

        response = self.client.post(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']),
            {'name': 'Colleague Updated Name'}
        )

        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.name, 'Colleague Updated Name')

    def test_assignment_edit_as_unrelated_user_denied(self):
        """Test that unrelated user without permission cannot edit"""
        self.client.force_login(self.unrelated_user)

        response = self.client.post(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']),
            {'name': 'Unauthorized Update'}
        )

        self.assertEqual(response.status_code, 403)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.name, 'Test Assignment')  # Should not change

    # ========== Name Field Validation Tests ==========

    def test_assignment_name_edit_success(self):
        """Test successful name edit with valid input"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']),
            {'name': 'Valid New Name'}
        )

        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.name, 'Valid New Name')

    def test_assignment_name_validation(self):
        """Test that empty name returns validation error"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']),
            {'name': ''}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Opdracht naam is verplicht')  # Error message
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.name, 'Test Assignment')  # Should not change

    # ========== HTMX Workflow Tests ==========

    def test_assignment_edit_get_returns_edit_form(self):
        """Test that GET request returns edit form HTML"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name'])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form')  # Form element
        self.assertContains(response, 'Test Assignment')  # Current value in form
        self.assertContains(response, 'name="name"')  # Input name attribute

    def test_assignment_edit_post_returns_display_view(self):
        """Test that POST request with valid data returns display view"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']),
            {'name': 'Updated Name'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Updated Name')
        # Should return display template, not form
        self.assertNotContains(response, '<form')

    def test_assignment_edit_get_with_cancel_returns_display_view(self):
        """Test that GET with ?cancel=true returns display view without saving"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']) + '?cancel=true'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Assignment')  # Original value
        # Should return display template, not form
        self.assertNotContains(response, '<input')

    def test_assignment_edit_validation_error_returns_form_with_errors(self):
        """Test that POST with invalid data returns form with error messages"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'name']),
            {'name': ''}  # Empty (invalid)
        )

        self.assertEqual(response.status_code, 200)
        # Should return form template
        self.assertContains(response, '<form')
        # Should contain error message
        self.assertContains(response, 'Opdracht naam is verplicht')

    # ========== Extra Info Foldable State Tests ==========

    def test_assignment_extra_info_get_expanded_state(self):
        """Test that GET with ?expanded=true returns expanded display view with full text"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'extra_info']) + '?expanded=true'
        )

        self.assertEqual(response.status_code, 200)
        # Should contain the full text (not truncated)
        self.assertContains(response, 'Lorem ipsum dolor sit amet')
        # Should NOT contain "Toon meer" link when expanded
        self.assertNotContains(response, 'Toon meer')

    def test_assignment_extra_info_get_collapsed_state(self):
        """Test that GET with expanded=false returns collapsed display view"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'extra_info']) + '?expanded=false'
        )

        self.assertEqual(response.status_code, 200)
        # Should contain "Toon meer" link (show more) for long text
        self.assertContains(response, 'Toon meer')

    # ========== Edge Case Tests ==========

    def test_assignment_edit_invalid_attribute_returns_404(self):
        """Test that invalid attribute name returns 404"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse('assignment-edit-attribute', args=[self.assignment.id, 'invalid_field'])
        )

        self.assertEqual(response.status_code, 404)

    def test_assignment_edit_nonexistent_assignment_returns_404(self):
        """Test that nonexistent assignment ID returns 404"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse('assignment-edit-attribute', args=[99999, 'name'])
        )

        self.assertEqual(response.status_code, 404)
