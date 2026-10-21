"""Contact person and remark on an assignment: read and written by Business Managers only."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Event, Placement, Service
from wies.core.roles import ROLE_USER_ADMIN
from wies.core.tests.role_helpers import (
    STAFF_EMAIL,
    make_business_manager_user,
    make_other_business_manager_user,
    make_staff_user,
)

User = get_user_model()

CONTACT = "Jan de Vries"
NOTE = "Budget nog niet rond"


class AssignmentBmFieldsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner_user = make_business_manager_user()
        # A Business Manager who does not own this assignment.
        self.business_manager_user = make_other_business_manager_user()
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

        self.user_admin = User.objects.create_user(email="gebruikersbeheerder@rijksoverheid.nl")
        self.user_admin.groups.add(Group.objects.get_or_create(name=ROLE_USER_ADMIN)[0])

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

    def _timeline(self, user, context=None):
        Event.objects.create(
            user=self.owner_user,
            user_email=self.owner_user.email,
            object_type="Assignment",
            action="update",
            source="user",
            object_id=self.assignment.id,
            context=context
            or {"field_name": "internal_note", "field_label": "Opmerking", "old_value": "", "new_value": NOTE},
        )
        self.client.force_login(user)
        response = self.client.get(reverse("assignment-events-partial", args=[self.assignment.public_id]))
        assert response.status_code == 200
        return response.content.decode()

    def _save(self, user, field, value):
        """One field through the edit sheet, as its row menu opens it."""
        self.client.force_login(user)
        url = reverse("assignment-edit", args=[self.assignment.public_id]) + f"?veld={field}"
        return self.client.post(url, {field: value, "terug_url": f"/opdrachten/?opdracht={self.assignment.public_id}"})

    def test_business_manager_sees_both_fields_marked_as_business_manager_only(self):
        body = self._panel(self.business_manager_user)
        assert CONTACT in body
        assert NOTE in body
        assert "Alleen zichtbaar voor de Business Managers" in body

    def test_placed_consultant_does_not_see_them(self):
        body = self._panel(self.consultant_user)
        assert CONTACT not in body
        assert NOTE not in body

    def test_user_admin_does_not_see_them(self):
        body = self._panel(self.user_admin)
        assert CONTACT not in body
        assert NOTE not in body

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_does_not_see_them(self):
        body = self._panel(make_staff_user())
        assert CONTACT not in body
        assert NOTE not in body

    def test_business_manager_does_not_see_them_on_an_external_assignment(self):
        """Nobody can fill them in there, so the rows would stay empty for good."""
        self.assignment.source = "otys_iir"
        self.assignment.save()
        body = self._panel(self.business_manager_user)
        assert CONTACT not in body
        assert "Contactpersoon" not in body

    def test_business_manager_who_is_not_the_owner_can_save_them(self):
        assert self._save(self.business_manager_user, "contact_person", "Piet").status_code == 204
        assert self._save(self.business_manager_user, "internal_note", "Nieuw").status_code == 204
        self.assignment.refresh_from_db()
        assert self.assignment.contact_person == "Piet"
        assert self.assignment.internal_note == "Nieuw"
        assert self.assignment.name == "Opdracht"

    def test_both_are_capped_at_200_characters(self):
        for field in ("contact_person", "internal_note"):
            response = self._save(self.business_manager_user, field, "a" * 201)
            assert response.status_code == 200
            assert "Gebruik maximaal 200 tekens. Het zijn er nu 201." in response.content.decode()
        self.assignment.refresh_from_db()
        assert self.assignment.contact_person == CONTACT
        assert self.assignment.internal_note == NOTE

    def test_owner_edit_sheet_offers_them(self):
        body = self._edit_sheet(self.owner_user)
        assert 'name="contact_person"' in body
        assert 'name="internal_note"' in body
        assert "Opdracht wijzigen" in body
        assert "Alleen zichtbaar voor de Business Managers." in body

    def test_placed_consultant_cannot_save_them(self):
        assert self._save(self.consultant_user, "internal_note", "Gehackt").status_code == 403
        self.assignment.refresh_from_db()
        assert self.assignment.internal_note == NOTE

    def test_inline_edit_endpoint_does_not_leak_the_value(self):
        self.client.force_login(self.consultant_user)
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "internal_note"])
        response = self.client.get(url + "?cancel=1")
        assert NOTE not in response.content.decode()

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_inline_edit_endpoint_does_not_leak_to_the_beheer_roles(self):
        """Neither the Gebruikersbeheerder nor the Applicatiebeheerder plans."""
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "internal_note"])
        for user in (self.user_admin, make_staff_user()):
            self.client.force_login(user)
            for query in ("", "?edit=1", "?cancel=1"):
                assert NOTE not in self.client.get(url + query).content.decode()

    def test_business_manager_cannot_edit_them_on_an_external_assignment(self):
        self.assignment.source = "otys_iir"
        self.assignment.save()
        assert self._save(self.business_manager_user, "internal_note", "Nieuw").status_code == 403

    def test_timeline_shows_the_change_to_a_business_manager(self):
        body = self._timeline(self.business_manager_user)
        assert NOTE in body
        assert "Beperkt zichtbaar" in body

    def test_timeline_says_a_cleared_contact_person_was_removed(self):
        context = {
            "field_name": "contact_person",
            "field_label": "Contactpersoon",
            "old_value": CONTACT,
            "new_value": "",
        }
        assert "heeft de contactpersoon verwijderd." in self._timeline(self.business_manager_user, context)

    def test_timeline_hides_the_values_of_a_field_no_longer_declared(self):
        """Without a declaration there is no read rule left to check."""
        context = {"field_name": "removed_field", "field_label": "Verlenging", "old_value": "", "new_value": NOTE}
        body = self._timeline(self.consultant_user, context)
        assert "heeft de verlenging gewijzigd." in body
        assert NOTE not in body

    def test_timeline_hides_the_change_from_others(self):
        assert NOTE not in self._timeline(self.consultant_user)
        assert "opmerking" not in self._timeline(self.user_admin)
