"""Markup that the WCAG audit pinned down: heading levels in the sidebar and
on the cards, the input purpose of the profile name fields, the current page
in the Beheer menu and the sticky-bar inset of sheets."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
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
from wies.core.roles import ROLE_USER_ADMIN, setup_roles

User = get_user_model()


class A11yMarkupTest(TestCase):
    def setUp(self):
        self.client.force_login(
            User.objects.create_user(email="auth@rijksoverheid.nl", first_name="Au", last_name="Th")
        )

    def test_sidebar_filter_groups_are_level_two_headings(self):
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, "<h2>Opdrachtgever</h2>")
        self.assertNotContains(response, "<h3>Opdrachtgever</h3>")

    def test_date_filter_has_an_id_to_return_focus_to(self):
        # The sidebar is swapped on every filter change; focus_restore.js finds
        # the field again only by id (WCAG 2.4.3).
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        self.assertContains(response, '<nldd-date-field id="filter-beschikbaar_vanaf"')

    def test_profile_name_fields_carry_their_input_purpose(self):
        response = self.client.get(reverse("profile-name-edit"), headers={"hx-request": "true"})
        assert response.status_code == 200
        self.assertContains(response, 'autocomplete="given-name"')
        self.assertContains(response, 'autocomplete="family-name"')

    def test_card_titles_are_level_two_headings(self):
        """The cards follow the page h1, so an h3 there skips a level.

        Both lists: Wie zit waar? renders placement_cards.html, Aanvragen
        renders assignment_card_rows.html.
        """
        org = OrganizationUnit.objects.create(name="Toets Org", label="Toets Org")
        skill = Skill.objects.create(name="Python Developer")

        open_assignment = Assignment.objects.create(name="Open Aanvraag", source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=open_assignment, organization=org)
        Service.objects.create(assignment=open_assignment, description="Open rol", skill=skill, status="OPEN")

        placed_assignment = Assignment.objects.create(
            name="Lopende Opdracht", source="wies", start_date=date(2025, 1, 1)
        )
        AssignmentOrganizationUnit.objects.create(assignment=placed_assignment, organization=org)
        service = Service.objects.create(assignment=placed_assignment, description="Rol", skill=skill)
        colleague = Colleague.objects.create(name="Fred Full", email="fred@rijksoverheid.nl")
        Placement.objects.create(colleague=colleague, service=service, source="wies")

        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, "<h2>Fred Full</h2>")
        self.assertNotContains(response, "<h3>Fred Full</h3>")

        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        self.assertContains(response, "<h2>Open Aanvraag</h2>")
        self.assertNotContains(response, "<h3>Open Aanvraag</h3>")

    def test_admin_sidebar_marks_the_current_page_beyond_colour(self):
        """The DS shows `selected` by colour alone (1.4.1); the bold text is the second cue."""
        setup_roles()
        user_admin = User.objects.create_user(email="beheer@rijksoverheid.nl", first_name="Be", last_name="Heer")
        user_admin.groups.add(Group.objects.get(name=ROLE_USER_ADMIN))
        self.client.force_login(user_admin)

        response = self.client.get(reverse("label-admin"))

        assert response.status_code == 200
        self.assertContains(response, f'<nldd-list-item href="{reverse("label-admin")}" selected>')
        self.assertContains(response, 'text="**Labels**"')
        self.assertContains(response, 'text="Gebruikers"')
        self.assertNotContains(response, 'text="**Gebruikers**"')

    def test_pages_load_the_sticky_bar_inset(self):
        """Without it a sheet's sticky footer covers the focused option (2.4.11)."""
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, "js/sticky_bar_inset.js")
