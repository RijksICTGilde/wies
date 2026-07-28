"""Tests for the 'Wie zit waar?' grouping/sorting logic in PlacementListView.

Covers the ?groep= (person vs assignment view) count metric, the ?order= sort
allowlist (including the removed "skill" value), default sort per view, and the
per-view sort_options.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Placement, Service, Skill

User = get_user_model()


def _make_placement(name, assignment_name, end_offset_days, *, colleague=None, skill=None):
    """Create an active placement (visible to everyone) and return it.

    A single colleague/skill can be reused across calls to build the
    "1 person, 2 assignments" and "2 people, 1 assignment" scenarios.
    """
    today = timezone.now().date()
    if colleague is None:
        colleague = Colleague.objects.create(
            name=name,
            email=f"{name.lower().replace(' ', '.')}@test.com",
            source="wies",
        )
    if skill is None:
        skill = Skill.objects.create(name=f"Skill {assignment_name}")

    assignment = Assignment.objects.create(
        name=assignment_name,
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=end_offset_days),
        source="wies",
    )
    service = Service.objects.create(
        assignment=assignment,
        description=f"Service {assignment_name}",
        skill=skill,
        source="wies",
    )
    return Placement.objects.create(colleague=colleague, service=service, source="wies")


@pytest.mark.django_db
class TestPlacementGrouping:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")
        self.client = Client()
        self.client.force_login(self.user)

    # --- results_count metric per view -------------------------------------

    def test_count_metric_differs_from_placement_count(self):
        """person-count counts distinct colleagues; assignment-count distinct opdrachten.

        5 placements across 3 colleagues and 3 assignments, so neither count equals
        the raw placement count: person-count and assignment-count are both 3.
        The per-view dedup direction is asserted separately in the two tests below.
        """
        alice = Colleague.objects.create(name="Alice", email="alice@test.com", source="wies")
        _make_placement("Alice", "Opdracht A", 30, colleague=alice)
        _make_placement("Alice", "Opdracht B", 30, colleague=alice)

        shared_skill = Skill.objects.create(name="Shared skill")
        today = timezone.now().date()
        shared_assignment = Assignment.objects.create(
            name="Opdracht C",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=30),
            source="wies",
        )
        shared_service = Service.objects.create(
            assignment=shared_assignment, description="Shared", skill=shared_skill, source="wies"
        )
        bob = Colleague.objects.create(name="Bob", email="bob@test.com", source="wies")
        carol = Colleague.objects.create(name="Carol", email="carol@test.com", source="wies")
        Placement.objects.create(colleague=bob, service=shared_service, source="wies")
        Placement.objects.create(colleague=carol, service=shared_service, source="wies")

        # Persons: Alice, Bob, Carol = 3. Assignments: A, B, C = 3.
        # Placements: 4. To make counts differ from placement count and from each
        # other, give Alice a second placement on Opdracht C too (existing assignment).
        Placement.objects.create(colleague=alice, service=shared_service, source="wies")
        # Now persons = 3 (Alice, Bob, Carol), assignments = 3 (A, B, C), placements = 5.

        person_resp = self.client.get(reverse("home"))
        assert person_resp.status_code == 200
        assert person_resp.context_data["results_count"] == 3

        assignment_resp = self.client.get(reverse("home") + "?groep=assignment")
        assert assignment_resp.status_code == 200
        assert assignment_resp.context_data["results_count"] == 3

    def test_count_person_view_dedupes_colleague(self):
        """One colleague on 2 assignments counts as 1 person, 2 assignments."""
        alice = Colleague.objects.create(name="Alice", email="alice@test.com", source="wies")
        _make_placement("Alice", "Opdracht A", 30, colleague=alice)
        _make_placement("Alice", "Opdracht B", 30, colleague=alice)

        person_resp = self.client.get(reverse("home"))
        assert person_resp.context_data["results_count"] == 1

        assignment_resp = self.client.get(reverse("home") + "?groep=assignment")
        assert assignment_resp.context_data["results_count"] == 2

    def test_count_assignment_view_dedupes_assignment(self):
        """Two colleagues on 1 assignment count as 2 persons, 1 assignment."""
        shared_skill = Skill.objects.create(name="Shared skill")
        today = timezone.now().date()
        assignment = Assignment.objects.create(
            name="Opdracht X",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=30),
            source="wies",
        )
        service = Service.objects.create(
            assignment=assignment, description="X", skill=shared_skill, source="wies"
        )
        bob = Colleague.objects.create(name="Bob", email="bob@test.com", source="wies")
        carol = Colleague.objects.create(name="Carol", email="carol@test.com", source="wies")
        Placement.objects.create(colleague=bob, service=service, source="wies")
        Placement.objects.create(colleague=carol, service=service, source="wies")

        person_resp = self.client.get(reverse("home"))
        assert person_resp.context_data["results_count"] == 2

        assignment_resp = self.client.get(reverse("home") + "?groep=assignment")
        assert assignment_resp.context_data["results_count"] == 1

    # --- groupby param handling --------------------------------------------

    def test_groupby_defaults_to_person(self):
        _make_placement("Alice", "Opdracht A", 30)
        resp = self.client.get(reverse("home"))
        assert resp.status_code == 200
        assert resp.context_data["groupby_field"] == "person"

    def test_groupby_invalid_falls_back_to_person(self):
        _make_placement("Alice", "Opdracht A", 30)
        resp = self.client.get(reverse("home") + "?groep=zzz")
        assert resp.status_code == 200
        assert resp.context_data["groupby_field"] == "person"

    def test_groupby_assignment_is_honoured(self):
        _make_placement("Alice", "Opdracht A", 30)
        resp = self.client.get(reverse("home") + "?groep=assignment")
        assert resp.status_code == 200
        assert resp.context_data["groupby_field"] == "assignment"

    # --- order param handling ----------------------------------------------

    def test_removed_skill_order_is_ignored(self):
        """The removed ?order=skill must not 500 and falls back to default sort."""
        _make_placement("Charlie", "Opdracht A", 30)
        _make_placement("Alice", "Opdracht B", 30)

        resp = self.client.get(reverse("home") + "?order=skill")
        assert resp.status_code == 200
        # Default person-view sort is on colleague name (ascending).
        names = [p.colleague.name for p in resp.context_data["object_list"]]
        assert names == sorted(names)

    def test_unknown_order_is_ignored(self):
        _make_placement("Alice", "Opdracht A", 30)
        resp = self.client.get(reverse("home") + "?order=zzz")
        assert resp.status_code == 200

    def test_order_name_descending(self):
        _make_placement("Alice", "Opdracht A", 30)
        _make_placement("Bob", "Opdracht B", 30)
        _make_placement("Charlie", "Opdracht C", 30)

        resp = self.client.get(reverse("home") + "?order=-name")
        assert resp.status_code == 200
        names = [p.colleague.name for p in resp.context_data["object_list"]]
        assert names == ["Charlie", "Bob", "Alice"]

    def test_order_end_date_ascending(self):
        _make_placement("Alice", "Opdracht Late", 90)
        _make_placement("Bob", "Opdracht Early", 10)
        _make_placement("Carol", "Opdracht Mid", 45)

        resp = self.client.get(reverse("home") + "?order=end_date")
        assert resp.status_code == 200
        end_dates = [p.service.assignment.end_date for p in resp.context_data["object_list"]]
        assert end_dates == sorted(end_dates)

    # --- default sort per view ---------------------------------------------

    def test_default_sort_person_view_is_by_name(self):
        _make_placement("Charlie", "Opdracht Z", 30)
        _make_placement("Alice", "Opdracht A", 30)
        _make_placement("Bob", "Opdracht M", 30)

        resp = self.client.get(reverse("home"))
        names = [p.colleague.name for p in resp.context_data["object_list"]]
        assert names == ["Alice", "Bob", "Charlie"]

    def test_default_sort_assignment_view_is_by_assignment_name(self):
        _make_placement("Charlie", "Opdracht Z", 30)
        _make_placement("Alice", "Opdracht A", 30)
        _make_placement("Bob", "Opdracht M", 30)

        resp = self.client.get(reverse("home") + "?groep=assignment")
        assignment_names = [p.service.assignment.name for p in resp.context_data["object_list"]]
        assert assignment_names == ["Opdracht A", "Opdracht M", "Opdracht Z"]

    # --- sort_options per view ---------------------------------------------

    def test_sort_options_person_view_offers_name(self):
        _make_placement("Alice", "Opdracht A", 30)
        resp = self.client.get(reverse("home"))
        values = [o["value"] for o in resp.context_data["sort_options"]]
        labels = [o["label"] for o in resp.context_data["sort_options"]]
        assert "-name" in values
        assert any("Naam" in label for label in labels)

    def test_sort_options_assignment_view_has_no_name(self):
        _make_placement("Alice", "Opdracht A", 30)
        resp = self.client.get(reverse("home") + "?groep=assignment")
        values = [o["value"] for o in resp.context_data["sort_options"]]
        labels = [o["label"] for o in resp.context_data["sort_options"]]
        assert "-name" not in values
        assert not any("Naam" in label for label in labels)
