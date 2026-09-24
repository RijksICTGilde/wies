"""Role tag in the user list and the filter sheet (rol/merk/labels) — #544."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import SUBGROEP_CATEGORY, Colleague, Label, LabelCategory, Suborganization
from wies.core.roles import (
    ROLE_BDM,
    ROLE_CONSULTANT,
    ROLE_OFFICE_ASSISTANT,
    role_label,
)

User = get_user_model()


class UserFilterFixture:
    """One admin, one merk and one beheerder-colleague, for the render tests below.

    A plain mixin, not a TestCase: inheriting from a TestCase would make pytest
    collect the parent's tests again under every child class.
    """

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(email="a@rijksoverheid.nl", first_name="A", last_name="Admin")
        self.admin.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.merk = Suborganization.objects.create(name="Merk A")
        self.office_assistant, _ = Group.objects.get_or_create(name=ROLE_OFFICE_ASSISTANT)
        u = User.objects.create_user(email="c@rijksoverheid.nl", first_name="Cor", last_name="Consultant")
        u.groups.add(self.office_assistant)
        Colleague.objects.create(
            user=u, name="Cor Consultant", email="c@rijksoverheid.nl", source="wies", suborganization=self.merk
        )


class UserFilterRenderTest(UserFilterFixture, TestCase):
    def test_row_shows_role_tag(self):
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        assert f'text="{role_label(ROLE_OFFICE_ASSISTANT)}"' in html
        assert f'text="{ROLE_OFFICE_ASSISTANT}"' not in html

    def test_filter_sheet_renders_role_and_merk(self):
        # The sheet lives in the page itself: its #filter-form drives the search
        # box and the chips, so it must exist before the sheet is opened.
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        assert "user-filter-sheet" in html
        assert 'id="filter-form"' in html
        assert role_label(ROLE_OFFICE_ASSISTANT) in html  # role option, by label
        assert "Merk A" in html  # merk option
        assert 'name="rol"' in html
        assert 'name="merk"' in html

    def test_role_filter_lists_the_roles_by_label(self):
        """The full list behind "Meer..." is the one the view builds: sorted on
        ``Group.name`` it would open with ``bdm``, which is no reader's A-Z."""
        for key in (ROLE_BDM, ROLE_CONSULTANT):
            Group.objects.get_or_create(name=key)
        self.client.force_login(self.admin)

        html = self.client.get(
            reverse("admin-users") + "?filter_modal=rol", headers={"hx-request": "true"}
        ).content.decode()

        # One per option row; the template lowercases it for the search box.
        assert re.findall(r'data-option-label="([^"]*)"', html) == [
            role_label(ROLE_BDM).lower(),
            role_label(ROLE_CONSULTANT).lower(),
            role_label(ROLE_OFFICE_ASSISTANT).lower(),
        ]

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
        html = self.client.get(reverse("admin-users") + f"?rol={self.office_assistant.id}").content.decode()
        assert 'data-wies-dismiss="filter"' in html
        assert 'data-filter-name="rol"' in html
        assert "data-clear-all-filters" in html


class UserFilterOobTest(UserFilterRenderTest):
    def test_apply_swap_carries_chips_and_oob_sheet(self):
        self.client.force_login(self.admin)
        # Simulate the apply swap: a filter GET with HX-Request.
        html = self.client.get(
            reverse("admin-users") + f"?rol={self.office_assistant.id}", headers={"hx-request": "true"}
        ).content.decode()
        assert 'data-wies-dismiss="filter"' in html
        # The filter panel travels along OOB so the sheet shows the new counts.
        assert 'hx-swap-oob="outerHTML:#filter-panel"' in html


class UserFilterFlowTest(UserFilterRenderTest):
    def test_filter_swap_returns_results_with_oob_sheet(self):
        self.client.force_login(self.admin)
        html = self.client.get(
            reverse("admin-users") + f"?rol={self.office_assistant.id}", headers={"hx-request": "true"}
        ).content.decode()
        # The results fragment comes back with the filter panel as an OOB swap.
        assert 'id="results"' in html
        assert 'hx-swap-oob="outerHTML:#filter-panel"' in html
        assert 'id="filter-form"' in html

    def test_role_filter_is_multiselect(self):
        # Two roles at once must work (getlist).
        other, _ = Group.objects.get_or_create(name=ROLE_CONSULTANT)
        u2 = User.objects.create_user(email="c2@rijksoverheid.nl", first_name="C2", last_name="T")
        u2.groups.add(other)
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("admin-users") + f"?rol={self.office_assistant.id}&rol={other.id}")
        assert resp.status_code == 200


class UserFilterSlotTest(UserFilterRenderTest):
    def test_sheet_filter_panel_has_no_sidebar_slot(self):
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        # Inside the sheet the filter panel must not carry slot="sidebar".
        panel = html.split('id="filter-panel"')[1].split(">")[0]
        assert 'slot="sidebar"' not in panel, panel


