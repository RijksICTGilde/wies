"""The result lists carry what a screen reader hears after a filter change.

live_region.js reads ``data-announce`` off the list that htmx swapped in; these
tests pin the attribute and its wording to the three lists.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
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

HX = {"HTTP_HX_REQUEST": "true"}


class LiveAnnounceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="auth@rijksoverheid.nl", first_name="Auth", last_name="User")
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(self.user)

    def test_user_list_announces_its_count(self):
        User.objects.create_user(email="een@rijksoverheid.nl", first_name="Een", last_name="Persoon")
        response = self.client.get(reverse("admin-users"), **HX)
        assert response.status_code == 200
        self.assertContains(response, 'data-announce="2 gebruikers"')

    def test_user_list_announces_a_single_result_in_singular(self):
        response = self.client.get(reverse("admin-users"), {"zoek": "Auth"}, **HX)
        self.assertContains(response, 'data-announce="1 gebruiker"')

    def test_empty_user_list_announces_the_empty_state(self):
        response = self.client.get(reverse("admin-users"), {"zoek": "niemand-heet-zo"}, **HX)
        self.assertContains(response, 'data-announce="Geen gebruikers gevonden"')

    def _open_assignment(self):
        # Running now: the home page shows only current placements.
        org = OrganizationUnit.objects.create(name="Org", label="Org")
        assignment = Assignment.objects.create(
            name="Aanvraag", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31), source="wies"
        )
        AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)
        return Service.objects.create(
            assignment=assignment,
            description="Rol",
            skill=Skill.objects.create(name="Developer"),
            status="OPEN",
            source="wies",
        )

    def test_assignment_list_announces_its_count(self):
        self._open_assignment()
        response = self.client.get(reverse("assignment-list"), **HX)
        assert response.status_code == 200
        self.assertContains(response, 'data-announce="1 opdracht"')

    def test_home_announces_colleagues_by_default(self):
        colleague = Colleague.objects.create(name="Collega", email="collega@rijksoverheid.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=self._open_assignment(), source="wies")
        response = self.client.get(reverse("home"), **HX)
        assert response.status_code == 200
        # Jinja escapes the apostrophe in the attribute; the browser reads it back as-is.
        self.assertContains(response, 'data-announce="1 collega&#39;s"')

    def test_empty_home_announces_the_empty_state(self):
        response = self.client.get(reverse("home"), **HX)
        self.assertContains(response, 'data-announce="Geen inzetten gevonden"')
