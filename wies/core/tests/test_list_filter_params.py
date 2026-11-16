from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Label, LabelCategory, Placement, Service, Skill
from wies.core.roles import ROLE_USER_ADMIN

User = get_user_model()


class ListFilterInvalidLabelParamTests(TestCase):
    """A non-numeric ``?labels=`` value is ignored instead of raising a 500."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="V", last_name="iewer")

    def test_home_ignores_non_numeric_label_param(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": "abc"})

        assert response.status_code == 200

    def test_admin_users_ignores_non_numeric_label_param(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin-users"), {"labels": "abc"})

        assert response.status_code == 200

    def test_valid_label_param_still_works(self):
        """A numeric value is still honoured, guarding against over-filtering."""
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": "999999"})

        assert response.status_code == 200


class ActiveFilterIndicatorTests(TestCase):
    """The active-filter indicators reflect the filters actually applied.

    A value resolving to no row still filters everything away, so it counts as
    active; an empty value is unset and must show no indicator. An unresolvable
    value gets an "Onbekend …" token and "Wis alle filters", so the user is not
    stranded on an empty list.
    """

    ACTIVE_FILTER_MARKER = 'data-wies-dismiss="filter"'
    CLEAR_ALL_MARKER = "data-clear-all-filters"

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="V", last_name="iewer")

    def test_home_unresolvable_label_shows_clear_all(self):
        """It empties the list, so the user needs the way back."""
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": "abc"})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER in response.content.decode()

    def test_home_empty_label_hides_clear_all(self):
        """An empty value filters nothing, so nothing is active."""
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": ""})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER not in response.content.decode()

    def test_home_valid_label_shows_filter_tokens(self):
        """A real label id renders a token, proving the negative assertions above
        are not trivially green."""
        category = LabelCategory.objects.create(name="Cat", color="#FF5733")
        label = Label.objects.create(name="Python", category=category)
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": str(label.public_id)})

        assert response.status_code == 200
        assert self.ACTIVE_FILTER_MARKER in response.content.decode()

    def test_admin_users_unresolvable_label_shows_clear_all(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin-users"), {"labels": "abc"})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER in response.content.decode()

    def test_admin_users_empty_label_hides_clear_all(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin-users"), {"labels": ""})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER not in response.content.decode()

    def test_admin_users_valid_label_shows_clear_all(self):
        category = LabelCategory.objects.create(name="Cat", color="#FF5733")
        label = Label.objects.create(name="Python", category=category)
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin-users"), {"labels": str(label.public_id)})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER in response.content.decode()

    def test_assignments_unresolvable_rol_shows_clear_all(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("assignment-list"), {"rol": "abc"})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER in response.content.decode()

    def test_assignments_empty_rol_hides_clear_all(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("assignment-list"), {"rol": ""})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER not in response.content.decode()

    def test_assignments_valid_rol_shows_filter_tokens(self):
        skill = Skill.objects.create(name="Python")
        self.client.force_login(self.user)

        response = self.client.get(reverse("assignment-list"), {"rol": str(skill.public_id)})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER in response.content.decode()


class UserAdminRoleFilterTests(TestCase):
    """``?rol=`` names a Group pk, since Django's Group has no public_id.

    It fails closed like every other facet, so a stale value empties the list
    instead of showing everyone.
    """

    TARGET = "Doelwit"

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="V", last_name="iewer")
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        User.objects.create_user(email="target@rijksoverheid.nl", first_name="T", last_name=self.TARGET)
        self.client.force_login(self.user)

    def _shows_target(self, params):
        response = self.client.get(reverse("admin-users"), params)
        assert response.status_code == 200
        return self.TARGET in response.content.decode()

    def test_baseline_without_filter_shows_the_user(self):
        assert self._shows_target({})

    def test_unknown_group_matches_nothing(self):
        assert not self._shows_target({"rol": "999999"})

    def test_malformed_value_matches_nothing(self):
        assert not self._shows_target({"rol": "abc"})

    def test_empty_value_is_no_filter_at_all(self):
        assert self._shows_target({"rol": ""})

    def test_existing_group_still_filters_normally(self):
        group, _ = Group.objects.get_or_create(name=ROLE_USER_ADMIN)
        User.objects.get(last_name=self.TARGET).groups.add(group)

        assert self._shows_target({"rol": str(group.id)})


class FailClosedCountsTests(TestCase):
    """A filter that matches nothing empties the counts too, not just the list:
    numbers next to an empty list would promise results that are not there."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="V", last_name="iewer")
        self.client.force_login(self.user)
        today = timezone.now().date()
        self.skill = Skill.objects.create(name="Ontwikkelaar")
        assignment = Assignment.objects.create(
            name="Lopend", start_date=today - timedelta(days=10), end_date=today + timedelta(days=30), source="wies"
        )
        service = Service.objects.create(assignment=assignment, description="Rol", skill=self.skill, source="wies")
        colleague = Colleague.objects.create(name="Anna", email="anna@rijksoverheid.nl", source="wies")
        Placement.objects.create(colleague=colleague, service=service, source="wies")

    def _rol_count(self, params):
        response = self.client.get(reverse("home"), params)
        group = next(g for g in response.context_data["filter_groups"] if g["name"] == "rol")
        return next(o["count"] for o in group["options"] if o["value"] == str(self.skill.public_id))

    def test_known_label_free_list_counts(self):
        assert self._rol_count({}) == 1

    def test_unknown_label_zeroes_the_counts(self):
        assert self._rol_count({"labels": "00000000-0000-4000-8000-000000000000"}) == 0

    def test_unknown_loopt_af_value_is_dropped(self):
        """It filters nothing, so it is no active filter and leaves no hidden input behind."""
        response = self.client.get(reverse("home"), {"loopt_af": "1j"})
        assert "loopt_af" not in response.context_data["active_filters"]
        assert 'value="1j"' not in response.content.decode()


class PageNumberTests(TestCase):
    """A stale or edited ?pagina= lands on a real page on every list, never a 404."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="V", last_name="iewer")
        self.client.force_login(self.user)

    def test_every_list_clamps_the_page_number(self):
        for name in ("home", "assignment-list"):
            for page in ("abc", "0", "-1", "999"):
                with self.subTest(list=name, page=page):
                    response = self.client.get(reverse(name), {"pagina": page})
                    assert response.status_code == 200
                    assert response.context_data["page_obj"].number == 1
