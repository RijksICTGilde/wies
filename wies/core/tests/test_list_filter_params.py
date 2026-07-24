from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
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
    applied. A non-numeric filter param is ignored by the queryset, so it must not
    count as an active filter — otherwise the page shows an "active" indicator for a
    filter that isn't set.

    Two indicators are gated on ``active_filter_count``:
    - the chip strip's clear-all button (``data-clear-all-filters``), on the
      "Wie zit waar?" (home) and opdrachten (assignment-list) pages;
    - the compact filter bar's count badge (``filter-button--active``), on the
      Gebruikers (admin-users) page, which renders the bar instead of the chips.
    The modal footer holds a second, always-rendered "Wis alle filters" button, so
    asserting on that raw text would be ambiguous."""

    CLEAR_ALL_MARKER = "data-clear-all-filters"
    ACTIVE_BADGE_MARKER = "filter-button--active"

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="V", last_name="iewer")

    def test_home_non_numeric_label_hides_clear_all(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": "abc"})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER not in response.content.decode()

    def test_home_valid_label_shows_clear_all(self):
        """Positive control: a real label id is an active filter, so the clear-all
        button must render — proving the negative assertions aren't trivially green."""
        category = LabelCategory.objects.create(name="Cat", color="#FF5733")
        label = Label.objects.create(name="Python", category=category)
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": str(label.public_id)})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER in response.content.decode()

    def test_admin_users_non_numeric_label_hides_active_badge(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin-users"), {"labels": "abc"})

        assert response.status_code == 200
        assert self.ACTIVE_BADGE_MARKER not in response.content.decode()

    def test_admin_users_valid_label_shows_active_badge(self):
        category = LabelCategory.objects.create(name="Cat", color="#FF5733")
        label = Label.objects.create(name="Python", category=category)
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin-users"), {"labels": str(label.public_id)})

        assert response.status_code == 200
        assert self.ACTIVE_BADGE_MARKER in response.content.decode()

    def test_assignments_non_numeric_rol_hides_clear_all(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("assignment-list"), {"rol": "abc"})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER not in response.content.decode()

    def test_assignments_valid_rol_shows_clear_all(self):
        skill = Skill.objects.create(name="Python")
        self.client.force_login(self.user)

        response = self.client.get(reverse("assignment-list"), {"rol": str(skill.public_id)})

        assert response.status_code == 200
        assert self.CLEAR_ALL_MARKER in response.content.decode()
