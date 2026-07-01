import importlib

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Event,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)

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

    def test_assigned_colleague_can_edit_name(self):
        """A consultant placed on the assignment can edit ``name``."""
        self.client.force_login(self.assigned_user)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]),
            {"name": "Colleague Updated Name"},
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Colleague Updated Name"

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

    @override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
    def test_staff_member_can_edit_assignment_owner(self):
        """A user in STAFF_EMAILS can edit whole-object fields on an
        assignment they don't own (issue #392)."""
        staff_user = User.objects.create_user(
            email="staff@rijksoverheid.nl",
            first_name="Staff",
            last_name="Member",
        )
        new_bdm_user = User.objects.create_user(
            email="bdm2@rijksoverheid.nl",
            first_name="New",
            last_name="BDM",
        )
        bdm_group, _ = Group.objects.get_or_create(name="Business Development Manager")
        new_bdm_user.groups.add(bdm_group)
        new_bdm = Colleague.objects.create(
            user=new_bdm_user,
            name="New BDM",
            email="bdm2@rijksoverheid.nl",
            source="wies",
        )
        self.client.force_login(staff_user)

        response = self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "owner"]),
            {"owner": new_bdm.id},
        )

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.owner_id == new_bdm.id

    @override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
    def test_staff_member_cannot_edit_external_source_assignment(self):
        """Staff still can't edit non-wies-sourced assignments — the
        ``_is_wies_sourced`` gate runs before the staff branch."""
        staff_user = User.objects.create_user(
            email="staff@rijksoverheid.nl",
            first_name="Staff",
            last_name="Member",
        )
        self.client.force_login(staff_user)

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
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]),
            {"name": "Event Test Name"},
        )

        event = Event.objects.get(object_type="Assignment", action="update")
        assert event.object_id == self.assignment.id
        assert event.user == self.user_with_permission
        assert event.user_email == "perm@rijksoverheid.nl"
        assert event.context["field_name"] == "name"
        assert event.context["field_label"] == "Opdracht naam"
        assert event.context["old_value"] == "Test Assignment"
        assert event.context["new_value"] == "Event Test Name"

    def test_assignment_edit_no_change_no_event(self):
        """Test that saving the same value does not create an event"""
        self.client.force_login(self.user_with_permission)

        self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]),
            {"name": "Test Assignment"},  # Same as current value
        )

        assert not Event.objects.filter(object_type="Assignment", action="update").exists()

    def test_assignment_edit_event_stores_user(self):
        """Test that event stores the user FK for live lookups"""
        self.client.force_login(self.owner_user)

        self.client.post(
            reverse("inline-edit", args=["assignment", self.assignment.id, "name"]),
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
                "field_name": "extra_info",
                "field_label": "Opdrachtomschrijving",
                "old_value": long_old,
                "new_value": long_new,
            },
        )

        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200
        self.assertContains(response, "Opdrachtomschrijving")
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
                "field_name": "extra_info",
                "field_label": "Opdrachtomschrijving",
                "old_value": "short old",
                "new_value": "short new",
            },
        )

        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200
        self.assertContains(response, "short old")
        self.assertContains(response, "short new")
        self.assertNotContains(response, "show-more-toggle")

    def test_timeline_renders_collection_event_as_bullets(self):
        """A services-collection event stores per-change deltas; the
        timeline view formats each change at render time via the spec's
        `render_change` callable and shows them as bullets."""
        self.client.force_login(self.user_with_permission)
        Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_name": "services",
                "field_label": "Team",
                "changes": [
                    {
                        "old": None,
                        "new": {"id": 2, "skill_name": "Java", "colleague_name": None, "description": ""},
                    },
                ],
            },
        )

        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200
        self.assertContains(response, "Team")
        self.assertContains(response, "Toegevoegd: Java (open)")
        # Collection changes render as a bulleted list.
        self.assertContains(response, "<ul")
        self.assertContains(response, "<li>")

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

    def test_timeline_renders_legacy_organizations_string_event(self):
        """Regression: `organizations` events created in the PR #341 release
        window (2026-05-20 → 2026-06-08) stored ``old_value`` / ``new_value``
        as ``str(list_of_dicts)`` — a Python repr — because the pre-#369
        inline-edit code did ``str(old_value or "")`` on every field. The
        current renderer (``_organizations_render_change``) was deployed in
        the 2026-06-10 release and assumes a list of dicts; on a legacy
        event it iterates the string character by character and crashes
        with ``TypeError: string indices must be integers, not 'str'``.

        Post-fix: the runtime guard in ``_attach_audit_render_data`` catches
        the ``TypeError``, logs a warning carrying the event id and field
        name, and falls back to the raw context so the timeline still
        renders."""
        self.client.force_login(self.user_with_permission)
        # Exact shape produced by the pre-#369 code path:
        #     "old_value": str(old_value or "")
        # where old_value was _current_value(obj, organizations_spec), i.e.
        # the list returned by _organizations_initial.
        legacy_old = "[{'organization': <OrganizationUnit: Ministerie van Financien>, 'role': 'PRIMARY'}]"
        legacy_new = (
            "[{'organization': <OrganizationUnit: Ministerie van Financien>, 'role': 'PRIMARY'}, "
            "{'organization': <OrganizationUnit: Ministerie van Buitenlandse Zaken>, 'role': 'INVOLVED'}]"
        )
        event = Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_name": "organizations",
                "field_label": "Opdrachtgever(s)",
                "old_value": legacy_old,
                "new_value": legacy_new,
            },
        )

        with self.assertLogs("wies.core.views", level="WARNING") as log_ctx:
            response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.id]))

        assert response.status_code == 200
        self.assertContains(response, "Opdrachtgever(s)")
        # Operator can audit production logs for the event id + field name.
        assert any(f"id={event.id}" in m and "field=organizations" in m for m in log_ctx.output), log_ctx.output

    def test_migration_scrubs_legacy_organizations_event_in_place(self):
        """The 0008 data migration replaces ``old_value``/``new_value`` with
        ``[]`` on legacy ``organizations`` events whose values are strings,
        and leaves valid rows + unrelated events alone."""

        scrub_module = importlib.import_module("wies.core.migrations.0008_scrub_legacy_organizations_events")

        legacy = Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_name": "organizations",
                "field_label": "Opdrachtgever(s)",
                "old_value": "[{'organization': <OrganizationUnit: X>, 'role': 'PRIMARY'}]",
                "new_value": "[{'organization': <OrganizationUnit: Y>, 'role': 'PRIMARY'}]",
            },
        )
        valid = Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_name": "organizations",
                "field_label": "Opdrachtgever(s)",
                "old_value": [{"name": "X", "role": "PRIMARY"}],
                "new_value": [{"name": "Y", "role": "PRIMARY"}],
            },
        )
        unrelated = Event.objects.create(
            user=self.user_with_permission,
            user_email=self.user_with_permission.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={
                "field_name": "name",
                "field_label": "Opdracht naam",
                "old_value": "Oud",
                "new_value": "Nieuw",
            },
        )

        scrub_module.scrub_legacy_organizations_events(apps, schema_editor=None)

        legacy.refresh_from_db()
        valid.refresh_from_db()
        unrelated.refresh_from_db()

        assert legacy.context["old_value"] == []
        assert legacy.context["new_value"] == []
        assert valid.context["old_value"] == [{"name": "X", "role": "PRIMARY"}]
        assert valid.context["new_value"] == [{"name": "Y", "role": "PRIMARY"}]
        assert unrelated.context["old_value"] == "Oud"
        assert unrelated.context["new_value"] == "Nieuw"

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


