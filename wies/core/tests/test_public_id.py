"""Tests for the unguessable public_id on URL-exposed models (defense-in-depth
against sequential-PK enumeration). The int PK stays internal; the public_id is
what URLs expose."""

import datetime
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils import timezone

from wies.core.models import (
    Assignment,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)
from wies.core.public_id import PUBLIC_ID_LENGTH, generate_public_id

User = get_user_model()

_PUBLIC_ID_RE = re.compile(rf"^[1-9A-HJ-NP-Za-km-z]{{{PUBLIC_ID_LENGTH}}}$")


def assert_is_public_id(value):
    """A public_id is a short base58 token (not the 36-char UUID it replaced)."""
    assert isinstance(value, str)
    assert _PUBLIC_ID_RE.match(value), value


class AssignmentPublicIdTests(TestCase):
    def test_new_assignment_gets_a_unique_uuid_public_id(self):
        a1 = Assignment.objects.create(name="A", source="wies")
        a2 = Assignment.objects.create(name="B", source="wies")

        assert_is_public_id(a1.public_id)
        assert a1.public_id != a2.public_id

    def test_public_id_is_stable_across_reload(self):
        a = Assignment.objects.create(name="A", source="wies")
        original = a.public_id
        a.refresh_from_db()

        assert a.public_id == original

    def test_base_fixture_loads_and_every_assignment_has_a_public_id(self):
        """`just setup` loads base_dummy_data.json; every assignment must end up
        with a public_id (guards against a future required field the fixture
        forgets)."""
        call_command("loaddata", "base_dummy_data.json", verbosity=0)

        total = Assignment.objects.count()
        assert total > 0
        assert Assignment.objects.filter(public_id__isnull=True).count() == 0


