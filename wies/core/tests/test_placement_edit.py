"""Tests for ``placement_edit_view`` (POST /plaatsing/<public_id>/bewerken/).

Regression: untested, this view called the non-existent
``_emit_placement_change_on_assignment`` and 500'd on every save (#393).
"""

import uuid
from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import (
    Assignment,
    Colleague,
    Event,
    Placement,
    Service,
    Skill,
)

User = get_user_model()


class PlacementEditViewTest(TestCase):
    """POST-only save of the combined placement edit form.

    Edit rights on a Placement chain to UPDATE on the parent assignment, which
    for a wies assignment is its BM-owner (see permissions.py).
    """

    def setUp(self):
        self.client = Client()

        # The Colleague is created on login (user_logged_in signal), so log in
        # here to fetch it as the assignment owner.
        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl")
        self.client.force_login(self.owner_user)
        self.owner = Colleague.objects.get(user=self.owner_user)

        self.other_user = User.objects.create_user(email="outsider@rijksoverheid.nl")

        self.skill = Skill.objects.create(name="Python Developer")
        self.assignment = Assignment.objects.create(
            name="Test Opdracht",
            source="wies",
            owner=self.owner,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.service = Service.objects.create(
            assignment=self.assignment,
            skill=self.skill,
            description="Bouwt dingen",
            source="wies",
        )
        # Starts on the SERVICE period; the edit switches to a deviating one,
        # which must trigger the audit mirror.
        self.placement = Placement.objects.create(
            colleague=self.owner,
            service=self.service,
            period_source=Placement.SERVICE,
            source="wies",
        )
        self.url = reverse("placement-edit", args=[self.placement.public_id])

    def _valid_payload(self, **overrides):
        """Returns a valid POST payload for the combined Service+Placement form."""
        payload = {
            "skill": str(self.skill.public_id),
            "description": "Bouwt dingen",
            "period_source": Placement.PLACEMENT,
            "specific_start_date": "2026-03-01",
            "specific_end_date": "2026-06-30",
            "terug_url": f"/?plaatsing={self.placement.public_id}",
        }
        payload.update(overrides)
        return payload

    def test_happy_path_saves_and_returns_hx_location(self):
        """Regression for the NameError: a valid POST returns 204, not 500."""
        self.client.force_login(self.owner_user)

        response = self.client.post(self.url, self._valid_payload())

        assert response.status_code == 204, (
            f"Verwacht 204, kreeg {response.status_code}. Een 500 hier betekent "
            "dat _save_placement_edit een niet-bestaande functie aanroept."
        )
        assert "HX-Location" in response

        self.placement.refresh_from_db()
        assert self.placement.period_source == Placement.PLACEMENT
        assert self.placement.specific_start_date == date(2026, 3, 1)
        assert self.placement.specific_end_date == date(2026, 6, 30)

    def test_happy_path_records_team_event_on_parent_assignment(self):
        """The audit mirror records the change as a "Team" event on the assignment."""
        self.client.force_login(self.owner_user)

        self.client.post(self.url, self._valid_payload())

        events = Event.objects.filter(
            object_type="Assignment",
            object_id=self.assignment.id,
            action="update",
        )
        team_events = [e for e in events if e.context.get("field_label") == "Team"]
        assert len(team_events) == 1, f"Verwacht één Team-event, kreeg {len(team_events)}"
        assert team_events[0].context["field_name"] == "services"

    def test_forbidden_for_user_without_edit_rights(self):
        self.client.force_login(self.other_user)

        response = self.client.post(self.url, self._valid_payload())

        assert response.status_code == 403
        self.placement.refresh_from_db()
        assert self.placement.period_source == Placement.SERVICE

    def test_get_not_allowed(self):
        """GET returns 405, so it can never show an empty form that wipes fields on save."""
        self.client.force_login(self.owner_user)

        response = self.client.get(self.url)

        assert response.status_code == 405

    def test_unknown_pk_returns_404(self):
        self.client.force_login(self.owner_user)

        response = self.client.post(reverse("placement-edit", args=[uuid.uuid4()]), self._valid_payload())

        assert response.status_code == 404
