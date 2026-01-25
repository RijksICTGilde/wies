from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Config, LabelCategory, User
from wies.core.roles import setup_roles
from wies.core.services.filter_order import CONFIG_KEY


class FilterSettingsViewTest(TestCase):
    """Integration tests for filter settings views"""

    def setUp(self):
        setup_roles()
        self.beheerder = User.objects.create(
            username="beheerder",
            email="beheerder@example.com",
            first_name="Beheerder",
            last_name="User",
        )
        self.beheerder.groups.add(Group.objects.get(name="Beheerder"))

        self.regular_user = User.objects.create(
            username="regular",
            email="regular@example.com",
            first_name="Regular",
            last_name="User",
        )

        self.client = Client()

    def test_filter_settings_requires_permission(self):
        """Page requires change_config permission."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("filter-settings"))
        assert response.status_code == 403

    def test_filter_settings_accessible_for_beheerder(self):
        """Beheerder can access the page."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("filter-settings"))
        assert response.status_code == 200

    def test_filter_settings_shows_all_filters(self):
        """Page displays all filters."""
        LabelCategory.objects.create(name="TestCat", color="#000000")
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("filter-settings"))

        assert response.status_code == 200
        assert b"Ministerie" in response.content
        assert b"Opdrachtgever" in response.content
        assert b"Rollen" in response.content
        assert b"Periode" in response.content
        assert b"TestCat" in response.content


class FilterMoveViewTest(TestCase):
    """Integration tests for filter move view"""

    def setUp(self):
        setup_roles()
        self.beheerder = User.objects.create(
            username="beheerder",
            email="beheerder@example.com",
            first_name="Beheerder",
            last_name="User",
        )
        self.beheerder.groups.add(Group.objects.get(name="Beheerder"))

        self.regular_user = User.objects.create(
            username="regular",
            email="regular@example.com",
            first_name="Regular",
            last_name="User",
        )

        self.client = Client()
        Config.set(CONFIG_KEY, ["ministerie", "opdrachtgever", "rol", "periode"])

    def test_filter_move_requires_post(self):
        """Move endpoint rejects GET requests (405)."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("filter-move", args=[1, "down"]))
        assert response.status_code == 405

    def test_filter_move_requires_permission(self):
        """Move endpoint requires change_config permission."""
        self.client.force_login(self.regular_user)
        response = self.client.post(reverse("filter-move", args=[1, "down"]))
        assert response.status_code == 403

    def test_filter_move_validates_direction(self):
        """Invalid direction returns 400."""
        self.client.force_login(self.beheerder)
        response = self.client.post(reverse("filter-move", args=[1, "invalid"]))
        assert response.status_code == 400

    def test_filter_move_validates_position(self):
        """Invalid position returns 400."""
        self.client.force_login(self.beheerder)
        response = self.client.post(reverse("filter-move", args=[0, "up"]))
        assert response.status_code == 400
        response = self.client.post(reverse("filter-move", args=[100, "up"]))
        assert response.status_code == 400

    def test_filter_move_returns_moved_direction(self):
        """Response contains data-moved-direction attribute."""
        self.client.force_login(self.beheerder)
        response = self.client.post(reverse("filter-move", args=[2, "up"]), headers={"hx-request": "true"})
        assert response.status_code == 200
        assert b'data-moved-direction="up"' in response.content

    def test_filter_order_persists_across_requests(self):
        """Order persists after change."""
        self.client.force_login(self.beheerder)

        # Move opdrachtgever up
        self.client.post(reverse("filter-move", args=[2, "up"]), headers={"hx-request": "true"})

        # Check persisted order
        order = Config.get(CONFIG_KEY)
        assert order[0] == "opdrachtgever"
        assert order[1] == "ministerie"

    def test_filter_move_down_works(self):
        """Filter can be moved down."""
        self.client.force_login(self.beheerder)

        # Move ministerie down
        self.client.post(reverse("filter-move", args=[1, "down"]), headers={"hx-request": "true"})

        order = Config.get(CONFIG_KEY)
        assert order[0] == "opdrachtgever"
        assert order[1] == "ministerie"

    def test_filter_move_returns_204_for_non_htmx(self):
        """Returns 204 No Content for non-HTMX requests."""
        self.client.force_login(self.beheerder)
        response = self.client.post(reverse("filter-move", args=[2, "up"]))
        assert response.status_code == 204
