"""Tests for ``placement_edit_view`` (POST /plaatsing/<pk>/bewerken/).

Deze view had geen enkele test, waardoor een aanroep naar een niet-bestaande
functie (``_emit_placement_change_on_assignment``) een 500 gaf bij élke
geslaagde opslag. De happy-path-test hieronder vangt die regressie: hij eist
een 204 (geen 500) én controleert dat de audit-mirror een "Team"-event op de
ouder-opdracht legt (#393).
"""

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
    """POST-only opslag van het gecombineerde plaatsing-bewerkformulier.

    Bewerkrechten op een Placement chainen naar UPDATE op de ouder-opdracht,
    en dat is de BM-owner van een wies-opdracht (zie permissions.py).
    """

    def setUp(self):
        self.client = Client()

        # De owner: een user met een gekoppelde Colleague die eigenaar van de
        # opdracht is -> heeft UPDATE op de opdracht, service en placement.
        # De Colleague wordt bij login aangemaakt (user_logged_in-signal), dus
        # loggen we hier alvast in om hem op te halen als opdracht-eigenaar.
        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl")
        self.client.force_login(self.owner_user)
        self.owner = Colleague.objects.get(user=self.owner_user)

        # Een buitenstaander zonder enige relatie tot de opdracht.
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
        # Placement die de opdrachtperiode overneemt; de edit wijzigt dit naar
        # een afwijkende periode, wat de audit-mirror moet triggeren.
        self.placement = Placement.objects.create(
            colleague=self.owner,
            service=self.service,
            period_source=Placement.SERVICE,
            source="wies",
        )
        self.url = reverse("placement-edit", args=[self.placement.pk])

    def _valid_payload(self, **overrides):
        """Een geldige POST voor het gecombineerde formulier: Service-velden
        (skill, description) plus de Placement-periodegroep."""
        payload = {
            "skill": str(self.skill.id),
            "description": "Bouwt dingen",
            "period_source": Placement.PLACEMENT,
            "specific_start_date": "2026-03-01",
            "specific_end_date": "2026-06-30",
            "terug_url": f"/?plaatsing={self.placement.id}",
        }
        payload.update(overrides)
        return payload

    def test_happy_path_saves_and_returns_hx_location(self):
        """Geldige POST door een bevoegde gebruiker: geen 500, wijziging in de
        DB, 204 met HX-Location. Dit is de regressietest voor de NameError."""
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
        """De audit-mirror legt de plaatsingswijziging als "Team"-event op de
        tijdlijn van de ouder-opdracht. Een 500 vóór de save zou dit event
        nooit aanmaken -> deze assertion vangt de regressie ook."""
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
        """Een gebruiker zonder bewerkrechten op de placement krijgt 403 en
        wijzigt niets."""
        self.client.force_login(self.other_user)

        response = self.client.post(self.url, self._valid_payload())

        assert response.status_code == 403
        self.placement.refresh_from_db()
        assert self.placement.period_source == Placement.SERVICE

    def test_get_not_allowed(self):
        """De view is POST-only (@require_POST); GET geeft 405 zodat een GET
        nooit een leeg formulier kan tonen dat bij opslaan velden wist."""
        self.client.force_login(self.owner_user)

        response = self.client.get(self.url)

        assert response.status_code == 405

    def test_unknown_pk_returns_404(self):
        self.client.force_login(self.owner_user)

        response = self.client.post(reverse("placement-edit", args=[999999]), self._valid_payload())

        assert response.status_code == 404
