"""Test pagination behavior for placement list view."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Placement, Service, Skill

User = get_user_model()


def _placed_assignments(response) -> list[str]:
    """The opdracht on each card of a person-view page; each test colleague has one.

    A card without a period has no current placement, like the viewer's own.
    """
    return [card["assignment_text"] for card in response.context_data["cards"] if card["period_text"]]


@pytest.mark.django_db
class TestPlacementPagination:
    """Test that placement pagination doesn't show duplicates."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create authenticated user for tests."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_pagination_no_duplicates(self):
        """Test that paginated results don't contain duplicate placements."""
        # Create test data: 75 placements (more than the page size of 60)
        skill = Skill.objects.create(name="Test Skill")

        # Create 75 colleagues, assignments, services, and placements
        assignments_created = []
        today = timezone.now().date()

        for i in range(75):
            colleague = Colleague.objects.create(
                name=f"Test Colleague {i}",
                email=f"colleague{i}@test.com",
                source="wies",
            )

            assignment = Assignment.objects.create(
                name=f"Test Assignment {i}",
                start_date=today - timedelta(days=30),
                end_date=today + timedelta(days=30),  # Current assignment
                source="wies",
            )

            service = Service.objects.create(
                assignment=assignment,
                description=f"Test Service {i}",
                skill=skill,
                source="wies",
            )

            Placement.objects.create(
                colleague=colleague,
                service=service,
                source="wies",
            )
            assignments_created.append(assignment.name)

        # Get first page
        response1 = self.client.get(reverse("home"))
        assert response1.status_code == 200

        page1_assignments = _placed_assignments(response1)

        # Get second page
        response2 = self.client.get(reverse("home") + "?pagina=2")
        assert response2.status_code == 200

        # The placed opdrachten on page 2
        page2_assignments = _placed_assignments(response2)

        # Check no duplicates between pages
        duplicates = set(page1_assignments) & set(page2_assignments)
        assert len(duplicates) == 0, f"Found {len(duplicates)} opdrachten on both pages: {duplicates}"

        # Check total count
        total_assignments = page1_assignments + page2_assignments
        assert len(total_assignments) == 75, f"Expected 75 total placements, got {len(total_assignments)}"
        assert len(set(total_assignments)) == 75, f"Expected 75 unique placements, got {len(set(total_assignments))}"

    def test_pagination_with_historical_filter(self):
        """Test that historical filter works correctly across pagination."""
        skill = Skill.objects.create(name="Test Skill")
        today = timezone.now().date()

        # Create 60 total placements: 30 current, 30 historical
        current_assignments = []
        historical_assignments = []

        for i in range(60):
            colleague = Colleague.objects.create(
                name=f"Test Colleague {i}",
                email=f"colleague{i}@test.com",
                source="wies",
            )

            # Alternate between current and historical assignments
            is_current = i < 30

            assignment = Assignment.objects.create(
                name=f"Test Assignment {i}",
                start_date=today - timedelta(days=60) if not is_current else today - timedelta(days=30),
                end_date=today - timedelta(days=1) if not is_current else today + timedelta(days=30),
                source="wies",
            )

            service = Service.objects.create(
                assignment=assignment,
                description=f"Test Service {i}",
                skill=skill,
                source="wies",
            )

            Placement.objects.create(
                colleague=colleague,
                service=service,
                source="wies",
            )

            if is_current:
                current_assignments.append(assignment.name)
            else:
                historical_assignments.append(assignment.name)

        # Get all pages
        response = self.client.get(reverse("home"))
        assert response.status_code == 200

        all_assignments = _placed_assignments(response)

        # Should only see the 30 current placements
        assert len(all_assignments) == 30, f"Expected 30 current placements, got {len(all_assignments)}"

        # None of the historical placements should appear
        shown_historical = set(all_assignments) & set(historical_assignments)
        assert len(shown_historical) == 0, f"Found {len(shown_historical)} historical placements in results"

        # All current placements should be present
        shown_current = set(all_assignments) & set(current_assignments)
        assert len(shown_current) == 30, f"Expected all 30 current placements, only found {len(shown_current)}"