class AssignmentPublicIdRoutingTests(TestCase):
    """The dedicated assignment routes resolve by public_id, so the sequential
    integer PK is no longer walkable in those URLs. (The ?opdracht= panel param
    and the shared inline-edit route are converted in a later slice.)"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="u@rijksoverheid.nl", first_name="U", last_name="s")
        self.owner = Colleague.objects.create(user=self.user, name="Owner", email="u@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="DTC4NL", owner=self.owner, source="wies")
        self.client.force_login(self.user)

    def test_events_route_resolves_by_public_id(self):
        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.public_id]))

        assert response.status_code == 200

    def test_delete_route_resolves_by_public_id_for_owner(self):
        response = self.client.get(reverse("assignment-delete", args=[self.assignment.public_id]))

        assert response.status_code == 200
        self.assertContains(response, "DTC4NL")

    def test_routes_no_longer_accept_integer_pk(self):
        """The old sequential-int URL form must not build or resolve."""
        for route in ("assignment-events-partial", "assignment-delete"):
            try:
                url = reverse(route, args=[self.assignment.pk])
            except NoReverseMatch:
                continue  # int rejected by the <pubid:> pattern - exactly the point
            assert self.client.get(url).status_code == 404, f"{route} still resolved an int pk"


class AssignmentPanelParamTests(TestCase):
    """The ?opdracht= side-panel param resolves by public_id, so an authenticated
    user can no longer walk the integer PK space to harvest opdracht metadata."""

    HX = {"HX-Request": "true", "HX-Target": "side_panel-content"}

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="u@rijksoverheid.nl", first_name="U", last_name="s")
        self.owner = Colleague.objects.create(user=self.user, name="Owner", email="u@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="DTC4NL", owner=self.owner, source="wies")
        self.client.force_login(self.user)

    def _panel(self, route, value):
        return self.client.get(reverse(route) + f"?opdracht={value}", headers=self.HX)

    def test_home_panel_opens_by_public_id(self):
        response = self._panel("home", self.assignment.public_id)

        assert response.status_code == 200
        self.assertContains(response, "DTC4NL")

    def test_panel_request_with_integer_pk_is_404(self):
        """An HX panel request for a non-public_id value returns 404 (HTMX won't
        swap), instead of opening an empty or broken panel - on every surface
        that resolves ?opdracht= (each is a different view type)."""
        for route in ("home", "assignment-list", "user-profile"):
            assert self._panel(route, self.assignment.pk).status_code == 404, route

    def test_panel_request_with_malformed_value_is_404(self):
        for route in ("home", "assignment-list", "user-profile"):
            assert self._panel(route, "not-a-uuid").status_code == 404, route

    def test_full_page_with_invalid_opdracht_stays_graceful(self):
        """A full-page load (no HX) with a bad ?opdracht= renders the page
        without a panel, never a 404."""
        response = self.client.get(reverse("home") + f"?opdracht={self.assignment.pk}")

        assert response.status_code == 200
        self.assertNotContains(response, "DTC4NL")

    def test_assignment_list_panel_opens_by_public_id(self):
        response = self._panel("assignment-list", self.assignment.public_id)

        assert response.status_code == 200
        self.assertContains(response, "DTC4NL")

    def test_profile_panel_opens_by_public_id(self):
        response = self._panel("user-profile", self.assignment.public_id)

        assert response.status_code == 200
        self.assertContains(response, "DTC4NL")


class ColleaguePublicIdTests(TestCase):
    def test_new_colleague_gets_a_unique_uuid_public_id(self):
        c1 = Colleague.objects.create(name="A", email="a@rijksoverheid.nl", source="wies")
        c2 = Colleague.objects.create(name="B", email="b@rijksoverheid.nl", source="wies")

        assert_is_public_id(c1.public_id)
        assert c1.public_id != c2.public_id

    def test_base_fixture_loads_and_every_colleague_has_a_public_id(self):
        call_command("loaddata", "base_dummy_data.json", verbosity=0)

        assert Colleague.objects.count() > 0
        assert Colleague.objects.filter(public_id__isnull=True).count() == 0


class ColleaguePanelParamTests(TestCase):
    """The ?collega= side-panel param resolves by public_id, so an authenticated
    user can no longer walk the integer PK space to harvest colleague PII."""

    HX = {"HX-Request": "true", "HX-Target": "side_panel-content"}

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="u@rijksoverheid.nl", first_name="U", last_name="s")
        Colleague.objects.create(user=self.user, name="Owner", email="u@rijksoverheid.nl", source="wies")
        self.colleague = Colleague.objects.create(name="Jan Testcollega", email="jan@rijksoverheid.nl", source="wies")
        self.client.force_login(self.user)

    def _panel(self, route, value):
        return self.client.get(reverse(route) + f"?collega={value}", headers=self.HX)

    def test_panel_opens_by_public_id(self):
        response = self._panel("home", self.colleague.public_id)

        assert response.status_code == 200
        self.assertContains(response, "Jan Testcollega")

    def test_panel_request_with_integer_pk_is_404(self):
        for route in ("home", "assignment-list", "user-profile"):
            assert self._panel(route, self.colleague.pk).status_code == 404, route

    def test_panel_request_with_malformed_value_is_404(self):
        assert self._panel("home", "not-a-uuid").status_code == 404

    def test_full_page_with_invalid_collega_stays_graceful(self):
        response = self.client.get(reverse("home") + f"?collega={self.colleague.pk}")

        assert response.status_code == 200
        self.assertNotContains(response, "Jan Testcollega")


class PlacementPublicIdTests(TestCase):
    def test_new_placement_gets_a_unique_uuid_public_id(self):
        skill = Skill.objects.create(name="Dev")
        assignment = Assignment.objects.create(name="A", source="wies")
        service = Service.objects.create(assignment=assignment, description="", skill=skill, source="wies")
        colleague = Colleague.objects.create(name="C", email="c@rijksoverheid.nl", source="wies")
        p1 = Placement.objects.create(colleague=colleague, service=service, source="wies")
        p2 = Placement.objects.create(colleague=colleague, service=service, source="wies")

        assert_is_public_id(p1.public_id)
        assert p1.public_id != p2.public_id


class PlacementPanelParamTests(TestCase):
    """The ?plaatsing= panel resolves by public_id AND keeps placement_visibility:
    a placement the viewer may not see is indistinguishable from a nonexistent one."""

    HX = {"HX-Request": "true", "HX-Target": "side_panel-content"}

    def setUp(self):
        self.client = Client()
        self.viewer = User.objects.create_user(email="v@rijksoverheid.nl", first_name="V", last_name="i")
        Colleague.objects.create(user=self.viewer, name="Viewer", email="v@rijksoverheid.nl", source="wies")
        self.owner = Colleague.objects.create(name="Owner", email="o@rijksoverheid.nl", source="wies")
        self.placed = Colleague.objects.create(name="Placed Person", email="p@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="A", owner=self.owner, source="wies")
        skill = Skill.objects.create(name="Dev")
        self.service = Service.objects.create(assignment=self.assignment, description="", skill=skill, source="wies")
        self.client.force_login(self.viewer)

    def _placement(self, *, start_offset, end_offset):
        today = timezone.now().date()
        return Placement.objects.create(
            colleague=self.placed,
            service=self.service,
            period_source=Placement.PLACEMENT,
            specific_start_date=today + datetime.timedelta(days=start_offset),
            specific_end_date=today + datetime.timedelta(days=end_offset),
            source="wies",
        )

    def _panel(self, value):
        return self.client.get(reverse("home") + f"?plaatsing={value}", headers=self.HX)

    def test_active_placement_opens_by_public_id(self):
        active = self._placement(start_offset=-5, end_offset=5)

        response = self._panel(active.public_id)

        assert response.status_code == 200
        self.assertContains(response, "Placed Person")

    def test_hidden_placement_indistinguishable_from_missing(self):
        """Anti-oracle: an ended placement the unrelated viewer may not see returns
        the same 404 as a nonexistent public_id, so its existence stays hidden."""
        hidden = self._placement(start_offset=-30, end_offset=-10)

        assert self._panel(hidden.public_id).status_code == 404
        assert self._panel(generate_public_id()).status_code == 404

    def test_malformed_value_is_404(self):
        assert self._panel("not-a-uuid").status_code == 404

    def test_full_page_with_hidden_placement_stays_graceful(self):
        hidden = self._placement(start_offset=-30, end_offset=-10)

        response = self.client.get(reverse("home") + f"?plaatsing={hidden.public_id}")

        assert response.status_code == 200
        self.assertNotContains(response, "Placed Person")


class UserPublicIdTests(TestCase):
    def test_new_user_gets_a_unique_uuid_public_id(self):
        u1 = User.objects.create_user(email="a@rijksoverheid.nl")
        u2 = User.objects.create_user(email="b@rijksoverheid.nl")

        assert_is_public_id(u1.public_id)
        assert u1.public_id != u2.public_id


class UserAdminRoutePublicIdTests(TestCase):
    """The beheer/gebruikers/<pk>/... routes resolve by public_id."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(email="admin@rijksoverheid.nl", first_name="Ad", last_name="Min")
        self.admin.user_permissions.add(
            Permission.objects.get(codename="change_user"),
            Permission.objects.get(codename="delete_user"),
        )
        self.target = User.objects.create_user(email="target@rijksoverheid.nl", first_name="Tar", last_name="Get")
        self.client.force_login(self.admin)

    def test_edit_route_resolves_by_public_id(self):
        response = self.client.get(reverse("user-edit", args=[self.target.public_id]))

        assert response.status_code == 200

    def test_routes_no_longer_accept_integer_pk(self):
        for route in ("user-edit", "user-delete"):
            try:
                url = reverse(route, args=[self.target.pk])
            except NoReverseMatch:
                continue
            assert self.client.get(url).status_code == 404, route


