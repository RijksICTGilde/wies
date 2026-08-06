"""Tests for the unguessable public_id on URL-exposed models (defense-in-depth
against sequential-PK enumeration). The int PK stays internal; the public_id is
what URLs expose."""

import datetime
import uuid

import pytest
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils import timezone

from wies.core.editables.colleague import ColleagueEditables
from wies.core.inline_edit.forms import use_public_id_choices
from wies.core.models import (
    Assignment,
    Colleague,
    ErrorEvent,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    Suborganization,
)
from wies.core.public_id import generate_public_id
from wies.core.tests.inline_edit_helpers import post_inline_edit

User = get_user_model()


def assert_is_public_id(value):
    """A public_id is a UUIDv4 (the unguessable identifier exposed in URLs)."""
    assert isinstance(value, uuid.UUID)
    assert value.version == 4


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
    integer PK is no longer walkable in those URLs."""

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
                continue  # int rejected by the <uuid:> converter, which is the point
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


class PublicIdUniquenessTests(TestCase):
    """The database constraint is the guarantee: a duplicate public_id never lands."""

    def test_duplicate_public_id_is_rejected(self):
        taken = uuid.UUID("00000000-0000-4000-8000-00000000000a")
        LabelCategory.objects.create(name="Cat1", color="#FF0000", public_id=taken)
        with self.assertRaises(IntegrityError):  # noqa: PT027 (prefer pytest.raises) - TestCase assertRaises matches the rest of this file
            LabelCategory.objects.create(name="Cat2", color="#00FF00", public_id=taken)


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


@override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
class ErrorEventPublicIdTests(TestCase):
    """The staff error pages are routed on the id, so ErrorEvent carries a
    public_id too: if the staff check ever breaks, the errors (which quote
    tracebacks and request paths) are still not walkable."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(email="staff@rijksoverheid.nl", first_name="St", last_name="Aff")
        self.error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Kapot")
        self.client.force_login(self.staff)

    def test_error_event_gets_a_unique_public_id(self):
        other = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Ook kapot")

        assert_is_public_id(self.error.public_id)
        assert self.error.public_id != other.public_id

    def test_detail_route_resolves_by_public_id(self):
        url = reverse("error-detail", args=[self.error.public_id])
        assert self.client.get(url).status_code == 200

    def test_routes_no_longer_accept_integer_pk(self):
        for route in ("error-detail", "delete-error"):
            try:
                url = reverse(route, args=[self.error.pk])
            except NoReverseMatch:
                continue
            assert self.client.get(url).status_code == 404, route


class SuborganizationPublicIdTests(TestCase):
    def test_suborganization_gets_a_unique_public_id(self):
        s1 = Suborganization.objects.create(name="Rijks ICT Gilde")
        s2 = Suborganization.objects.create(name="Rijksconsultants")

        assert_is_public_id(s1.public_id)
        assert s1.public_id != s2.public_id


class SuborganizationAdminRoutePublicIdTests(TestCase):
    """The beheer/merken/... routes resolve by public_id."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(email="admin@rijksoverheid.nl", first_name="Ad", last_name="Min")
        self.admin.user_permissions.add(
            Permission.objects.get(codename="change_suborganization"),
            Permission.objects.get(codename="delete_suborganization"),
        )
        self.suborganization = Suborganization.objects.create(name="Rijks ICT Gilde")
        self.client.force_login(self.admin)

    def test_edit_route_resolves_by_public_id(self):
        url = reverse("suborganization-edit", args=[self.suborganization.public_id])
        assert self.client.get(url).status_code == 200

    def test_delete_route_resolves_by_public_id(self):
        url = reverse("suborganization-delete", args=[self.suborganization.public_id])
        assert self.client.get(url).status_code == 200

    def test_routes_no_longer_accept_integer_pk(self):
        for route in ("suborganization-edit", "suborganization-delete"):
            try:
                url = reverse(route, args=[self.suborganization.pk])
            except NoReverseMatch:
                continue
            assert self.client.get(url).status_code == 404, route


class ChoiceFieldPublicIdTests(TestCase):
    """A select's option values cross the client boundary too, so they carry the
    public_id instead of Django's default pk. Models without a public_id
    (Group) keep the pk."""

    def test_option_values_are_public_ids_not_pks(self):
        merk = Suborganization.objects.create(name="Rijks ICT Gilde")
        field = ColleagueEditables.suborganization.form_field()

        values = {str(value) for value, _label in field.choices if value}
        assert str(merk.public_id) in values
        assert str(merk.pk) not in values

    def test_model_without_public_id_keeps_the_pk(self):
        field = forms.ModelChoiceField(queryset=Group.objects.all())
        use_public_id_choices(field)
        assert field.to_field_name is None

    def test_field_accepts_public_id_and_rejects_pk(self):
        merk = Suborganization.objects.create(name="Rijks ICT Gilde")
        field = ColleagueEditables.suborganization.form_field()

        assert field.clean(str(merk.public_id)) == merk
        with pytest.raises(ValidationError):
            field.clean(str(merk.pk))

    def test_unparseable_value_is_a_validation_error_not_a_crash(self):
        """A UUID lookup raises on junk, so guard the #503 class of bug: the
        field must reject it as an invalid choice, never surface a 500."""
        Suborganization.objects.create(name="Rijks ICT Gilde")
        field = ColleagueEditables.suborganization.form_field()

        for junk in ("not-a-uuid", "1 OR 1=1", "'; drop--"):
            with pytest.raises(ValidationError):
                field.clean(junk)


class InlineEditChoicePublicIdTests(TestCase):
    """End-to-end: the inline-edit endpoint saves on a public_id and ignores a pk."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="own@rijksoverheid.nl", first_name="Own")
        self.colleague = Colleague.objects.create(
            user=self.user, name="Own", email="own@rijksoverheid.nl", source="wies"
        )
        self.merk = Suborganization.objects.create(name="Rijks ICT Gilde")
        self.client.force_login(self.user)
        self.url = reverse("inline-edit", args=["colleague", self.colleague.public_id, "suborganization"])

    def test_save_by_public_id(self):
        response = post_inline_edit(self.client, self.url, {"suborganization": str(self.merk.public_id)})

        assert response.status_code == 200
        self.colleague.refresh_from_db()
        assert self.colleague.suborganization == self.merk

    def test_pk_is_not_accepted(self):
        response = post_inline_edit(self.client, self.url, {"suborganization": str(self.merk.pk)})

        assert response.status_code == 200
        self.colleague.refresh_from_db()
        assert self.colleague.suborganization is None

    def test_junk_does_not_error(self):
        response = post_inline_edit(self.client, self.url, {"suborganization": "not-a-uuid"})

        assert response.status_code == 200
        self.colleague.refresh_from_db()
        assert self.colleague.suborganization is None


