"""Tests for the client (opdrachtgever) menu in the assignment panel.

The client renders as a breadcrumb (Fin > DGBD > Datafundamenten) and "Bekijk
opdrachten" opens a submenu with one item per level, so you can filter on any
ancestor instead of only the leaf.
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
        # One "Bekijk opdrachten" opener with a submenu item per level.
        assert "Bekijk opdrachten</nldd-menu-item>" not in body  # the opener is not plain text
        assert 'text="Bekijk opdrachten"' in body
        assert 'text="Datafundamenten &amp; Analytics"' in body
        assert 'text="DGBD"' in body
        assert 'text="Fin"' in body
        # The opener nests a submenu.
        assert "<nldd-menu>" in body
        # The old single action is gone.
        assert "Bekijk alle opdrachten" not in body

    def test_each_level_links_to_its_own_org_filter(self):
        body = self._panel_body()
        # Every level filters on its own public_id, not just the leaf.
        assert f"?org={self.dgbd.public_id}" in body
        assert f"?org={self.fin.public_id}" in body
        # The leaf holds no assignments deeper in its subtree, so it filters on
        # org rather than org_self.
        assert f"?org={self.leaf.public_id}" in body

    def test_leaf_with_deeper_assignments_filters_on_org_self(self):
        # With an assignment below the node, the node stands for "this unit
        # itself" and filters via org_self.
        deeper = OrganizationUnit.objects.create(name="Team Data", parent=self.leaf)
        other = Assignment.objects.create(
            name="Ander", source="wies", start_date=date(2026, 1, 1), end_date=date(2026, 6, 1)
        )
        AssignmentOrganizationUnit.objects.create(assignment=other, organization=deeper, role="PRIMARY")

        body = self._panel_body()
        assert f"?org_self={self.leaf.public_id}" in body


class AssignmentPanelSecondOrgTest(TestCase):
    """Each client row of an assignment carries its own "Bekijk opdrachten" submenu.

    Regression: the menu only knew the first row, leaving the involved party
    unreachable.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="kijker@rijksoverheid.nl")
        self.client.force_login(self.user)

        # Two branches: a primary client under DGBD, an involved one under DGABD.
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
        # DGABD sits only in the involved party's path, not the primary one's.
        assert f"?org={self.dgabd.public_id}" in body
        assert f"?org={self.involved.public_id}" in body
        assert f"?org={self.dgbd.public_id}" in body
        assert f"?org={self.primary.public_id}" in body
        assert body.count('text="Bekijk opdrachten"') == 2

    def test_each_menu_is_named_after_its_own_organization(self):
        # Two stacked ⋯ menus must be tellable apart.
        body = self._panel_body()
        assert 'text="Acties voor opdrachtgever Datafundamenten"' in body
        assert 'text="Acties voor opdrachtgever Team Inkoop"' in body

    def test_menus_hold_no_edit_action(self):
        # Editing runs through "Gegevens bewerken" at the top; a per-row edit
        # would leave the assignment name unreachable, as it is the heading.
        User.objects.filter(pk=self.user.pk).update(is_superuser=True, is_staff=True)
        body = self._panel_body()
        assert "Opdrachtgever wijzigen" not in body
        assert "&veld=organizations" not in body
        # What remains is the non-editing action, on every row.
        assert body.count('text="Bekijk opdrachten"') == 2

    def test_single_organization_shows_no_role_suffix(self):
        # With a single client, "(primair)" says nothing.
        AssignmentOrganizationUnit.objects.filter(assignment=self.assignment, role="INVOLVED").delete()
        body = self._panel_body()
        assert "(primair)" not in body
        assert "(betrokken)" not in body
