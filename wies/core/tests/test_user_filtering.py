"""Rol-tag in de gebruikerslijst en de filtersheet (rol/merk/labels) — #544."""

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
        assert 'text="Beheerder"' in html  # rol-tag in de rij

    def test_filter_sheet_renders_role_and_merk(self):
        # De sheet staat in de pagina zelf: #filter-form erin stuurt het zoekveld
        # en de chips aan, dus het mag niet pas na openen bestaan.
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        assert "user-filter-sheet" in html
        assert 'id="filter-form"' in html
        assert "Beheerder" in html  # rol-optie
        assert "Merk A" in html  # merk-optie
        assert 'name="rol"' in html
        assert 'name="merk"' in html

    def test_filter_sheet_collapses_long_group_behind_meer(self):
        # Genoeg merken (> top_n=3) zodat de rest achter "Meer…" valt.
        for i in range(6):
            s = Suborganization.objects.create(name=f"Extra Merk {i}")
            u = User.objects.create_user(email=f"x{i}@rijksoverheid.nl", first_name=f"X{i}", last_name="Test")
            Colleague.objects.create(
                user=u, name=f"X{i} Test", email=f"x{i}@rijksoverheid.nl", source="wies", suborganization=s
            )
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users")).content.decode()
        # Gedeeld filter_sidebar-patroon: top-3 + een "Meer..."-rij die de
        # filter_options_modal opent.
        assert "Meer..." in html
        assert "filter_modal=merk" in html

    def test_active_filter_renders_chip(self):
        # De chipstrip verving de teller op de knop: die zei hoeveel, niet wat.
        self.client.force_login(self.admin)
        html = self.client.get(reverse("admin-users") + f"?rol={self.beheerder.id}").content.decode()
        assert 'data-wies-dismiss="filter"' in html
        assert 'data-filter-name="rol"' in html
        assert "data-clear-all-filters" in html


class UserFilterOobTest(UserFilterRenderTest):
    def test_apply_swap_carries_chips_and_oob_sheet(self):
        self.client.force_login(self.admin)
        # Simuleer de apply-swap: filter-GET met HX-Request → #user-content fragment.
        html = self.client.get(
            reverse("admin-users") + f"?rol={self.beheerder.id}", headers={"hx-request": "true"}
        ).content.decode()
        assert 'data-wies-dismiss="filter"' in html
        # Het filterpaneel reist OOB mee, zodat de sheet de nieuwe counts toont.
        assert 'hx-swap-oob="outerHTML:#filter-panel"' in html


class UserFilterFlowTest(UserFilterRenderTest):
    def test_filter_swap_returns_results_with_oob_sheet(self):
        self.client.force_login(self.admin)
        html = self.client.get(
            reverse("admin-users") + f"?rol={self.beheerder.id}", headers={"hx-request": "true"}
        ).content.decode()
        # #results-fragment terug, met het filterpaneel als OOB (counts bijgewerkt).
        assert 'id="results"' in html
        assert 'hx-swap-oob="outerHTML:#filter-panel"' in html
        # Rol-checkbox staat aangevinkt in de meegeswapte sheet.
        assert 'id="filter-form"' in html

    def test_role_filter_is_multiselect(self):
        # Twee rollen tegelijk moet werken (getlist).
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
        # In de sheet mag het filterpaneel GEEN slot="sidebar" dragen.
        panel = html.split('id="filter-panel"')[1].split(">")[0]
        assert 'slot="sidebar"' not in panel, panel
