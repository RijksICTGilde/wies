from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, AssignmentOrganizationUnit, Colleague, OrganizationUnit

User = get_user_model()


class ExcludedOrgPanelTests(TestCase):
    """An assignment linked to an excluded (intelligence-service) organization is
    hidden from every list; it must be equally unreachable via the side panel and
    the events/delete routes, so it can't be viewed by guessing its id."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="u@rijksoverheid.nl", first_name="U", last_name="s")
        self.colleague = Colleague.objects.create(user=self.user, name="U s", email="u@rijksoverheid.nl", source="wies")
        self.client.force_login(self.user)

        secret_org = OrganizationUnit.objects.create(
            name="Algemene Inlichtingen- en Veiligheidsdienst", abbreviations=["AIVD"]
        )
        normal_org = OrganizationUnit.objects.create(name="Ministerie van Test", abbreviations=["MvT"])

        self.secret = Assignment.objects.create(name="Geheime Opdracht", owner=self.colleague, source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=self.secret, organization=secret_org)
        self.normal = Assignment.objects.create(name="Gewone Opdracht", owner=self.colleague, source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=self.normal, organization=normal_org)

    def _home_panel(self, assignment):
        return self.client.get(reverse("home"), {"opdracht": assignment.id})

    def test_panel_hides_excluded_assignment(self):
        self.assertNotContains(self._home_panel(self.secret), "Geheime Opdracht")

    def test_panel_shows_normal_assignment(self):
        self.assertContains(self._home_panel(self.normal), "Gewone Opdracht")

    def test_events_route_is_404_for_excluded_assignment(self):
        assert self.client.get(reverse("assignment-events-partial", args=[self.secret.id])).status_code == 404
        assert self.client.get(reverse("assignment-events-partial", args=[self.normal.id])).status_code == 200

    def test_delete_route_is_404_for_excluded_assignment(self):
        assert self.client.get(reverse("assignment-delete", args=[self.secret.id])).status_code == 404
