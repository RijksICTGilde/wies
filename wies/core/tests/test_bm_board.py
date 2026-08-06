"""PoC BM-kanban-bord: de kaart-data die build_bm_board oplevert — bezetting
(ingevuld/totaal), open plekken en de bijna-afgelopen-signalering."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Placement, Service
from wies.core.services.board import ENDING_SOON_WEEKS, build_bm_board


def _card_for(board, assignment_id):
    for cards in board.values():
        for card in cards:
            if card["id"] == assignment_id:
                return card
    return None


class BuildBmBoardTest(TestCase):
    def setUp(self):
        self.owner = Colleague.objects.create(name="BM", email="bm@example.test")
        self.member = Colleague.objects.create(name="Lid", email="lid@example.test")

    def _assignment(self, **kwargs):
        return Assignment.objects.create(name="Opdracht", source="wies", owner=self.owner, **kwargs)

    def _service(self, assignment, *, filled=False):
        svc = Service.objects.create(assignment=assignment, description="Rol", status="OPEN", source="wies")
        if filled:
            Placement.objects.create(colleague=self.member, service=svc, source="wies")
        return svc

    def test_occupancy_counts_filled_vs_total(self):
        a = self._assignment()
        self._service(a, filled=True)
        self._service(a, filled=True)
        self._service(a, filled=False)
        card = _card_for(build_bm_board(self.owner), a.id)
        assert card["fte"] == 3
        assert card["filled"] == 2
        assert card["open_count"] == 1

    def test_fully_filled_has_no_open(self):
        a = self._assignment()
        self._service(a, filled=True)
        card = _card_for(build_bm_board(self.owner), a.id)
        assert card["open_count"] == 0

    def test_weeks_until_end_within_window(self):
        soon = timezone.now().date() + timedelta(weeks=3)
        a = self._assignment(end_date=soon)
        card = _card_for(build_bm_board(self.owner), a.id)
        assert card["weeks_until_end"] == 3
        assert 0 <= card["weeks_until_end"] <= ENDING_SOON_WEEKS

    def test_weeks_until_end_far_away(self):
        far = timezone.now().date() + timedelta(weeks=30)
        a = self._assignment(end_date=far)
        card = _card_for(build_bm_board(self.owner), a.id)
        assert card["weeks_until_end"] == 30

    def test_no_end_date_gives_none(self):
        a = self._assignment(end_date=None)
        card = _card_for(build_bm_board(self.owner), a.id)
        assert card["weeks_until_end"] is None

    def test_only_own_assignments(self):
        other_owner = Colleague.objects.create(name="Ander", email="ander@example.test")
        mine = self._assignment()
        theirs = Assignment.objects.create(name="Van ander", source="wies", owner=other_owner)
        board = build_bm_board(self.owner)
        assert _card_for(board, mine.id) is not None
        assert _card_for(board, theirs.id) is None

    def test_gilde_filter_splits_by_id_parity(self):
        a = self._assignment()
        expected = "it" if a.id % 2 == 0 else "digi"
        other = "digi" if expected == "it" else "it"
        # Met het eigen gilde zit de kaart erin, met het andere niet.
        assert _card_for(build_bm_board(self.owner, gilde=expected), a.id) is not None
        assert _card_for(build_bm_board(self.owner, gilde=other), a.id) is None

    def test_ending_within_months_filter(self):
        near = self._assignment(end_date=timezone.now().date() + timedelta(days=20))
        far = self._assignment(end_date=timezone.now().date() + timedelta(days=200))
        no_date = self._assignment(end_date=None)
        board = build_bm_board(self.owner, ending_within_months=1)
        assert _card_for(board, near.id) is not None
        assert _card_for(board, far.id) is None
        assert _card_for(board, no_date.id) is None

    def test_ending_filter_excludes_past_dates(self):
        past = self._assignment(end_date=timezone.now().date() - timedelta(days=5))
        board = build_bm_board(self.owner, ending_within_months=3)
        assert _card_for(board, past.id) is None