class AssignmentDeleteViewTests(TestCase):
    """Issue #313: BM-owner can delete a wies-sourced opdracht; nobody else can."""

    def setUp(self):
        self.client = Client()

        self.owner_user = User.objects.create_user(
            email="owner-del@rijksoverheid.nl", first_name="Owner", last_name="BM"
        )
        self.owner_colleague = Colleague.objects.create(
            user=self.owner_user, name="Owner BM", email="owner-del@rijksoverheid.nl", source="wies"
        )

        # Beheerder-like: holds core.change_assignment but is NOT the owner.
        # Locks in the literal reading of #313 (owner-only DELETE).
        self.admin_user = User.objects.create_user(
            email="admin-del@rijksoverheid.nl", first_name="Admin", last_name="User"
        )
        self.admin_user.user_permissions.add(Permission.objects.get(codename="change_assignment"))

        self.placed_user = User.objects.create_user(
            email="placed-del@rijksoverheid.nl", first_name="Placed", last_name="User"
        )
        self.placed_colleague = Colleague.objects.create(
            user=self.placed_user, name="Placed User", email="placed-del@rijksoverheid.nl", source="wies"
        )

        self.unrelated_user = User.objects.create_user(
            email="unrelated-del@rijksoverheid.nl", first_name="U", last_name="User"
        )

        self.assignment = Assignment.objects.create(name="Te verwijderen", owner=self.owner_colleague, source="wies")
        self.service = Service.objects.create(description="Dienst X", assignment=self.assignment, source="wies")
        self.placement = Placement.objects.create(colleague=self.placed_colleague, service=self.service)

        self.external_assignment = Assignment.objects.create(
            name="Otys opdracht", owner=self.owner_colleague, source="otys_iir"
        )

        self.url = reverse("assignment-delete", args=[self.assignment.id])
        self.external_url = reverse("assignment-delete", args=[self.external_assignment.id])

    def test_owner_can_delete_wies_assignment(self):
        self.client.force_login(self.owner_user)
        assignment_id = self.assignment.id
        service_id = self.service.id
        placement_id = self.placement.id

        response = self.client.post(self.url)

        assert response.status_code == 200
        assert not Assignment.objects.filter(id=assignment_id).exists()
        # Cascades from Assignment → Service → Placement.
        assert not Service.objects.filter(id=service_id).exists()
        assert not Placement.objects.filter(id=placement_id).exists()

    def test_delete_records_audit_event_snapshot_format(self):
        """The delete is never shown in the UI, but the Event we persist for
        the audit trail must capture the cascaded rows in the agreed format:
        the opdracht name, one "rol (occupant or open)" entry per service, and
        the org label per relation."""
        self.client.force_login(self.owner_user)
        self.service.skill = Skill.objects.create(name="Java")
        self.service.save()  # filled by self.placed_colleague
        # A second rol that is still open (aanvraag, no placement).
        Service.objects.create(
            description="Open", assignment=self.assignment, skill=Skill.objects.create(name="Python"), source="wies"
        )
        org = OrganizationUnit.objects.create(name="minbzk", label="Ministerie van BZK")
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=org)
        assignment_id = self.assignment.id

        self.client.post(self.url)

        event = Event.objects.get(object_type="Assignment", action="delete", object_id=assignment_id)
        assert event.user == self.owner_user
        assert event.context["name"] == "Te verwijderen"
        assert event.context["services"] == [f"Java ({self.placed_colleague.name})", "Python (open)"]
        assert event.context["organizations"] == ["Ministerie van BZK"]
        assert "placements" not in event.context

    def test_delete_audit_event_omits_empty_lists(self):
        """An opdracht with no rollen and no opdrachtgevers logs just the
        name — no empty lists in the context."""
        self.client.force_login(self.owner_user)
        empty = Assignment.objects.create(name="Lege opdracht", owner=self.owner_colleague, source="wies")
        empty_id = empty.id

        self.client.post(reverse("assignment-delete", args=[empty_id]))

        event = Event.objects.get(object_type="Assignment", action="delete", object_id=empty_id)
        assert event.context == {"name": "Lege opdracht"}

    def test_delete_redirects_to_page_behind_panel(self):
        """HX-Redirect returns to the page the side panel was opened over,
        with the opdracht panel param stripped (other params preserved)."""
        self.client.force_login(self.owner_user)
        response = self.client.post(
            self.url,
            headers={"HX-Current-URL": "https://testserver/medewerkers/?collega=5&opdracht=99"},
        )
        assert response.status_code == 200
        assert response["HX-Redirect"] == "/medewerkers/?collega=5"

    def test_delete_redirect_falls_back_to_list_without_header(self):
        """Without HX-Current-URL the redirect falls back to the opdrachten-lijst."""
        self.client.force_login(self.owner_user)
        response = self.client.post(self.url)
        assert response.status_code == 200
        assert response["HX-Redirect"] == reverse("assignment-list")

    def test_get_renders_confirmation_modal(self):
        self.client.force_login(self.owner_user)
        response = self.client.get(self.url)
        assert response.status_code == 200
        self.assertContains(response, "Weet je zeker dat je opdracht &#39;Te verwijderen&#39; wilt verwijderen?")
        self.assertContains(response, "Verwijderen is permanent en niet terug te draaien.")
        self.assertContains(response, f'action="{self.url}"')
        self.assertContains(response, "Verwijderen")

    def test_owner_cannot_delete_otys_iir_assignment(self):
        self.client.force_login(self.owner_user)
        response = self.client.post(self.external_url)
        assert response.status_code == 403
        assert Assignment.objects.filter(id=self.external_assignment.id).exists()

    def test_beheerder_cannot_delete(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(self.url)
        assert response.status_code == 403
        assert Assignment.objects.filter(id=self.assignment.id).exists()

    def test_placed_consultant_cannot_delete(self):
        self.client.force_login(self.placed_user)
        response = self.client.post(self.url)
        assert response.status_code == 403
        assert Assignment.objects.filter(id=self.assignment.id).exists()

    def test_unrelated_user_cannot_delete(self):
        self.client.force_login(self.unrelated_user)
        response = self.client.post(self.url)
        assert response.status_code == 403
        assert Assignment.objects.filter(id=self.assignment.id).exists()

    @override_settings(STAFF_EMAILS=["staff-del@rijksoverheid.nl"])
    def test_staff_member_can_delete_wies_assignment(self):
        """A user in STAFF_EMAILS can delete a wies-sourced assignment
        they don't own (parallel to the staff edit permission, #392)."""
        staff_user = User.objects.create_user(
            email="staff-del@rijksoverheid.nl", first_name="Staff", last_name="Member"
        )
        self.client.force_login(staff_user)
        assignment_id = self.assignment.id

        response = self.client.post(self.url)

        assert response.status_code == 200
        assert response["HX-Redirect"] == reverse("assignment-list")
        assert not Assignment.objects.filter(id=assignment_id).exists()

    @override_settings(STAFF_EMAILS=["staff-del@rijksoverheid.nl"])
    def test_staff_member_cannot_delete_otys_iir_assignment(self):
        """Staff still can't delete non-wies-sourced assignments — the
        ``_is_wies_sourced`` gate runs before the staff branch."""
        staff_user = User.objects.create_user(
            email="staff-del@rijksoverheid.nl", first_name="Staff", last_name="Member"
        )
        self.client.force_login(staff_user)
        response = self.client.post(self.external_url)
        assert response.status_code == 403
        assert Assignment.objects.filter(id=self.external_assignment.id).exists()
