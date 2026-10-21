"""Contact person and remark on an assignment: read and written by Business Managers only."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Event, Placement, Service
from wies.core.tests.role_helpers import STAFF_EMAIL, make_bdm_user, make_staff_user

User = get_user_model()

CONTACT = "Jan de Vries"
NOTE = "Budget nog niet rond"


class AssignmentBmFieldsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner_user = make_bdm_user(email="owner@rijksoverheid.nl", name="Owner")
        # A Business Manager who does not own this assignment.
        self.bdm_user = make_bdm_user(email="bdm@rijksoverheid.nl", name="Other Bdm")
        self.assignment = Assignment.objects.create(
            name="Opdracht",
            source="wies",
            owner=self.owner_user.colleague,
            start_date=date(2026, 1, 1),
            end_date=date(2099, 12, 31),
            contact_person=CONTACT,
            internal_note=NOTE,
        )

        self.consultant_user = User.objects.create_user(email="consultant@rijksoverheid.nl")
        consultant = Colleague.objects.create(
            name="Consultant", email=self.consultant_user.email, source="wies", user=self.consultant_user
        )
        service = Service.objects.create(description="Rol", assignment=self.assignment, source="wies")
        Placement.objects.create(colleague=consultant, service=service)

        self.beheerder_user = User.objects.create_user(email="beheerder@rijksoverheid.nl")
        self.beheerder_user.user_permissions.add(Permission.objects.get(codename="change_assignment"))

    def _panel(self, user):
        self.client.force_login(user)
        response = self.client.get(
            f"/opdrachten/?opdracht={self.assignment.public_id}",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 200
        return response.content.decode()

    def _edit_sheet(self, user):
        self.client.force_login(user)
        response = self.client.get(
            f"/opdrachten/?opdracht={self.assignment.public_id}&bewerken=1",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 200
        return response.content.decode()

    def _timeline(self, user):
        Event.objects.create(
            user=self.owner_user,
            user_email=self.owner_user.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context={"field_name": "internal_note", "field_label": "Opmerking", "old_value": "", "new_value": NOTE},
        )
        self.client.force_login(user)
        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.public_id]))
        assert response.status_code == 200
        return response.content.decode()

    def _save(self, user, data):
        self.client.force_login(user)
        url = reverse("assignment-edit", args=[self.assignment.public_id])
        return self.client.post(url, {**data, "terug_url": f"/opdrachten/?opdracht={self.assignment.public_id}"})

    def test_bdm_sees_both_fields_marked_as_bm_only(self):
        body = self._panel(self.bdm_user)
        assert CONTACT in body
        assert NOTE in body
        assert "Alleen zichtbaar voor de Business Managers" in body

    def test_placed_consultant_does_not_see_them(self):
        body = self._panel(self.consultant_user)
        assert CONTACT not in body
        assert NOTE not in body

    def test_beheerder_does_not_see_them(self):
        body = self._panel(self.beheerder_user)
        assert CONTACT not in body
        assert NOTE not in body

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_does_not_see_them(self):
        body = self._panel(make_staff_user())
        assert CONTACT not in body
        assert NOTE not in body

    def test_bdm_who_is_not_the_owner_can_save_them(self):
        response = self._save(self.bdm_user, {"contact_person": "Piet", "internal_note": "Nieuw"})
        assert response.status_code == 204
        self.assignment.refresh_from_db()
        assert self.assignment.contact_person == "Piet"
        assert self.assignment.internal_note == "Nieuw"
        assert self.assignment.name == "Opdracht"

    def test_owner_edit_sheet_offers_them(self):
        body = self._edit_sheet(self.owner_user)
        assert 'name="contact_person"' in body
        assert 'name="internal_note"' in body

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_edit_sheet_leaves_them_out(self):
        """Staff may edit the rest of the assignment, but not these two."""
        body = self._edit_sheet(make_staff_user())
        assert 'name="name"' in body
        assert 'name="contact_person"' not in body
        assert 'name="internal_note"' not in body

    def test_placed_consultant_cannot_save_them(self):
        self.client.force_login(self.consultant_user)
        url = reverse("assignment-edit", args=[self.assignment.public_id]) + "?veld=internal_note"
        response = self.client.post(url, {"internal_note": "Gehackt"})
        assert response.status_code == 403
        self.assignment.refresh_from_db()
        assert self.assignment.internal_note == NOTE

    def test_inline_edit_endpoint_does_not_leak_the_value(self):
        self.client.force_login(self.consultant_user)
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "internal_note"])
        response = self.client.get(url + "?cancel=1")
        assert NOTE not in response.content.decode()

    def test_bdm_cannot_edit_them_on_an_external_assignment(self):
        self.assignment.source = "otys_iir"
        self.assignment.save()
        response = self._save(self.bdm_user, {"internal_note": "Nieuw"})
        assert response.status_code == 403

    def test_timeline_shows_the_change_to_a_bdm(self):
        assert NOTE in self._timeline(self.bdm_user)

    def test_timeline_hides_the_change_from_others(self):
        assert NOTE not in self._timeline(self.consultant_user)
        assert "opmerking" not in self._timeline(self.beheerder_user)
