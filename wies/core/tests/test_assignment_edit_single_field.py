"""Tests for the single-field variant of ``assignment_edit_view``.

Regression: ``?veld=<name>`` must save only that field, since a blank value in
an omitted field would wipe its column.
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
        # Both owner and other are BDM, so both are valid choices in the
        # Business Manager field (choices = _bdm_queryset).
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
        # Only the BM changes; name and period stay.
        assert self.assignment.owner_id == self.other.id
        assert self.assignment.name == "Originele naam"
        assert self.assignment.start_date == date(2026, 1, 1)
        assert self.assignment.end_date == date(2026, 12, 31)

    def test_panel_has_no_per_row_edit_links(self):
        """The panel offers no per-row edit.

        A per-row edit would leave the assignment name unreachable: it is the
        panel heading, not a row.
        """
        response = self.client.get(
            f"/opdrachten/?opdracht={self.assignment.public_id}",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        body = response.content.decode()
        assert "&veld=" not in body
        # The button that opens the full form is present.
        assert "bewerken=1" in body

    def test_forbidden_without_edit_rights(self):
        self.client.force_login(self.other_user)
        url = reverse("assignment-edit", args=[self.assignment.public_id]) + "?veld=owner"
        response = self.client.post(url, {"owner": str(self.owner.public_id)})
        assert response.status_code == 403


class AssignmentOwnerOutsideBdmGroupTest(TestCase):
    """The current Business Manager is a choice even outside the BDM group.

    Regression: without an option matching its ``value`` the combo box rendered
    empty and saving wiped the Business Manager.
    """

    def setUp(self):
        self.client = Client()
        Group.objects.get_or_create(name="Business Development Manager")
        # The owner is deliberately NOT in the BDM group; his edit rights come
        # from owning the assignment.
        self.owner_user = User.objects.create_user(email="sophie@rijksoverheid.nl")
        self.client.force_login(self.owner_user)
        self.owner = Colleague.objects.get(user=self.owner_user)

        self.assignment = Assignment.objects.create(
            name="Handhaving Informatiesysteem",
            source="wies",
            owner=self.owner,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        org = OrganizationUnit.objects.create(name="Defensie", label="Def")
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=org, role="PRIMARY")

    def _edit_form(self):
        response = self.client.get(
            f"/opdrachten/?opdracht={self.assignment.public_id}&bewerken=1&veld=owner",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 200
        return response.content.decode()

    def test_current_owner_is_an_option_and_preselected(self):
        body = self._edit_form()
        # The combo box `value` points at an option that actually exists.
        assert f'value="{self.owner.public_id}"' in body
        assert f'<nldd-menu-item value="{self.owner.public_id}"' in body

    def test_saving_another_field_keeps_the_owner(self):
        # The reported scenario: editing the assignment dropped the BM.
        url = reverse("assignment-edit", args=[self.assignment.public_id]) + "?veld=owner"
        response = self.client.post(
            url,
            {"owner": str(self.owner.public_id), "terug_url": f"/opdrachten/?opdracht={self.assignment.public_id}"},
        )
        assert response.status_code == 204
        self.assignment.refresh_from_db()
        assert self.assignment.owner_id == self.owner.id

    def test_choices_without_an_assignment_stay_limited_to_the_group(self):
        # On create there is no owner yet, so the list stays the group.
        from wies.core.editables.assignment import _bdm_queryset  # noqa: PLC0415 (import not at top) — test-local

        assert self.owner not in list(_bdm_queryset())
