"""Role tag in the user list and the filter sheet (rol/merk/labels) — #544."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Colleague, Suborganization

User = get_user_model()


class UserFilterRenderTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(email="a@rijksoverheid.nl", first_name="A", last_name="Admin")
        self.admin.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.merk = Suborganization.objects.create(name="Merk A")
        self.beheerder = Group.objects.create(name="Beheerder")
        u = User.objects.create_user(email="c@rijksoverheid.nl", first_name="Cor", last_name="Consultant")
        u.groups.add(self.beheerder)
        Colleague.objects.create(
            user=u, name="Cor Consultant", email="c@rijksoverheid.nl", source="wies", suborganization=self.merk
        )

    def test_row_shows_role_tag(self):
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        assert 'text="Beheerder"' in html  # role tag in the row

    def test_filter_sheet_renders_role_and_merk(self):
        # The sheet lives in the page itself: its #filter-form drives the search
        # box and the chips, so it must exist before the sheet is opened.
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        assert "user-filter-sheet" in html
        assert 'id="filter-form"' in html
        assert "Beheerder" in html  # role option
        assert "Merk A" in html  # merk option
        assert 'name="rol"' in html
        assert 'name="merk"' in html

    def test_filter_sheet_collapses_long_group_behind_meer(self):
        # More merken than top_n=3, so the rest collapses behind "Meer...".
        for i in range(6):
            s = Suborganization.objects.create(name=f"Extra Merk {i}")
            u = User.objects.create_user(email=f"x{i}@rijksoverheid.nl", first_name=f"X{i}", last_name="Test")
            Colleague.objects.create(
                user=u, name=f"X{i} Test", email=f"x{i}@rijksoverheid.nl", source="wies", suborganization=s
            )
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        # Shared filter_sidebar pattern: top 3 plus a "Meer..." row.
        assert "Meer..." in html
        assert "filter_modal=merk" in html

    def test_active_filter_renders_chip(self):
        # The chip strip replaced the button counter, which said how many but not what.
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users") + f"?rol={self.beheerder.id}").content.decode()
        assert 'data-wies-dismiss="filter"' in html
        assert 'data-filter-name="rol"' in html
        assert "data-clear-all-filters" in html


class UserFilterOobTest(UserFilterRenderTest):
    def test_apply_swap_carries_chips_and_oob_sheet(self):
        self.client.force_login(self.admin)
        # Simulate the apply swap: a filter GET with HX-Request.
        html = self.client.get(
            reverse("admin-users") + f"?rol={self.beheerder.id}", headers={"hx-request": "true"}
        ).content.decode()
        assert 'data-wies-dismiss="filter"' in html
        # The filter panel travels along OOB so the sheet shows the new counts.
        assert 'hx-swap-oob="outerHTML:#filter-panel"' in html


class UserFilterFlowTest(UserFilterRenderTest):
    def test_filter_swap_returns_results_with_oob_sheet(self):
        self.client.force_login(self.admin)
        html = self.client.get(
            reverse("admin-users") + f"?rol={self.beheerder.id}", headers={"hx-request": "true"}
        ).content.decode()
        # The results fragment comes back with the filter panel as an OOB swap.
        assert 'id="results"' in html
        assert 'hx-swap-oob="outerHTML:#filter-panel"' in html
        assert 'id="filter-form"' in html

    def test_role_filter_is_multiselect(self):
        # Two roles at once must work (getlist).
        other = Group.objects.create(name="Consultant")
        u2 = User.objects.create_user(email="c2@rijksoverheid.nl", first_name="C2", last_name="T")
        u2.groups.add(other)
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("admin-users") + f"?rol={self.beheerder.id}&rol={other.id}")
        assert resp.status_code == 200


class UserFilterSlotTest(UserFilterRenderTest):
    def test_sheet_filter_panel_has_no_sidebar_slot(self):
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        # Inside the sheet the filter panel must not carry slot="sidebar".
        panel = html.split('id="filter-panel"')[1].split(">")[0]
        assert 'slot="sidebar"' not in panel, panel
