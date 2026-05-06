from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Event, Placement, Service

User = get_user_model()


class AssignmentEditAttributeTest(TestCase):
    """Tests for assignment inline editing feature"""

    def setUp(self):
        """Create test data"""
        self.client = Client()

        # Create users
        self.user_with_permission = User.objects.create_user(
            email="perm@rijksoverheid.nl",
            first_name="User",
            last_name="WithPerm",
        )
        change_permission = Permission.objects.get(codename="change_assignment")
        self.user_with_permission.user_permissions.add(change_permission)

        self.owner_user = User.objects.create_user(
            email="owner@rijksoverheid.nl",
            first_name="Owner",
            last_name="User",
        )

        self.assigned_user = User.objects.create_user(
            email="assigned@rijksoverheid.nl",
            first_name="Assigned",
            last_name="User",
        )

        self.unrelated_user = User.objects.create_user(
            email="unrelated@rijksoverheid.nl",
            first_name="Unrelated",
            last_name="User",
        )

        # Create colleagues
        self.owner_colleague = Colleague.objects.create(
            user=self.owner_user,
            name="Owner Colleague",
            email="owner@rijksoverheid.nl",
            source="wies",
        )

        self.assigned_colleague = Colleague.objects.create(
            user=self.assigned_user,
            name="Assigned Colleague",
            email="assigned@rijksoverheid.nl",
            source="wies",
        )

        # Create assignment with long extra_info (>300 chars for foldable testing)
        self.assignment = Assignment.objects.create(
            name="Test Assignment",
            owner=self.owner_colleague,
            extra_info="Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10,  # Long text
            source="wies",  # Editable source
        )

        # Create external assignment (not editable)
        self.external_assignment = Assignment.objects.create(
            name="External Assignment",
            owner=self.owner_colleague,
            source="otys_iir",  # External source - not editable
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
        response = self.client.get(reverse("inline-edit", args=["assignment", self.assignment.id, "name"]))
        # Should redirect to login or return 403
        assert response.status_code in [302, 403]

    def test_assignment_edit_with_change_assignment_permission(self):
        """Test that user with change_assignment permission can edit"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]), {"name": "Updated Assignment Name"}
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Updated Assignment Name"

    def test_assignment_edit_as_owner_without_permission(self):
        """Test that assignment owner (BDM) can edit without explicit permission"""
        self.client.force_login(self.owner_user)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]), {"name": "Owner Updated Name"}
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Owner Updated Name"

    def test_assigned_colleague_cannot_edit_name(self):
        """Placed consultants are limited to description-style fields.

        Regression for the PR #311 placement-bug class: a colleague
        placed on the assignment must NOT be able to edit the
        assignment ``name`` (a management field).
        """
        self.client.force_login(self.assigned_user)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]),
            {"name": "Colleague Updated Name"},
        )

        assert response.status_code == 200
        self.assertContains(response, "geen rechten")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Test Assignment"

    def test_assigned_colleague_can_edit_extra_info(self):
        """Placed consultants do gain narrow access to ``extra_info`` (description)."""
        self.client.force_login(self.assigned_user)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "extra_info"]),
            {"extra_info": "Description by colleague"},
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.extra_info == "Description by colleague"

    def test_assigned_colleague_cannot_edit_owner_field(self):
        """Placed consultant is limited to name/extra_info. Attempting
        to edit ``owner`` (a management field) returns the display
        partial with a Dutch denial alert; DB unchanged."""
        self.client.force_login(self.assigned_user)
        other_colleague = Colleague.objects.create(
            name="Other BDM",
            email="other-bdm@rijksoverheid.nl",
            source="wies",
        )

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "owner"]),
            {"owner": other_colleague.id},
        )

        assert response.status_code == 200
        self.assertContains(response, "geen rechten")
        self.assignment.refresh_from_db()
        assert self.assignment.owner_id == self.owner_colleague.id

    def test_assigned_colleague_cannot_edit_period(self):
        """Placed consultant cannot edit the looptijd group."""
        self.client.force_login(self.assigned_user)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "period"]),
            {"start_date": "2026-01-01", "end_date": "2026-12-31"},
        )

        assert response.status_code == 200
        self.assertContains(response, "geen rechten")
        self.assignment.refresh_from_db()
        assert self.assignment.start_date is None
        assert self.assignment.end_date is None

    def test_owner_can_edit_owner_field(self):
        """The BDM owner can edit the ``owner`` field — sanity check
        that the field permission doesn't accidentally block owners."""
        self.client.force_login(self.owner_user)
        new_bdm_user = User.objects.create_user(
            email="new-bdm@rijksoverheid.nl",
            first_name="New",
            last_name="BDM",
        )
        bdm_group, _ = Group.objects.get_or_create(name="Business Development Manager")
        new_bdm_user.groups.add(bdm_group)
        new_bdm = Colleague.objects.create(
            user=new_bdm_user,
            name="New BDM",
            email="new-bdm@rijksoverheid.nl",
            source="wies",
        )

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "owner"]),
            {"owner": new_bdm.id},
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.owner_id == new_bdm.id

    def test_assignment_edit_as_unrelated_user_denied(self):
        """Unrelated users get the display partial + a Dutch denial alert
        (never a bare 403); the DB is not modified."""
        self.client.force_login(self.unrelated_user)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]), {"name": "Unauthorized Update"}
        )

        assert response.status_code == 200
        self.assertContains(response, "geen rechten")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Test Assignment"

    def test_external_source_assignment_not_editable_even_with_permission(self):
        """External-source (otys_iir) assignments are read-only — display
        partial + denial alert, DB unchanged."""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.external_assignment.id, "name"]),
            {"name": "Attempted Update"},
        )

        assert response.status_code == 200
        self.assertContains(response, "geen rechten")
        self.external_assignment.refresh_from_db()
        assert self.external_assignment.name == "External Assignment"

    # ========== Name Field Validation Tests ==========

    def test_assignment_name_edit_success(self):
        """Test successful name edit with valid input"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]), {"name": "Valid New Name"}
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Valid New Name"

    def test_assignment_name_validation(self):
        """Test that empty name returns validation error"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]), {"name": ""}
        )

        assert response.status_code == 200
        self.assertContains(response, "Opdracht naam is verplicht")  # Error message
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Test Assignment"  # Should not change

    # ========== HTMX Workflow Tests ==========

    def test_assignment_edit_get_returns_edit_form(self):
        """GET with `?edit=true` returns the edit form HTML. Plain GET
        returns the display partial (the pencil button triggers the
        `?edit=true` request)."""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]) + "?edit=true"
        )

        assert response.status_code == 200
        self.assertContains(response, "<form")
        self.assertContains(response, "Test Assignment")
        self.assertContains(response, 'name="name"')

    def test_assignment_edit_post_returns_display_view(self):
        """Test that POST request with valid data returns display view"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]), {"name": "Updated Name"}
        )

        assert response.status_code == 200
        self.assertContains(response, "Updated Name")
        # Should return display template, not form
        self.assertNotContains(response, "<form")

    def test_assignment_edit_get_with_cancel_returns_display_view(self):
        """Test that GET with ?cancel=true returns display view without saving"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]) + "?cancel=true"
        )

        assert response.status_code == 200
        self.assertContains(response, "Test Assignment")  # Original value
        # Should return display template, not form
        self.assertNotContains(response, "<input")

    def test_assignment_edit_validation_error_returns_form_with_errors(self):
        """Test that POST with invalid data returns form with error messages"""
        self.client.force_login(self.user_with_permission)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]),
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
            reverse("inline-edit", args=["assignment", self.assignment.id, "extra_info"]) + "?cancel=true"
        )

        assert response.status_code == 200

        # Should contain "Toon meer" toggle label for long text
        self.assertContains(response, "Toon meer")

        # Truncated + full spans render with the inline-edit classes;
        # visibility is toggled via the HTML `hidden` attribute.
        self.assertContains(response, 'class="inline-edit-long-text__truncated"')
        self.assertContains(response, 'class="inline-edit-long-text__full"')

        # Beginning of the text appears in the truncated version.
        self.assertContains(response, "Lorem ipsum dolor sit amet")

        # Full text is hidden initially (client-side toggle flips it).
        self.assertContains(response, "hidden>", count=1)

    def test_assignment_extra_info_short_text_no_toggle(self):
        """Test that short descriptions don't have toggle functionality"""
        self.client.force_login(self.user_with_permission)

        # Update assignment with short text
        self.assignment.extra_info = "Short description"
        self.assignment.save()

        response = self.client.get(
            reverse("inline-edit", args=["assignment", self.assignment.id, "extra_info"]) + "?cancel=true"
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

        response = self.client.get(reverse("inline-edit", args=["assignment", self.assignment.id, "invalid_field"]))

        assert response.status_code == 404

    def test_assignment_edit_nonexistent_assignment_returns_404(self):
        """Test that nonexistent assignment ID returns 404"""
        self.client.force_login(self.user_with_permission)

        response = self.client.get(reverse("inline-edit", args=["assignment", 99999, "name"]))

        assert response.status_code == 404

    # ========== Event Logging Tests ==========

    def test_assignment_edit_creates_event(self):
        """Test that editing an assignment creates an Assignment.update event"""
        self.client.force_login(self.user_with_permission)

        self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]),
            {"name": "Event Test Name"},
        )

        event = Event.objects.get(object_type="Assignment", action="update")
        assert event.object_id == self.assignment.id
        assert event.user == self.user_with_permission
        assert event.user_email == "perm@rijksoverheid.nl"
        assert event.context["field_type"] == "text"
        assert event.context["field_name"] == "name"
        assert event.context["field_label"] == "Opdracht naam"
        assert event.context["old_value"] == "Test Assignment"
        assert event.context["new_value"] == "Event Test Name"

    def test_assignment_edit_no_change_no_event(self):
        """Test that saving the same value does not create an event"""
        self.client.force_login(self.user_with_permission)

        self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]),
            {"name": "Test Assignment"},  # Same as current value
        )

        assert not Event.objects.filter(object_type="Assignment", action="update").exists()

    def test_assignment_edit_event_stores_user(self):
        """Test that event stores the user FK for live lookups"""
        self.client.force_login(self.owner_user)

        self.client.post(
            reverse("assignment-edit-attribute", args=[self.assignment.id, "name"]),
            {"name": "Owner Changed Name"},
        )

        event = Event.objects.get(object_type="Assignment", action="update")
        assert event.user == self.owner_user
        assert event.user_email == "owner@rijksoverheid.nl"

    # ========== Timeline Rendering Tests ==========

    def test_timeline_renders_textarea_change_with_toon_meer(self):
        """Long textarea changes render with the Toon meer pattern, not inline 'van X naar Y'"""
        self.client.force_login(self.user_with_permission)
        long_old = "a" * 500
        long_new = "b" * 500
        Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_type": "textarea",
                "field_name": "extra_info",
                "field_label": "Beschrijving",
                "old_value": long_old,
                "new_value": long_new,
            },
        )

        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200
        self.assertContains(response, "Beschrijving")
        self.assertContains(response, "truncated-text")
        self.assertContains(response, "show-more-toggle")
        self.assertContains(response, "Toon meer")
        # Must NOT use the inline "van ... naar ..." form for textarea
        self.assertNotContains(response, f'van "{long_old}"')

    def test_timeline_textarea_short_value_no_toggle(self):
        """Short textarea values render without the Toon meer toggle"""
        self.client.force_login(self.user_with_permission)
        Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_type": "textarea",
                "field_name": "extra_info",
                "field_label": "Beschrijving",
                "old_value": "short old",
                "new_value": "short new",
            },
        )

        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200
        self.assertContains(response, "short old")
        self.assertContains(response, "short new")
        self.assertNotContains(response, "show-more-toggle")

    def test_timeline_renders_text_change_inline(self):
        """Text field changes render inline as 'van X naar Y'"""
        self.client.force_login(self.user_with_permission)
        Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_type": "text",
                "field_name": "name",
                "field_label": "Opdracht naam",
                "old_value": "Old Name",
                "new_value": "New Name",
            },
        )

        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200
        self.assertContains(response, 'van "Old Name"')
        self.assertContains(response, 'naar "New Name"')
        self.assertNotContains(response, "show-more-toggle")

    def test_timeline_legacy_event_without_field_type_renders_inline(self):
        """Pre-existing events missing field_type fall back to inline rendering"""
        self.client.force_login(self.user_with_permission)
        Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_name": "name",
                "field_label": "Opdracht naam",
                "old_value": "Legacy Old",
                "new_value": "Legacy New",
            },
        )

        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200
        self.assertContains(response, 'van "Legacy Old"')
        self.assertContains(response, 'naar "Legacy New"')

    def test_events_partial_accessible_to_unrelated_user(self):
        """Any authenticated user can open the updates tab, not just BDM/placed colleagues."""
        self.client.force_login(self.unrelated_user)

        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200

    def test_updates_tab_hidden_for_otys_iir_assignment(self):
        """For assignments with source='otys_iir' the updates tab is not rendered."""
        self.client.force_login(self.owner_user)

        response = self.client.get(
            reverse("home") + f"?opdracht={self.external_assignment.id}",
            headers={"HX-Request": "true", "HX-Target": "side_panel-content"},
        )

        assert response.status_code == 200
        self.assertNotContains(response, 'id="tab-updates"')
        self.assertNotContains(response, 'id="tab-panel-updates"')

    def test_updates_tab_shown_for_wies_assignment(self):
        """For assignments with source='wies' the updates tab is rendered."""
        self.client.force_login(self.owner_user)

        response = self.client.get(
            reverse("home") + f"?opdracht={self.assignment.id}",
            headers={"HX-Request": "true", "HX-Target": "side_panel-content"},
        )

        assert response.status_code == 200
        self.assertContains(response, 'id="tab-updates"')
        self.assertContains(response, 'id="tab-panel-updates"')