class FilterFacetFailClosedTests(TestCase):
    """Every filter facet fails closed the same way: a value that resolves to no
    row filters everything away instead of being dropped. A stale id in a shared
    or bookmarked URL must never quietly widen the overview."""

    FACETS = ("org", "org_self", "rol", "merk", "labels")
    PLACED_NAME = "Geplaatste Collega"

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="Viewer")
        Colleague.objects.create(user=self.user, name="Viewer", email="viewer@rijksoverheid.nl", source="wies")
        # A second colleague carries the placement, so the row we look for in the
        # response is not the viewer's own name in the header.
        placed = Colleague.objects.create(
            name=self.PLACED_NAME,
            email="placed@rijksoverheid.nl",
            source="wies",
            suborganization=Suborganization.objects.create(name="Rijks ICT Gilde"),
        )
        category = LabelCategory.objects.create(name="Expertise", color="#B3D7EE")
        placed.labels.add(Label.objects.create(name="ICT", category=category))
        self.org = OrganizationUnit.objects.create(name="Ministerie", label="Ministerie")
        assignment = Assignment.objects.create(name="Opdracht", source="wies")
        assignment.organizations.add(self.org)
        self.skill = Skill.objects.create(name="Developer")
        service = Service.objects.create(
            assignment=assignment,
            description="Werk",
            skill=self.skill,
            status="OPEN",
            source="wies",
        )
        self.placement = Placement.objects.create(colleague=placed, service=service, source="wies")
        self.client.force_login(self.user)

    def _page(self, params):
        response = self.client.get(reverse("home"), params)
        assert response.status_code == 200
        return response.content.decode()

    def _shows_placement(self, params):
        return self.PLACED_NAME in self._page(params)

    def test_baseline_without_filters_shows_the_placement(self):
        assert self._shows_placement({})

    def test_unknown_value_matches_nothing_for_every_facet(self):
        stranger = str(generate_public_id())
        for param in self.FACETS:
            with self.subTest(param=param):
                assert not self._shows_placement({param: stranger})

    def test_malformed_value_matches_nothing_for_every_facet(self):
        for param in self.FACETS:
            with self.subTest(param=param):
                assert not self._shows_placement({param: "not-a-uuid"})

    def test_sequential_pk_matches_nothing_for_every_facet(self):
        """The internal pk is not a usable filter token, and it does not fall
        back to unfiltered either."""
        for param in self.FACETS:
            with self.subTest(param=param):
                assert not self._shows_placement({param: "1"})

    def test_empty_value_is_no_filter_at_all(self):
        """``?org=`` is an empty select, not a selection that matched nothing.
        Emptying the list on it would strand the user on a filter they never
        chose."""
        for param in self.FACETS:
            with self.subTest(param=param):
                assert self._shows_placement({param: ""})

    def test_unresolvable_value_stays_clearable(self):
        """Failing closed must not be a dead end: the empty list still carries
        the clear-all button, so the user can get back. Asserted on the chip
        strip's marker, since the modal footer renders a clear-all button
        unconditionally and its raw text would pass either way."""
        stranger = str(generate_public_id())
        for param in self.FACETS:
            with self.subTest(param=param):
                page = self._page({param: stranger})
                assert self.PLACED_NAME not in page
                assert "data-clear-all-filters" in page

    def test_unknown_value_gets_a_named_chip_for_every_facet(self):
        """A chip is only rendered for a value that matches an option, so an
        unknown one needs its own label instead of dropping out of the chip row
        and leaving an empty list with no filter in sight."""
        chip_labels = {
            "org": "Onbekende opdrachtgever",
            "org_self": "Onbekende opdrachtgever",
            "rol": "Onbekende rol",
            "merk": "Onbekend merk",
            "labels": "Onbekend label",
        }
        stranger = str(generate_public_id())
        for param, label in chip_labels.items():
            with self.subTest(param=param):
                assert label in self._page({param: stranger})

    def test_known_value_still_shows_its_own_chip(self):
        page = self._page({"org": str(self.org.public_id), "rol": str(self.skill.public_id)})

        assert "Ministerie" in page
        assert "Developer" in page
        assert "Onbeken" not in page

    def test_a_resolvable_value_still_filters_normally(self):
        assert self._shows_placement({"org": str(self.org.public_id)})
