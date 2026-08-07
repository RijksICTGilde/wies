from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Label, LabelCategory, Skill

User = get_user_model()


class ListFilterInvalidLabelParamTests(TestCase):
    """A non-numeric ``?labels=`` value must be ignored instead of raising a 500.
    The org and rol filters already skip non-digit values; the label filter must
    behave the same, so a hand-edited or stale URL degrades gracefully."""

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
        """A numeric value is still honoured (guards against over-filtering)."""
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": "999999"})

        assert response.status_code == 200


class ActiveFilterIndicatorTests(TestCase):
    """The active-filter indicators must reflect the filters that are actually
    applied. A filter value that resolves to no row is not ignored: it filters
    everything away, so it IS an active filter and must show its indicator. An
    empty value is the opposite case, an unset filter, and must not.

    The chip strip's dismissable filter tokens (``data-wies-dismiss="filter"``)
    are gated on having active filters, on the "Wie zit waar?" (home) and
    opdrachten (assignment-list) pages.

    De Gebruikers-pagina toont dezelfde chipstrip. Een waarde die nergens naar
    resolvet krijgt geen eigen token (er is geen optie om te labelen), maar wel
    de strip met "Wis alle filters" — anders sta je met een lege lijst zonder
    weg terug."""

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
        """Positive control: a real label id is an active filter, so a filter token
        must render — proving the negative assertions aren't trivially green."""
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
    """``?rol=`` on the Gebruikers page names a Group pk: Group is Django's own
    model and has no public_id. It fails closed like every other facet, so a
    stale or hand-edited value empties the list instead of showing everyone."""

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
        group = Group.objects.create(name="Beheerder")
        User.objects.get(last_name=self.TARGET).groups.add(group)

        assert self._shows_target({"rol": str(group.id)})