class UserListSortTest(TestCase):
    """The toolbar sort control (#672): the order is named and can be changed."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(email="a@rijksoverheid.nl", first_name="Zed", last_name="Admin")
        self.admin.user_permissions.add(Permission.objects.get(codename="view_user"))
        User.objects.create_user(email="b@rijksoverheid.nl", first_name="Anna", last_name="Bakker")
        User.objects.create_user(email="j@rijksoverheid.nl", first_name="Mo", last_name="Jansen")
        self.client.force_login(self.admin)

    def _names_in_order(self, html: str, *names: str) -> list[str]:
        # From the list on: the signed-in admin's name is in the page header too.
        rows = html[html.index('id="user-table"') :]
        return sorted(names, key=rows.index)

    def test_default_order_is_last_name_and_says_so(self):
        html = self.client.get(reverse("admin-users")).content.decode()
        assert self._names_in_order(html, "Admin", "Bakker", "Jansen") == ["Admin", "Bakker", "Jansen"]
        assert 'id="sort-control"' in html
        assert 'text="Achternaam (A-Z)"' in html

    def test_order_param_reverses_last_name(self):
        html = self.client.get(reverse("admin-users") + "?order=-last_name").content.decode()
        assert self._names_in_order(html, "Admin", "Bakker", "Jansen") == ["Jansen", "Bakker", "Admin"]
        assert 'text="Achternaam (Z-A)"' in html
        # The filter form carries the order along, so a filter change keeps it.
        assert 'name="order"' in html
        assert 'value="-last_name"' in html

    def test_sort_links_drop_the_page_number(self):
        # Sorting from a paged URL must start the new order at page 1: the lists
        # page on "pagina", which the sort links have to drop along with "page".
        html = self.client.get(reverse("admin-users") + "?pagina=1&zoek=an").content.decode()
        control = html[html.index('id="sort-control"') :].split("</nldd-menu>")[0]
        assert "pagina=" not in control
        assert "zoek=an" in control
        assert "order=-last_name" in control

    def test_tussenvoegsel_sorts_on_the_name_proper(self):
        # "de Wit" stands under the W, and case does not count.
        User.objects.create_user(email="w@rijksoverheid.nl", first_name="Piet", last_name="de Wit")
        User.objects.create_user(email="d@rijksoverheid.nl", first_name="Ali", last_name="Demir")
        User.objects.create_user(email="h@rijksoverheid.nl", first_name="Kim", last_name="hendriks")
        User.objects.create_user(email="v@rijksoverheid.nl", first_name="Ans", last_name="In 't Veld")
        html = self.client.get(reverse("admin-users")).content.decode()
        assert self._names_in_order(html, "Demir", "de Wit", "hendriks", "Veld", "Jansen") == [
            "Demir",
            "hendriks",
            "Jansen",
            "Veld",
            "de Wit",
        ]
        html = self.client.get(reverse("admin-users") + "?order=-last_name").content.decode()
        assert self._names_in_order(html, "Demir", "de Wit", "hendriks") == ["de Wit", "hendriks", "Demir"]

    def test_leading_space_and_apostrophe_prefixes_do_not_escape_the_strip(self):
        # A leading space (CSV import, OIDC sync), "'s" and the spaceless "d'"
        # all fall away: these sort under the W, the G and the A.
        User.objects.create_user(email="w@rijksoverheid.nl", first_name="Piet", last_name="  de Wit")
        User.objects.create_user(email="g@rijksoverheid.nl", first_name="Ada", last_name="'s Gravesande")
        User.objects.create_user(email="d@rijksoverheid.nl", first_name="Luc", last_name="d'Anjou")
        html = self.client.get(reverse("admin-users")).content.decode()
        assert self._names_in_order(html, "Admin", "Anjou", "Bakker", "Gravesande", "Jansen", "de Wit") == [
            "Admin",
            "Anjou",
            "Bakker",
            "Gravesande",
            "Jansen",
            "de Wit",
        ]

    def test_order_by_first_name(self):
        html = self.client.get(reverse("admin-users") + "?order=first_name").content.decode()
        assert self._names_in_order(html, "Zed", "Anna", "Mo") == ["Anna", "Mo", "Zed"]

    def test_order_by_date_joined(self):
        # Newest first: the users of setUp were created admin, Bakker, Jansen.
        html = self.client.get(reverse("admin-users") + "?order=-date_joined").content.decode()
        assert self._names_in_order(html, "Admin", "Bakker", "Jansen") == ["Jansen", "Bakker", "Admin"]
        assert 'text="Toegevoegd (nieuwste eerst)"' in html

    def test_unknown_order_falls_back_to_default(self):
        html = self.client.get(reverse("admin-users") + "?order=email").content.decode()
        assert self._names_in_order(html, "Admin", "Bakker", "Jansen") == ["Admin", "Bakker", "Jansen"]
        assert 'text="Achternaam (A-Z)"' in html
        assert 'name="order"' not in html

    def test_sort_swap_carries_sort_control_oob(self):
        # The toolbar does not re-render on a swap, so the control travels OOB
        # to show the new order on the button.
        html = self.client.get(
            reverse("admin-users") + "?order=-last_name", headers={"hx-request": "true"}
        ).content.decode()
        assert 'id="sort-control" slot="end" priority="-2" hx-swap-oob="outerHTML"' in html


class UserRowProfileTest(UserFilterFixture, TestCase):
    """Merk and subgroep are visible on the row itself (#672)."""

    def test_row_shows_merk_and_subgroep_after_email(self):
        subgroep = LabelCategory.objects.create(name=SUBGROEP_CATEGORY, color="#0066CC")
        expertise = LabelCategory.objects.create(name="Expertise", color="#00CC66")
        colleague = Colleague.objects.get(email="c@rijksoverheid.nl")
        colleague.labels.add(
            Label.objects.create(name="AI", category=subgroep),
            Label.objects.create(name="Cloud", category=expertise),
        )
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        # Merk first, then the subgroep; other categories stay in the panel and the filters.
        assert 'supporting-text="c@rijksoverheid.nl · Merk A · AI"' in html

    def test_row_without_colleague_shows_only_email(self):
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        assert 'supporting-text="a@rijksoverheid.nl"' in html
