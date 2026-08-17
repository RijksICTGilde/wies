"""Tests for the placement-visibility rule.

Two functions decide who may see a placement:

- ``placement_timing`` / ``evaluate_placement_visibility`` — the per-row rule used
  by the panels and the colleague profile, where a placed colleague and the
  BM-owner also see their ended and planned placements.
- ``filter_visible_placements`` — the "Wie zit waar?" list, which shows only
  active placements, to every viewer alike.

The tests pin the pure rule down as a table, and assert the list is exactly the
active subset of it (viewer-independent), so the two surfaces cannot drift apart.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase

from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.placement_visibility import (
    PRIVACY_BM,
    PRIVACY_OWN,
    evaluate_placement_visibility,
    placement_timing,
)
from wies.core.querysets import annotate_placement_dates
from wies.core.services.placements import filter_visible_placements

TODAY = date(2026, 6, 15)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)


# The evaluate function only ever reads ``viewer.id``.
@dataclass
class _Viewer:
    id: int


class PlacementTimingTest(SimpleTestCase):
    """The three-way timing classification, including the boundaries."""

    def test_active_when_mid_range(self):
        assert placement_timing(start=YESTERDAY, end=TOMORROW, today=TODAY) == "active"

    def test_future_when_start_after_today(self):
        assert placement_timing(start=TOMORROW, end=TOMORROW + timedelta(days=30), today=TODAY) == "future"

    def test_ended_when_end_before_today(self):
        assert placement_timing(start=YESTERDAY - timedelta(days=30), end=YESTERDAY, today=TODAY) == "ended"

    def test_start_equal_today_is_active(self):
        # start > today is future, so start == today falls through to active.
        assert placement_timing(start=TODAY, end=TOMORROW, today=TODAY) == "active"

    def test_end_equal_today_is_active(self):
        # end < today is ended, so end == today is still active (last day counts).
        assert placement_timing(start=YESTERDAY, end=TODAY, today=TODAY) == "active"

    def test_null_start_is_never_future(self):
        assert placement_timing(start=None, end=TOMORROW, today=TODAY) == "active"

    def test_null_end_is_never_ended(self):
        assert placement_timing(start=YESTERDAY, end=None, today=TODAY) == "active"

    def test_future_start_with_null_end_is_future(self):
        # A future start wins regardless of the (missing) end date.
        assert placement_timing(start=TOMORROW, end=None, today=TODAY) == "future"

    def test_null_start_with_past_end_is_ended(self):
        # No start to make it future, and the end is in the past.
        assert placement_timing(start=None, end=YESTERDAY, today=TODAY) == "ended"

    def test_both_null_is_active(self):
        assert placement_timing(start=None, end=None, today=TODAY) == "active"


class EvaluatePlacementVisibilityTest(SimpleTestCase):
    """The full visibility matrix: timing x viewer, plus the note wording."""

    PLACED_ID = 1
    OWNER_ID = 2
    OTHER_ID = 3

    def _evaluate(self, *, start, end, viewer_id, owner_id=OWNER_ID):
        viewer = _Viewer(id=viewer_id) if viewer_id is not None else None
        return evaluate_placement_visibility(
            start=start,
            end=end,
            placed_colleague_id=self.PLACED_ID,
            viewer=viewer,
            owner_id=owner_id,
            today=TODAY,
        )

    # --- active: visible to everyone, no note, viewer irrelevant ---

    def test_active_visible_to_unrelated(self):
        result = self._evaluate(start=YESTERDAY, end=TOMORROW, viewer_id=self.OTHER_ID)
        assert result.visible is True
        assert result.timing == "active"
        assert result.privacy_note is None

    def test_active_visible_to_anonymous(self):
        result = self._evaluate(start=YESTERDAY, end=TOMORROW, viewer_id=None)
        assert result.visible is True
        assert result.privacy_note is None

    # --- future / ended: private to the placed colleague and the owner ---

    def test_future_visible_to_placed_colleague_with_own_note(self):
        result = self._evaluate(start=TOMORROW, end=TOMORROW + timedelta(days=30), viewer_id=self.PLACED_ID)
        assert result.visible is True
        assert result.timing == "future"
        assert result.privacy_note == PRIVACY_OWN

    def test_ended_visible_to_placed_colleague_with_own_note(self):
        result = self._evaluate(start=YESTERDAY - timedelta(days=30), end=YESTERDAY, viewer_id=self.PLACED_ID)
        assert result.visible is True
        assert result.timing == "ended"
        assert result.privacy_note == PRIVACY_OWN

    def test_future_visible_to_owner_with_bm_note(self):
        result = self._evaluate(start=TOMORROW, end=TOMORROW + timedelta(days=30), viewer_id=self.OWNER_ID)
        assert result.visible is True
        assert result.privacy_note == PRIVACY_BM

    def test_ended_visible_to_owner_with_bm_note(self):
        result = self._evaluate(start=YESTERDAY - timedelta(days=30), end=YESTERDAY, viewer_id=self.OWNER_ID)
        assert result.visible is True
        assert result.privacy_note == PRIVACY_BM

    def test_future_hidden_from_unrelated(self):
        result = self._evaluate(start=TOMORROW, end=TOMORROW + timedelta(days=30), viewer_id=self.OTHER_ID)
        assert result.visible is False
        assert result.privacy_note is None

    def test_ended_hidden_from_anonymous(self):
        result = self._evaluate(start=YESTERDAY - timedelta(days=30), end=YESTERDAY, viewer_id=None)
        assert result.visible is False

    # --- edge cases in the identity checks ---

    def test_owner_id_none_does_not_grant_or_crash(self):
        # An assignment without an owner: the BM branch must not fire.
        result = self._evaluate(
            start=TOMORROW, end=TOMORROW + timedelta(days=30), viewer_id=self.OWNER_ID, owner_id=None
        )
        assert result.visible is False

    def test_placed_branch_wins_when_viewer_is_both_placed_and_owner(self):
        # The placed-colleague check runs before the owner check, so a viewer who
        # is both gets PRIVACY_OWN, not PRIVACY_BM.
        result = evaluate_placement_visibility(
            start=TOMORROW,
            end=TOMORROW + timedelta(days=30),
            placed_colleague_id=self.PLACED_ID,
            viewer=_Viewer(id=self.PLACED_ID),
            owner_id=self.PLACED_ID,
            today=TODAY,
        )
        assert result.privacy_note == PRIVACY_OWN


class ListVisibilityParityTest(TestCase):
    """The WZW list (``filter_visible_placements``) must equal the ``active``
    subset of ``evaluate_placement_visibility``, for every viewer alike.

    This is the guardrail against the two implementations drifting: the list is
    active-only and viewer-independent, while the panels additionally show
    ended/future placements to the placed colleague and the BM-owner.
    """

    def setUp(self):
        self.skill = Skill.objects.create(name="Python Developer")
        self.placed = Colleague.objects.create(name="Placed", email="placed@rijksoverheid.nl", source="wies")
        self.owner = Colleague.objects.create(name="Owner", email="owner@rijksoverheid.nl", source="wies")
        self.unrelated = Colleague.objects.create(name="Other", email="other@rijksoverheid.nl", source="wies")

        self.assignment = Assignment.objects.create(name="A", source="wies", owner=self.owner)
        self.active = self._place(start=YESTERDAY, end=TOMORROW)
        self.future = self._place(start=TOMORROW, end=TOMORROW + timedelta(days=90))
        self.ended = self._place(start=YESTERDAY - timedelta(days=90), end=YESTERDAY)

    def _place(self, *, start, end):
        service = Service.objects.create(assignment=self.assignment, description="s", skill=self.skill, source="wies")
        return Placement.objects.create(
            colleague=self.placed,
            service=service,
            period_source=Placement.PLACEMENT,
            specific_start_date=start,
            specific_end_date=end,
            source="wies",
        )

    def _list_ids(self):
        qs = annotate_placement_dates(Placement.objects.all())
        return set(filter_visible_placements(qs, TODAY).values_list("id", flat=True))

    def _evaluate_active_ids(self, viewer):
        active = set()
        for placement in Placement.objects.all():
            result = evaluate_placement_visibility(
                start=placement.specific_start_date,
                end=placement.specific_end_date,
                placed_colleague_id=placement.colleague_id,
                viewer=viewer,
                owner_id=self.assignment.owner_id,
                today=TODAY,
            )
            if result.timing == "active":
                active.add(placement.id)
        return active

    def test_list_equals_active_subset_for_every_viewer(self):
        # The list takes no viewer; the evaluate side is computed per row. For
        # every viewer class the list must equal the set of active placements.
        for viewer in (None, self.placed, self.owner, self.unrelated):
            assert self._list_ids() == self._evaluate_active_ids(viewer), f"mismatch for viewer={viewer}"

    def test_list_is_viewer_independent(self):
        # Regression guard: no viewer branch may creep back into the list. The
        # queryset itself no longer takes a viewer, so the id set is one value.
        assert self._list_ids() == {self.active.id}

    def test_future_and_ended_absent_from_list_but_visible_on_panels(self):
        # The intended divergence: planned/ended placements never reach the list,
        # yet the panels still show them to the placed colleague and the owner.
        list_ids = self._list_ids()
        assert self.future.id not in list_ids
        assert self.ended.id not in list_ids

        for placement in (self.future, self.ended):
            for viewer in (self.placed, self.owner):
                result = evaluate_placement_visibility(
                    start=placement.specific_start_date,
                    end=placement.specific_end_date,
                    placed_colleague_id=placement.colleague_id,
                    viewer=viewer,
                    owner_id=self.assignment.owner_id,
                    today=TODAY,
                )
                assert result.visible is True, f"{placement} should be visible to {viewer} on the panel"
