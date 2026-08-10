"""Tests voor de één-veld-variant van ``assignment_edit_view``.

Het ⋯-menu van een gegevensrij bewerkt via ``?veld=<naam>`` alleen dat veld;
het potlood bewerkt alles. Deze test bewaakt dat een één-veld-save de overige
velden niet aanraakt (anders zou een lege waarde in het weggelaten veld die
kolom wissen).
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
)

User = get_user_model()


class AssignmentEditSingleFieldTest(TestCase):
    def setUp(self):
        self.client = Client()
        # owner en other zijn allebei BDM, zodat beide een geldige keuze zijn in
        # het Business Manager-veld (choices = _bdm_queryset).
        bdm_group, _ = Group.objects.get_or_create(name="Business Development Manager")

        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl")
        self.owner_user.groups.add(bdm_group)
        self.client.force_login(self.owner_user)
        self.owner = Colleague.objects.get(user=self.owner_user)

        self.other_user = User.objects.create_user(email="other@rijksoverheid.nl")
        self.other_user.groups.add(bdm_group)
        self.client.force_login(self.other_user)
        self.other = Colleague.objects.get(user=self.other_user)
        self.client.force_login(self.owner_user)

        self.assignment = Assignment.objects.create(
            name="Originele naam",
            source="wies",
            owner=self.owner,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        org = OrganizationUnit.objects.create(name="Rijkswaterstaat", label="RWS")
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=org, role="PRIMARY")

    def test_owner_save_leaves_name_and_period_untouched(self):
        url = reverse("assignment-edit", args=[self.assignment.public_id]) + "?veld=owner"
        response = self.client.post(
            url,
            {"owner": str(self.other.public_id), "terug_url": f"/opdrachten/?opdracht={self.assignment.public_id}"},
        )
        assert response.status_code == 204
        assert "HX-Location" in response

        self.assignment.refresh_from_db()
        # Alleen de BM verandert; naam en periode blijven staan.
        assert self.assignment.owner_id == self.other.id
        assert self.assignment.name == "Originele naam"
        assert self.assignment.start_date == date(2026, 1, 1)
        assert self.assignment.end_date == date(2026, 12, 31)

    def test_panel_menu_links_carry_the_field(self):
        response = self.client.get(
            f"/opdrachten/?opdracht={self.assignment.public_id}",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        body = response.content.decode()
        assert "&veld=owner" in body
        assert "&veld=period" in body
        assert "&veld=organizations" in body

    def test_forbidden_without_edit_rights(self):
        self.client.force_login(self.other_user)
        url = reverse("assignment-edit", args=[self.assignment.public_id]) + "?veld=owner"
        response = self.client.post(url, {"owner": str(self.owner.public_id)})
        assert response.status_code == 403
