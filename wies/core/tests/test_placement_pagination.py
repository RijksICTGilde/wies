"""Test pagination behavior for placement list view."""

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Placement, Service, Skill, User


@pytest.mark.django_db
class TestPlacementPagination:
    """Test that placement pagination doesn't show duplicates."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create authenticated user for tests."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_pagination_no_duplicates(self):
        """Test that paginated results don't contain duplicate placements."""
        # Create test data: 60 placements (more than page size of 50)
        skill = Skill.objects.create(name="Test Skill")

        # Create 60 colleagues, assignments, services, and placements
        placements_created = []
        today = timezone.now().date()

        for i in range(60):
            colleague = Colleague.objects.create(
                name=f"Test Colleague {i}",
                email=f"colleague{i}@test.com",
                source="wies",
            )

            assignment = Assignment.objects.create(
                name=f"Test Assignment {i}",
                status="INGEVULD",
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

            placement = Placement.objects.create(
                colleague=colleague,
                service=service,
                source="wies",
            )
            placements_created.append(placement.id)

        # Get first page
        response1 = self.client.get(reverse("home"))
        assert response1.status_code == 200

        # For Jinja2 templates, context is available immediately after get()
        page_obj = response1.context_data["page_obj"]

        # Extract placement IDs from page 1 (object_list is a list of Placement objects)
        page1_ids = [p.id for p in page_obj.object_list]

        # Get second page
        response2 = self.client.get(reverse("home") + "?pagina=2")
        assert response2.status_code == 200

        # Extract placement IDs from page 2
        page_obj2 = response2.context_data["page_obj"]
        page2_ids = [p.id for p in page_obj2.object_list]

        # Check no duplicates between pages
        duplicates = set(page1_ids) & set(page2_ids)
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate placement IDs across pages: {duplicates}"

        # Check total count
        total_ids = page1_ids + page2_ids
        assert len(total_ids) == 60, f"Expected 60 total placements, got {len(total_ids)}"
        assert len(set(total_ids)) == 60, f"Expected 60 unique placements, got {len(set(total_ids))}"

    def test_pagination_with_historical_filter(self):
        """Test that historical filter works correctly across pagination."""
        skill = Skill.objects.create(name="Test Skill")
        today = timezone.now().date()

        # Create 60 total placements: 30 current, 30 historical
        current_placement_ids = []
        historical_placement_ids = []

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
                status="INGEVULD",
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

            placement = Placement.objects.create(
                colleague=colleague,
                service=service,
                source="wies",
            )

            if is_current:
                current_placement_ids.append(placement.id)
            else:
                historical_placement_ids.append(placement.id)

        # Get all pages
        response = self.client.get(reverse("home"))
        assert response.status_code == 200

        page_obj = response.context_data["page_obj"]
        all_placement_ids = [p.id for p in page_obj.object_list]

        # Should only see the 30 current placements
        assert len(all_placement_ids) == 30, f"Expected 30 current placements, got {len(all_placement_ids)}"

        # None of the historical placements should appear
        shown_historical = set(all_placement_ids) & set(historical_placement_ids)
        assert len(shown_historical) == 0, f"Found {len(shown_historical)} historical placements in results"

        # All current placements should be present
        shown_current = set(all_placement_ids) & set(current_placement_ids)
        assert len(shown_current) == 30, f"Expected all 30 current placements, only found {len(shown_current)}"
