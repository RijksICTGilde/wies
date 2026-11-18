"""The "Meer..." sheet (?filter_modal=) returns before the list builds its page of results."""

import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from wies.core.models import Colleague, Skill, Suborganization
from wies.core.tests.role_helpers import grant_consultant, make_business_manager_user
from wies.core.views.assignments import AanvraagListView
from wies.core.views.placements import PlacementOverviewView
from wies.core.views.users import UserListView

User = get_user_model()

HTMX = {"hx-request": "true"}


def _option_labels(response) -> list[str]:
    # One per option row; the template lowercases it for the search box.
    return re.findall(r'data-option-label="([^"]*)"', response.content.decode())


class FilterModalTest(TestCase):
    def setUp(self):
        self.suborganizations = [Suborganization.objects.create(name=f"Merk {c}") for c in "ABCDE"]
        self.skills = [Skill.objects.create(name=f"Rol {c}") for c in "ABCDE"]
        self.business_manager = make_business_manager_user()

    def _modal(self, url_name, group_id, **params):
        return self.client.get(reverse(url_name), {"filter_modal": group_id, **params}, headers=HTMX)

    def test_wie_zit_waar_sheet_lists_the_group_without_building_the_page(self):
        self.client.force_login(self.business_manager)
        for weergave in ("persoon", "opdracht"):
            # The page build starts with the cards.
            with patch.object(PlacementOverviewView, "_cards_context") as page:
                response = self._modal("home", "onderdeel", weergave=weergave)
            assert response.status_code == 200
            assert response.context_data["filter_modal_group_id"] == "onderdeel"
            assert _option_labels(response) == [f"merk {c}" for c in "abcde"]
            page.assert_not_called()

    def test_aanvragen_sheet_lists_the_group_without_building_the_page(self):
        self.client.force_login(self.business_manager)
        # The page build starts with the cards.
        with patch.object(AanvraagListView, "_cards_context") as page:
            response = self._modal("assignment-list", "rol")
        assert response.status_code == 200
        assert _option_labels(response) == [f"rol {c}" for c in "abcde"]
        page.assert_not_called()

    def test_user_list_sheet_lists_the_group_without_building_the_page(self):
        admin = User.objects.create_user(email="a@rijksoverheid.nl")
        admin.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(admin)
        with patch.object(UserListView, "get_context_data") as page:
            response = self._modal("admin-users", "onderdeel")
        assert response.status_code == 200
        assert _option_labels(response) == [f"merk {c}" for c in "abcde"]
        page.assert_not_called()

    def test_user_list_sheet_still_needs_the_permission(self):
        """The early return sits in get(), after the permission check in dispatch()."""
        self.client.force_login(User.objects.create_user(email="geen@rijksoverheid.nl"))
        assert self._modal("admin-users", "onderdeel").status_code == 403

    def test_bezetting_sheet_lists_the_group_without_building_the_rows(self):
        # Bezetting lists an onderdeel only once a consultant is in it.
        for i, suborganization in enumerate(self.suborganizations):
            email = f"consultant{i}@rijksoverheid.nl"
            user = grant_consultant(User.objects.create_user(email=email))
            Colleague.objects.create(
                name=f"Consultant {i}", email=email, source="wies", user=user, suborganization=suborganization
            )
        self.client.force_login(self.business_manager)
        with patch("wies.core.views.bezetting.colleague_occupancy") as occupancy:
            response = self._modal("bezetting", "onderdeel")
        assert response.status_code == 200
        assert _option_labels(response) == [f"merk {c}" for c in "abcde"]
        occupancy.assert_not_called()

    def test_a_plain_filter_change_still_builds_the_page(self):
        self.client.force_login(self.business_manager)
        response = self.client.get(reverse("home"), headers=HTMX)
        assert response.status_code == 200
        assert "cards" in response.context_data
