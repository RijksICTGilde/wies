"""Markup that the WCAG audit pinned down: heading levels in the sidebar and
on the cards, and the input purpose of the profile name fields."""

from datetime import date

from django.contrib.auth import get_user_model
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
