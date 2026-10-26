"""Markup that the WCAG audits pinned down."""

from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.template import engines
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
from wies.core.views import PlacementListView

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

    def test_card_grids_are_lists_of_cards(self):
        """nldd-collection and nldd-card set no list roles themselves."""
        org = OrganizationUnit.objects.create(name="Toets Org", label="Toets Org")
        skill = Skill.objects.create(name="Python Developer")
        assignment = Assignment.objects.create(name="Lopende Opdracht", source="wies", start_date=date(2025, 1, 1))
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        service = Service.objects.create(assignment=assignment, description="Rol", skill=skill)
        colleague = Colleague.objects.create(name="Fred Full", email="fred@rijksoverheid.nl")
        Placement.objects.create(colleague=colleague, service=service, source="wies")
        # Aanvragen lists only opdrachten with an open role.
        Service.objects.create(assignment=assignment, description="Open rol", skill=skill, status="OPEN")

        for url, grid_id in ((reverse("home"), "placement-list"), (reverse("assignment-list"), "assignment-card-grid")):
            body = self.client.get(url).content.decode()
            assert f'<nldd-collection id="{grid_id}" role="list"' in body
            assert '<nldd-card role="listitem"' in body

    def test_load_more_cell_is_a_list_item(self):
        """A bare button inside role="list" breaks the list (axe aria-required-children)."""
        assignment = Assignment.objects.create(name="Lopende Opdracht", source="wies", start_date=date(2025, 1, 1))
        skill = Skill.objects.create(name="Python Developer")
        service = Service.objects.create(assignment=assignment, description="Rol", skill=skill)
        for name in ("Anna Een", "Bert Twee"):
            colleague = Colleague.objects.create(name=name, email=f"{name.split()[0].lower()}@rijksoverheid.nl")
            Placement.objects.create(colleague=colleague, service=service, source="wies")

        with patch.object(PlacementListView, "paginate_by", 1):
            body = self.client.get(reverse("home")).content.decode()

        assert '<div class="wies-load-more" role="listitem">' in body

    def test_colleague_panel_name_is_a_level_two_heading(self):
        colleague = Colleague.objects.create(name="Pieter de Wit", email="pieter@rijksoverheid.nl")

        response = self.client.get(reverse("home"), {"collega": colleague.public_id})

        # A focusable h2 in the light DOM, where focus_restore.js lands.
        self.assertContains(response, '<h2 id="panel-title" tabindex="-1">Pieter de Wit</h2>')
        # Inside an nldd-list the row became a tab stop with its own focus ring.
        self.assertNotContains(response, 'accessible-label="Collega"')

    def test_privacy_chip_focus_stop_has_role_and_name(self):
        """The focus lands on a named img, not on an nldd-tag host without a role."""
        template = engines["jinja2"].from_string(
            '{% from "parts/privacy_chip.html" import privacy_chip %}{{ privacy_chip("Alleen voor jou") }}'
        )

        html = template.render()

        focus_stop = html[html.index('<span class="wies-privacy-chip"') :].split(">", 1)[0]
        assert 'role="img"' in focus_stop
        assert 'tabindex="0"' in focus_stop
        assert 'aria-label="Beperkt zichtbaar. Alleen voor jou"' in focus_stop
        assert html.count('tabindex="0"') == 1
        assert 'aria-hidden="true"' in html
