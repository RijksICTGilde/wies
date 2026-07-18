"""Regression tests for two read/aggregate paths that did not inherit the
placement-visibility rule (the same class of leak as PR #468).

- The opdrachtgever (client) filter modal counted planned placements that
  ``placement_visibility`` hides from unrelated viewers.
- The generic inline-edit endpoint distinguished "object does not exist"
  (404) from "object exists but you may not touch it" (200), giving an
  existence oracle over sequential PKs.
"""

import datetime
import json
import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)

User = get_user_model()


def _modal_org_self_counts(response) -> dict[int, int]:
    """Extract {org_id: self placement count} from the client-modal json_script blob.

    Each org renders as a node carrying ``nr_of_placements``; a node that also has
    children emits a ``self: True`` sub-node holding its own (self) count, which is
    the precise value to compare against."""
    html = response.content.decode()
    match = re.search(r'<script id="client-data"[^>]*>(.*?)</script>', html, re.S)
    assert match, "client-data json_script not found in modal response"
    counts: dict[int, int] = {}

    def walk(nodes):
        for node in nodes:
            oid = node["id"]
            if node.get("self") or oid not in counts:
                counts[oid] = node["nr_of_placements"]
            walk(node.get("children", []))

    walk(json.loads(match.group(1)))
    return counts


class ClientModalPlacementCountVisibilityTests(TestCase):
    """Modal per-org placement counts must honour placement_visibility."""

    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl", first_name="O", last_name="w")
        self.placed_user = User.objects.create_user(email="placed@rijksoverheid.nl", first_name="P", last_name="l")
        self.unrelated_user = User.objects.create_user(email="other@rijksoverheid.nl", first_name="U", last_name="n")

        self.owner_colleague = Colleague.objects.create(
            user=self.owner_user, name="Owner Colleague", email="owner@rijksoverheid.nl", source="wies"
        )
        self.placed_colleague = Colleague.objects.create(
            user=self.placed_user, name="Placed Colleague", email="placed@rijksoverheid.nl", source="wies"
        )
        Colleague.objects.create(
            user=self.unrelated_user, name="Unrelated Colleague", email="other@rijksoverheid.nl", source="wies"
        )

        self.org = OrganizationUnit.objects.create(name="ZZZ Geheime Opdrachtgever", label="ZZZ Geheime Opdrachtgever")
        self.assignment = Assignment.objects.create(name="DTC4NL", owner=self.owner_colleague, source="wies")
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=self.org)
        skill = Skill.objects.create(name="Software Engineer")
        self.service = Service.objects.create(description="", assignment=self.assignment, skill=skill, source="wies")

    def _place(self, *, start_offset_days, end_offset_days):
        today = timezone.now().date()
        return Placement.objects.create(
            colleague=self.placed_colleague,
            service=self.service,
            specific_start_date=today + datetime.timedelta(days=start_offset_days),
            specific_end_date=today + datetime.timedelta(days=end_offset_days),
            period_source=Placement.PLACEMENT,
            source="wies",
        )

    def _modal_count_for(self, user) -> int:
        self.client.force_login(user)
        response = self.client.get(reverse("client-modal"))
        assert response.status_code == 200
        return _modal_org_self_counts(response).get(self.org.id, 0)

    def test_planned_placement_not_counted_for_unrelated_viewer(self):
        """A not-yet-started placement is private; its org count must not betray it."""
        self._place(start_offset_days=30, end_offset_days=120)

        assert self._modal_count_for(self.unrelated_user) == 0

    def test_planned_placement_counted_for_bm_owner(self):
        """The BM-owner may see the planned placement, so their count includes it."""
        self._place(start_offset_days=30, end_offset_days=120)

        assert self._modal_count_for(self.owner_user) == 1

    def test_active_placement_counted_for_everyone(self):
        """An active placement is public; the count includes it for any viewer."""
        self._place(start_offset_days=-10, end_offset_days=10)

        assert self._modal_count_for(self.unrelated_user) == 1


class InlineEditExistenceOracleTests(TestCase):
    """The generic inline-edit endpoint must not reveal whether an object
    exists to a viewer who may not touch it: 'not found' and 'not allowed'
    must be indistinguishable, so sequential PKs can't be walked as an oracle."""

    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl", first_name="O", last_name="w")
        self.unrelated_user = User.objects.create_user(email="other@rijksoverheid.nl", first_name="U", last_name="n")
        self.owner_colleague = Colleague.objects.create(
            user=self.owner_user, name="Owner Colleague", email="owner@rijksoverheid.nl", source="wies"
        )
        self.placed_colleague = Colleague.objects.create(
            name="Placed Colleague", email="placed@rijksoverheid.nl", source="wies"
        )
        Colleague.objects.create(
            user=self.unrelated_user, name="Unrelated Colleague", email="other@rijksoverheid.nl", source="wies"
        )
        self.assignment = Assignment.objects.create(name="DTC4NL", owner=self.owner_colleague, source="wies")
        skill = Skill.objects.create(name="Software Engineer")
        self.service = Service.objects.create(description="", assignment=self.assignment, skill=skill, source="wies")
        today = timezone.now().date()
        self.placement = Placement.objects.create(
            colleague=self.placed_colleague,
            service=self.service,
            specific_start_date=today + datetime.timedelta(days=30),
            specific_end_date=today + datetime.timedelta(days=120),
            period_source=Placement.PLACEMENT,
            source="wies",
        )

    def _get(self, pk):
        return self.client.get(reverse("inline-edit", args=["placement", pk, "period"]))

    def test_existing_forbidden_and_missing_are_indistinguishable(self):
        """An unrelated consultant cannot edit this placement (update_placement is
        owner-only) and cannot see it (it is planned). The response for the real,
        hidden placement must match the response for a non-existent PK."""
        self.client.force_login(self.unrelated_user)
        missing_pk = self.placement.pk + 100_000

        forbidden = self._get(self.placement.pk)
        missing = self._get(missing_pk)

        assert forbidden.status_code == missing.status_code
        normalize = lambda resp, pk: resp.content.decode().replace(str(pk), "PK")  # noqa: E731
        assert normalize(forbidden, self.placement.pk) == normalize(missing, missing_pk)

    def test_forbidden_response_leaks_no_object_data(self):
        """The denial response must not carry the hidden colleague's name."""
        self.client.force_login(self.unrelated_user)

        response = self._get(self.placement.pk)

        assert response.status_code == 200
        self.assertNotContains(response, "Placed Colleague")
