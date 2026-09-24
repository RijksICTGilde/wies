"""Who sees ended and future placements and assignments (#636).

The BDM role is what makes a viewer privileged for the placement-visibility rule,
not ownership and not being placed. These tests put a BDM who is neither on each
surface that shows such a row, panel, timeline event or profile card, and check
that application administration (``STAFF_EMAILS``) alone grants none of it.
"""

from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from wies.core.editables.assignment import _services_display_context
from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.roles import ROLE_BDM, is_bdm_request
from wies.core.tests.role_helpers import STAFF_EMAIL, make_other_bdm_user, make_staff_user
from wies.core.views import _get_colleague_assignments, _resolve_placement_panel
from wies.core.visibility_rules import PRIVACY_BDM
from wies.rijksauth.models import User


class IsBdmRequestTest(SimpleTestCase):
    """The role-based half of the visibility gate: the BDM role, else not."""

    @staticmethod
    def _request(*, email="u@rijksoverheid.nl", groups=()):
        user = Mock(is_authenticated=True, email=email)
        user.groups.filter.side_effect = lambda name: Mock(exists=Mock(return_value=name in groups))
        request = Mock(spec=["user"])
        request.user = user
        return request

    def test_bdm_can_see(self):
        assert is_bdm_request(self._request(groups={ROLE_BDM})) is True

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_bare_staff_cannot_see(self):
        # Application administration carries no functional rights.
        assert is_bdm_request(self._request(email=STAFF_EMAIL)) is False

    def test_unrelated_cannot_see(self):
        assert is_bdm_request(self._request()) is False

    def test_anonymous_cannot_see(self):
        request = Mock(spec=["user"])
        request.user = Mock(is_authenticated=False)
        assert is_bdm_request(request) is False


class _VisibilityFixture(TestCase):
    """An ended placement plus an unrelated BDM viewer and a bare staff viewer,
    neither of them placed."""

    def setUp(self):
        self.skill = Skill.objects.create(name="Python Developer")
        self.user_alice = User.objects.create_user(email="alice@rijksoverheid.nl")
        self.colleague_alice = Colleague.objects.create(
            name="Alice", email="alice@rijksoverheid.nl", source="wies", user=self.user_alice
        )
        self.assignment = Assignment.objects.create(name="Opdracht X", source="wies")
        service = Service.objects.create(assignment=self.assignment, description="s", skill=self.skill, source="wies")
        # Ended, so it is private to the placed colleague and privileged viewers.
        self.ended = Placement.objects.create(
            colleague=self.colleague_alice,
            service=service,
            period_source=Placement.PLACEMENT,
            specific_start_date=date(2024, 1, 1),
            specific_end_date=date(2024, 6, 14),
            source="wies",
        )
        self.bdm_viewer = make_other_bdm_user()
        self.user_staff = make_staff_user()

    def _request(self, user):
        request = RequestFactory().get(reverse("home"))
        request.user = user
        return request


