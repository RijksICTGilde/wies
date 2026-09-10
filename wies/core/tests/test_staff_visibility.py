"""Support staff see ended/future placements and assignments, like a BDM (#636).

A ``STAFF_EMAILS`` member is a privileged viewer for the placement-visibility
rule: the same rows, panels, timeline events and profile cards a BDM sees. These
tests mirror the BDM positive cases with a staff viewer on each surface.

Staff membership is email-based, so every test applies
``@override_settings(STAFF_EMAILS=[STAFF_EMAIL])``; ``make_staff_user`` provides
the matching user + colleague.
"""

from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from wies.core.editables.assignment import _services_display_context
from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.roles import is_bdm_or_staff
from wies.core.tests.role_helpers import STAFF_EMAIL, make_staff_user
from wies.core.views import _get_colleague_assignments, _resolve_placement_panel
from wies.core.visibility_rules import PRIVACY_BDM
from wies.rijksauth.models import User


class IsBdmOrStaffTest(SimpleTestCase):
    """The role-based half of the visibility gate: BDM or staff, else not."""

    @staticmethod
    def _request(*, email, in_bdm_group=False):
        # is_bdm reads user.groups.filter(...).exists(); pin it so the staff
        # branch is what's actually under test.
        user = Mock(is_authenticated=True, email=email)
        user.groups.filter.return_value.exists.return_value = in_bdm_group
        request = Mock(spec=["user"])
        request.user = user
        return request

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_can_see(self):
        assert is_bdm_or_staff(self._request(email=STAFF_EMAIL)) is True

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_check_is_case_insensitive(self):
        assert is_bdm_or_staff(self._request(email=STAFF_EMAIL.upper())) is True

    @override_settings(STAFF_EMAILS=["someone-else@rijksoverheid.nl"])
    def test_bdm_can_see(self):
        assert is_bdm_or_staff(self._request(email="b@rijksoverheid.nl", in_bdm_group=True)) is True

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_unrelated_cannot_see(self):
        # Not staff (different email) and not a BDM.
        assert is_bdm_or_staff(self._request(email="nobody@rijksoverheid.nl")) is False

    def test_anonymous_cannot_see(self):
        request = Mock(spec=["user"])
        request.user = Mock(is_authenticated=False)
        assert is_bdm_or_staff(request) is False


class _VisibilityFixture(TestCase):
    """An ended placement plus an unrelated staff/BDM viewer, none of them placed."""

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
        self.user_staff = make_staff_user()

    def _request(self, user):
        request = RequestFactory().get(reverse("home"))
        request.user = user
        return request


class StaffSeesTeamRowTest(_VisibilityFixture):
    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    @patch("wies.core.editables.assignment.timezone")
    def test_staff_sees_ended_team_row(self, mock_timezone):
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        rows = _services_display_context(self.assignment, self._request(self.user_staff))["value"]

        visible = [r for r in rows if r["colleague"]]
        assert len(visible) == 1
        assert visible[0]["colleague"].id == self.colleague_alice.id
        assert visible[0]["historical"] is True
        assert visible[0]["privacy_warning_text"] == PRIVACY_BDM

    @patch("wies.core.editables.assignment.timezone")
    def test_non_staff_does_not_see_ended_team_row(self, mock_timezone):
        # Same user, but with the email NOT in STAFF_EMAILS (no override) → hidden.
        mock_timezone.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        rows = _services_display_context(self.assignment, self._request(self.user_staff))["value"]

        assert [r for r in rows if r["colleague"]] == []


class StaffSeesPlacementPanelTest(_VisibilityFixture):
    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    @patch("wies.core.views.timezone")
    def test_staff_opens_ended_placement_panel(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        data = _resolve_placement_panel(self._request(self.user_staff), self.ended.public_id)

        assert data is not None
        assert data["assignment_card"]["privacy_warning_text"] == PRIVACY_BDM


class StaffSeesProfileHistoryTest(_VisibilityFixture):
    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    @patch("wies.core.views.timezone")
    def test_staff_sees_historical_placement_on_profile(self, mock_tz):
        mock_tz.now.return_value = Mock(date=Mock(return_value=date(2024, 6, 15)))

        assignments = _get_colleague_assignments(self._request(self.user_staff), self.colleague_alice)

        historical = [a for a in assignments if a["historical"]]
        assert len(historical) == 1
        assert historical[0]["privacy_warning_text"] == PRIVACY_BDM

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    @patch("wies.core.views.timezone")
    def test_staff_sees_ended_owned_assignment_on_profile(self, mock_tz):
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

        assignments = _get_colleague_assignments(self._request(self.user_staff), self.colleague_alice)

        assert any(a["id"] == owned.id and a["historical"] for a in assignments)


class OwnerPlacedOnEndedAssignmentTest(_VisibilityFixture):
    """When you own AND are placed on an ended assignment, the card shows via your
    own placement; the "Business Manager" label must ride along on it (#655).

    Regression: the owned-assignment visibility gate used to ``continue`` past the
    label for a non-privileged viewer, dropping it from a card that is shown anyway.
    """

    @patch("wies.core.views.timezone")
    def test_own_profile_keeps_the_bm_label_on_the_ended_card(self, mock_tz):
        # Alice is not a BDM and not staff; she views her own profile. The ended
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


class StaffSeesTimelineEventTest(TestCase):
    """The updates tab shows a staff viewer the team event for a hidden placement."""

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
        self.user_staff = make_staff_user()

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_sees_the_hidden_team_member(self):
        client = Client()
        client.force_login(self.user_staff)

        response = client.get(reverse("home") + f"?opdracht={self.assignment.public_id}", headers=self.HX)

        assert response.status_code == 200
        self.assertContains(response, "Hidden Colleague")
