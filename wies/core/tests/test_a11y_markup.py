"""Markup that the WCAG audits pinned down."""

from datetime import date
from unittest.mock import patch

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template import engines
from django.test import RequestFactory, TestCase
from django.urls import reverse

from wies.core.form_mixins import NlddFormMixin
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

    def test_date_filter_has_an_id_to_return_focus_to(self):
        # The sidebar is swapped on every filter change; focus_restore.js finds
        # the field again only by id (WCAG 2.4.3).
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        self.assertContains(response, '<nldd-date-field id="filter-beschikbaar_vanaf"')

    def test_search_field_names_its_suggestion_list(self):
        """The suggestion listbox takes its name from the field's accessible-label,
        not from the placeholder (WCAG 4.1.2)."""
        response = self.client.get(reverse("assignment-list"))
        assert response.status_code == 200
        self.assertContains(response, 'accessible-label="Rol, opdracht of opdrachtgever zoeken"')

    def test_profile_name_fields_carry_their_input_purpose(self):
        response = self.client.get(reverse("profile-name-edit"), headers={"hx-request": "true"})
        assert response.status_code == 200
        self.assertContains(response, 'autocomplete="given-name"')
        self.assertContains(response, 'autocomplete="family-name"')

    def test_card_titles_are_level_two_headings(self):
        """The cards follow the page h1, so an h3 there skips a level.

        Both lists: Wie zit waar? renders placement_cards.html, Aanvragen
        renders aanvraag_card_rows.html, whose heading is the role.
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
        self.assertContains(response, "<h2>Python Developer</h2>")
        self.assertNotContains(response, "<h3>Python Developer</h3>")

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

    def test_accessibility_status_is_text(self):
        """The status is text with a link to the register, not a label image (WCAG 1.1.1)."""
        response = self.client.get(reverse("toegankelijkheid"))
        assert response.status_code == 200
        self.assertContains(response, "Status: A, voldoet volledig.")
        self.assertContains(response, "Bekijk de verklaring in het register")
        self.assertNotContains(response, "toegankelijkheidslabel.svg")


class RequiredNoteTest(TestCase):
    """Forms mark their optional fields; a form without any says once that
    every field is required, or nothing tells the user."""

    NOTE = "Alle velden zijn verplicht."

    def setUp(self):
        setup_roles()
        user = User.objects.create_user(email="beheer@rijksoverheid.nl", first_name="Be", last_name="Heer")
        user.groups.add(Group.objects.get(name=ROLE_USER_ADMIN))
        self.client.force_login(user)

    def test_forms_without_optional_fields_say_so(self):
        for name in ("profile-name-edit", "label-form-create", "label-category-manage"):
            with self.subTest(view=name):
                response = self.client.get(reverse(name), headers={"hx-request": "true"})
                assert response.status_code == 200
                self.assertContains(response, self.NOTE, count=1)

    def test_a_form_with_one_field_says_so_for_that_field(self):
        response = self.client.get(reverse("suborganization-create"), headers={"hx-request": "true"})

        self.assertContains(response, "Dit veld is verplicht.", count=1)
        self.assertNotContains(response, self.NOTE)

    def test_a_generic_form_with_an_optional_field_leaves_it_out(self):
        class WithOptional(NlddFormMixin, forms.Form):
            name = forms.CharField(label="Naam")
            note = forms.CharField(label="Notitie", required=False)

        request = RequestFactory().get("/")
        html = (
            engines["jinja2"]
            .get_template("parts/generic_form_body.html")
            .render(
                {
                    "content": WithOptional(),
                    "form_post_url": "/",
                    "modal_element_id": "x",
                    "form_button_label": "Opslaan",
                },
                request=request,
            )
        )

        assert self.NOTE not in html
        assert "optional" in html


class DateFormatHintTest(TestCase):
    def test_a_date_field_shows_an_example_date(self):
        class WithDate(NlddFormMixin, forms.Form):
            start = forms.DateField(label="Startdatum")

        html = str(WithDate())

        field = html[html.index("<nldd-form-field") :].split(">", 1)[0]
        assert 'supporting-label="Bijvoorbeeld 31-01-2026"' in field

    def test_the_date_filter_shows_the_example_date_too(self):
        self.client.force_login(User.objects.create_user(email="f@rijksoverheid.nl", first_name="F", last_name="F"))
        html = self.client.get(reverse("assignment-list")).content.decode()

        wrapper = html[: html.index('<nldd-date-field id="filter-beschikbaar_vanaf"')].rsplit("<nldd-form-field", 1)[1]
        assert wrapper.startswith(' supporting-label="Bijvoorbeeld 31-01-2026">')