class AssignmentAdminSeesTeamRowTest(_VisibilityFixture):
    @patch("wies.core.editables.assignment.timezone")
    def test_a_bdm_sees_ended_team_row(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        rows = _services_display_context(self.assignment, self._request(self.bdm_viewer))["value"]

        visible = [r for r in rows if r["colleague"]]
        assert len(visible) == 1
        assert visible[0]["colleague"].id == self.colleague_alice.id
        assert visible[0]["historical"] is True
        assert visible[0]["privacy_warning_text"] == PRIVACY_BDM

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    @patch("wies.core.editables.assignment.timezone")
    def test_bare_staff_does_not_see_ended_team_row(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        rows = _services_display_context(self.assignment, self._request(self.user_staff))["value"]

        assert [r for r in rows if r["colleague"]] == []


class AssignmentAdminSeesPlacementPanelTest(_VisibilityFixture):
    @patch("wies.core.views.timezone")
    def test_a_bdm_opens_ended_placement_panel(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        data = _resolve_placement_panel(self._request(self.bdm_viewer), self.ended.public_id)

        assert data is not None
        assert data["assignment_card"]["privacy_warning_text"] == PRIVACY_BDM


class AssignmentAdminSeesProfileHistoryTest(_VisibilityFixture):
    @patch("wies.core.views.timezone")
    def test_a_bdm_sees_historical_placement_on_profile(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        assignments = _get_colleague_assignments(self._request(self.bdm_viewer), self.colleague_alice)

        historical = [a for a in assignments if a["historical"]]
        assert len(historical) == 1
        assert historical[0]["privacy_warning_text"] == PRIVACY_BDM

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    @patch("wies.core.views.timezone")
    def test_bare_staff_does_not_see_historical_placement_on_profile(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        assignments = _get_colleague_assignments(self._request(self.user_staff), self.colleague_alice)

        assert [a for a in assignments if a["historical"]] == []

    @patch("wies.core.views.timezone")
    def test_a_bdm_sees_ended_owned_assignment_on_profile(self, mock_tz):
        # An assignment Alice OWNS (no placement) that has ended: shown to a
        # privileged viewer via the owned-assignment branch.
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        owned = Assignment.objects.create(
            name="Alice Ended BM Assignment",
            source="wies",
            owner=self.colleague_alice,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 14),
        )

        assignments = _get_colleague_assignments(self._request(self.bdm_viewer), self.colleague_alice)

        assert any(a["id"] == owned.id and a["historical"] for a in assignments)


class OwnerPlacedOnEndedAssignmentTest(_VisibilityFixture):
    """When you own AND are placed on an ended assignment, the card shows via your
    own placement; the "Business Manager" label must ride along on it (#655).

    Regression: the owned-assignment visibility gate used to ``continue`` past the
    label for a non-privileged viewer, dropping it from a card that is shown anyway.
    """

    @patch("wies.core.views.timezone")
    def test_own_profile_keeps_the_bm_label_on_the_ended_card(self, mock_tz):
        # Alice is not a BDM; she views her own profile. The ended
        # assignment she owns is also one she is placed on (self.ended).
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))
        self.assignment.owner = self.colleague_alice
        self.assignment.start_date = date(2024, 1, 1)
        self.assignment.end_date = date(2024, 6, 14)
        self.assignment.save(update_fields=["owner", "start_date", "end_date"])

        assignments = _get_colleague_assignments(self._request(self.user_alice), self.colleague_alice)

        card = next(a for a in assignments if a["id"] == self.assignment.id)
        tag_names = {t["skill"] for t in card["tags"]}
        assert card["historical"] is True
        assert "Business Manager" in tag_names
        assert "Python Developer" in tag_names


class AssignmentAdminSeesTimelineEventTest(TestCase):
    """The updates tab shows a BDM viewer the team event for a hidden placement."""

    HX = {"HX-Request": "true", "HX-Target": "side-panel-content"}

    def setUp(self):
        self.skill = Skill.objects.create(name="Python Developer")
        self.assignment = Assignment.objects.create(name="DTC4NL", source="wies")
        self.hidden = Colleague.objects.create(name="Hidden Colleague", email="hidden@rijksoverheid.nl", source="wies")
        service = Service.objects.create(assignment=self.assignment, description="s", skill=self.skill, source="wies")
        today = timezone.now().date()
        Placement.objects.create(
            colleague=self.hidden,
            service=service,
            period_source=Placement.PLACEMENT,
            specific_start_date=today + timedelta(days=30),
            specific_end_date=today + timedelta(days=120),
            source="wies",
        )
        self.bdm_viewer = make_other_bdm_user()

    def test_a_bdm_sees_the_hidden_team_member(self):
        client = Client()
        client.force_login(self.bdm_viewer)

        response = client.get(reverse("home") + f"?opdracht={self.assignment.public_id}", headers=self.HX)

        assert response.status_code == 200
        self.assertContains(response, "Hidden Colleague")