class LabelPublicIdTests(TestCase):
    def test_category_and_label_get_unique_public_ids(self):
        cat = LabelCategory.objects.create(name="Cat", color="#FF0000")
        l1 = Label.objects.create(name="L1", category=cat)
        l2 = Label.objects.create(name="L2", category=cat)

        assert_is_public_id(cat.public_id)
        assert_is_public_id(l1.public_id)
        assert l1.public_id != l2.public_id


class LabelAdminRoutePublicIdTests(TestCase):
    """The beheer/labels/... routes resolve by public_id."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(email="admin@rijksoverheid.nl", first_name="Ad", last_name="Min")
        self.admin.user_permissions.add(
            Permission.objects.get(codename="change_label"),
            Permission.objects.get(codename="change_labelcategory"),
        )
        self.category = LabelCategory.objects.create(name="Cat", color="#FF0000")
        self.label = Label.objects.create(name="L1", category=self.category)
        self.client.force_login(self.admin)

    def test_label_edit_resolves_by_public_id(self):
        assert self.client.get(reverse("label-edit", args=[self.label.public_id])).status_code == 200

    def test_category_edit_resolves_by_public_id(self):
        assert self.client.get(reverse("label-category-edit", args=[self.category.public_id])).status_code == 200

    def test_routes_no_longer_accept_integer_pk(self):
        for route, obj in (("label-edit", self.label), ("label-category-edit", self.category)):
            try:
                url = reverse(route, args=[obj.pk])
            except NoReverseMatch:
                continue
            assert self.client.get(url).status_code == 404, route


class SkillOrgPublicIdTests(TestCase):
    """Skill and OrganizationUnit back the ?rol=/?org= filter facets; they carry
    a public_id so those URLs stop exposing sequential ids too."""

    def test_skill_gets_a_unique_public_id(self):
        s1 = Skill.objects.create(name="Python")
        s2 = Skill.objects.create(name="Java")

        assert_is_public_id(s1.public_id)
        assert s1.public_id != s2.public_id

    def test_organization_unit_gets_a_unique_public_id(self):
        o1 = OrganizationUnit.objects.create(name="Ministerie A")
        o2 = OrganizationUnit.objects.create(name="Ministerie B")

        assert_is_public_id(o1.public_id)
        assert o1.public_id != o2.public_id
