"""Tests voor het opdrachtgever-menu in het opdrachtpaneel.

De opdrachtgever staat als breadcrumb (Fin > DGBD > Datafundamenten). Het
acties-menu bood eerst een enkele "Bekijk alle opdrachten" die alleen op de
laagste node filterde -- juist de eenheid die de minste andere opdrachten
deelt. Nu opent "Bekijk opdrachten" een submenu met een item per niveau, zodat
je ook op DGBD of Fin kunt filteren.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
)

User = get_user_model()


class AssignmentPanelOrgMenuTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="kijker@rijksoverheid.nl")
        self.client.force_login(self.user)
        colleague = Colleague.objects.get(user=self.user)

        # Fin > DGBD > Datafundamenten & Analytics
        self.fin = OrganizationUnit.objects.create(name="Ministerie van Financiën", abbreviations=["Fin"])
        self.dgbd = OrganizationUnit.objects.create(name="DG Begroting", abbreviations=["DGBD"], parent=self.fin)
        self.leaf = OrganizationUnit.objects.create(
            name="Datafundamenten & Analytics", label="Datafundamenten & Analytics", parent=self.dgbd
        )

        self.assignment = Assignment.objects.create(
            name="Informatiebeveiliging Portaal",
            source="wies",
            owner=colleague,
            start_date=date(2026, 8, 4),
            end_date=date(2027, 4, 10),
        )
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=self.leaf, role="PRIMARY")

    def _panel_body(self):
        response = self.client.get(
            f"/opdrachten/?opdracht={self.assignment.public_id}",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 200
        return response.content.decode()

    def test_menu_has_a_submenu_item_per_hierarchy_level(self):
        body = self._panel_body()
        # Eén "Bekijk opdrachten"-opener met een submenu-item per niveau.
        assert "Bekijk opdrachten</nldd-menu-item>" not in body  # opener is geen platte tekst
        assert 'text="Bekijk opdrachten"' in body
        assert 'text="Datafundamenten &amp; Analytics"' in body
        assert 'text="DGBD"' in body
        assert 'text="Fin"' in body
        # De opener nest een submenu.
        assert "<nldd-menu>" in body
        # De oude enkele actie bestaat niet meer.
        assert "Bekijk alle opdrachten" not in body

    def test_each_level_links_to_its_own_org_filter(self):
        body = self._panel_body()
        # Elk niveau filtert op zijn eigen public_id, niet alleen de laagste.
        assert f"?org={self.dgbd.public_id}" in body
        assert f"?org={self.fin.public_id}" in body
        # De laagste node draagt geen andere opdrachten in zijn subtree, dus
        # filtert 'm direct op org (niet org_self).
        assert f"?org={self.leaf.public_id}" in body

    def test_leaf_with_deeper_assignments_filters_on_org_self(self):
        # Hangt er een opdracht ónder de gekozen node, dan staat die node voor
        # "deze eenheid zelf" en filtert 'm via org_self (subtree hoort erbij).
        deeper = OrganizationUnit.objects.create(name="Team Data", parent=self.leaf)
        other = Assignment.objects.create(
            name="Ander", source="wies", start_date=date(2026, 1, 1), end_date=date(2026, 6, 1)
        )
        AssignmentOrganizationUnit.objects.create(assignment=other, organization=deeper, role="PRIMARY")

        body = self._panel_body()
        assert f"?org_self={self.leaf.public_id}" in body


class AssignmentPanelSecondOrgTest(TestCase):
    """Een opdracht met een primaire opdrachtgever én een betrokken partij.

    Beide krijgen een eigen rij met een eigen "Bekijk opdrachten"-submenu; de
    tweede was eerder onbereikbaar omdat het menu alleen de eerste rij kende.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="kijker@rijksoverheid.nl")
        self.client.force_login(self.user)

        # Fin > DGBD > Datafundamenten (primair) en Fin > DGABD > Inkoop (betrokken)
        self.fin = OrganizationUnit.objects.create(name="Ministerie van Financiën", abbreviations=["Fin"])
        self.dgbd = OrganizationUnit.objects.create(name="DG Begroting", abbreviations=["DGBD"], parent=self.fin)
        self.primary = OrganizationUnit.objects.create(
            name="Datafundamenten", label="Datafundamenten", parent=self.dgbd
        )
        self.dgabd = OrganizationUnit.objects.create(
            name="DG Bedrijfsvoering", abbreviations=["DGABD"], parent=self.fin
        )
        self.involved = OrganizationUnit.objects.create(name="Team Inkoop", label="Team Inkoop", parent=self.dgabd)

        self.assignment = Assignment.objects.create(
            name="Informatiebeveiliging Portaal",
            source="wies",
            start_date=date(2026, 8, 4),
            end_date=date(2027, 4, 10),
        )
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=self.primary, role="PRIMARY")
        AssignmentOrganizationUnit.objects.create(
            assignment=self.assignment, organization=self.involved, role="INVOLVED"
        )

    def _panel_body(self):
        response = self.client.get(
            f"/opdrachten/?opdracht={self.assignment.public_id}",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 200
        return response.content.decode()

    def test_both_organizations_are_shown_with_their_role(self):
        body = self._panel_body()
        assert "Datafundamenten" in body
        assert "Team Inkoop" in body
        assert "(primair)" in body
        assert "(betrokken)" in body

    def test_the_second_organization_has_its_own_level_menu(self):
        body = self._panel_body()
        # DGABD zit alleen in het pad van de betrokken partij, niet in dat van
        # de primaire opdrachtgever.
        assert f"?org={self.dgabd.public_id}" in body
        assert f"?org={self.involved.public_id}" in body
        assert f"?org={self.dgbd.public_id}" in body
        assert f"?org={self.primary.public_id}" in body
        assert body.count('text="Bekijk opdrachten"') == 2

    def test_each_menu_is_named_after_its_own_organization(self):
        # Twee ⋯-menu's onder elkaar moeten uit elkaar te houden zijn.
        body = self._panel_body()
        assert 'text="Acties voor opdrachtgever Datafundamenten"' in body
        assert 'text="Acties voor opdrachtgever Team Inkoop"' in body

    def test_menus_hold_no_edit_action(self):
        # Bewerken loopt via "Gegevens bewerken" bovenaan; per rij zou de
        # opdrachtnaam onbereikbaar laten, want die staat als kop en niet als rij.
        User.objects.filter(pk=self.user.pk).update(is_superuser=True, is_staff=True)
        body = self._panel_body()
        assert "Opdrachtgever wijzigen" not in body
        assert "&veld=organizations" not in body
        # Wat blijft is de niet-bewerkende actie, op elke rij.
        assert body.count('text="Bekijk opdrachten"') == 2

    def test_single_organization_shows_no_role_suffix(self):
        # Bij één opdrachtgever zegt "(primair)" niets.
        AssignmentOrganizationUnit.objects.filter(assignment=self.assignment, role="INVOLVED").delete()
        body = self._panel_body()
        assert "(primair)" not in body
        assert "(betrokken)" not in body
