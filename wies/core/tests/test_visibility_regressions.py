"""Regression tests for the BDM visibility rule's edge surfaces (#636).

Two holes found in review:

- The ``?teamlid=`` member-edit sheet resolved its row against the unfiltered
  team list, so a viewer with UPDATE rights but without visibility (a
  ``change_assignment`` holder, staff) could read a hidden ended placement's
  colleague and dates through a crafted URL — data the 404 anti-oracle in
  ``_resolve_placement_panel`` exists to withhold.
- The timeline's privacy note was taken from the *first* noted row of the
  viewer's current team list, so an event about one colleague could carry
  another row's note ("jou"-wording on someone else's event), and an event
  whose placement was since deleted lost its chip entirely.
"""

from datetime import timedelta

from django.contrib.auth.models import Permission
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.placement_visibility import PRIVACY_BDM, PRIVACY_OWN
from wies.core.tests.role_helpers import grant_bdm
from wies.core.views import _team_event_privacy_note
from wies.rijksauth.models import User


def _place(assignment, skill, colleague, *, start, end):
    service = Service.objects.create(assignment=assignment, description="s", skill=skill, source="wies")
    return Placement.objects.create(
        colleague=colleague,
        service=service,
        period_source=Placement.PLACEMENT,
        specific_start_date=start,
        specific_end_date=end,
        source="wies",
    )


class MemberSheetHiddenRowTest(TestCase):
    """The ``?teamlid=`` sheet must honour the row-visibility rule.

    Dates are real offsets from ``timezone.now()`` so the view and the editables
    module agree on today without patching.
    """

    HX = {"HX-Request": "true", "HX-Target": "side-panel-content"}

    def setUp(self):
        self.skill = Skill.objects.create(name="Python Developer")
        today = timezone.now().date()

        self.owner = Colleague.objects.create(name="Owner", email="owner@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="DTC4NL", owner=self.owner, source="wies")

        active = Colleague.objects.create(name="Active Member", email="active@rijksoverheid.nl", source="wies")
        hidden = Colleague.objects.create(name="Hidden Member", email="hidden@rijksoverheid.nl", source="wies")
        self.active_placement = _place(
            self.assignment, self.skill, active, start=today - timedelta(days=10), end=today + timedelta(days=10)
        )
        self.hidden_placement = _place(
            self.assignment, self.skill, hidden, start=today - timedelta(days=100), end=today - timedelta(days=10)
        )

        # The surviving edit-but-not-see class: UPDATE via change_assignment,
        # no visibility (not placed, not a BDM).
        self.editor_user = User.objects.create_user(email="editor@rijksoverheid.nl")
        Colleague.objects.create(name="Editor", email="editor@rijksoverheid.nl", source="wies", user=self.editor_user)
        self.editor_user.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        self.editor_client = Client()
        self.editor_client.force_login(self.editor_user)

    def _sheet_url(self, placement) -> str:
        teamlid = placement.service.public_id
        return reverse("home") + f"?opdracht={self.assignment.public_id}&teamlid={teamlid}"

    def test_hidden_row_sheet_does_not_leak_to_an_editor_without_visibility(self):
        response = self.editor_client.get(self._sheet_url(self.hidden_placement), headers=self.HX)

        # The teamlid misses against the filtered rows, so the request falls
        # back to the read-only panel — which strips the hidden member too.
        assert response.status_code == 200
        self.assertNotContains(response, "Hidden Member")
        self.assertNotContains(response, "Teamlid bewerken")

    def test_visible_row_sheet_still_opens_for_that_editor(self):
        response = self.editor_client.get(self._sheet_url(self.active_placement), headers=self.HX)

        assert response.status_code == 200
        self.assertContains(response, "Teamlid bewerken")
        self.assertContains(response, "Active Member")

    def test_bdm_owner_still_opens_the_hidden_row_sheet(self):
        # Same email as the owner colleague, so the login signal links the two
        # instead of creating a second colleague for this user.
        owner_user = User.objects.create_user(email="owner@rijksoverheid.nl")
        self.owner.user = owner_user
        self.owner.save(update_fields=["user"])
        grant_bdm(owner_user)
        owner_client = Client()
        owner_client.force_login(owner_user)

        response = owner_client.get(self._sheet_url(self.hidden_placement), headers=self.HX)

        assert response.status_code == 200
        self.assertContains(response, "Teamlid bewerken")
        self.assertContains(response, "Hidden Member")


class TeamEventPrivacyNoteTest(TestCase):
    """The timeline note derives from the event's own names, not from whichever
    current team row happens to carry a note."""

    def setUp(self):
        self.skill = Skill.objects.create(name="Python Developer")
        self.today = timezone.now().date()
        self.assignment = Assignment.objects.create(name="Opdracht X", source="wies")

        self.active = Colleague.objects.create(name="Active Member", email="active@rijksoverheid.nl", source="wies")
        _place(
            self.assignment,
            self.skill,
            self.active,
            start=self.today - timedelta(days=10),
            end=self.today + timedelta(days=10),
        )

    def _request(self, user):
        request = RequestFactory().get(reverse("home"))
        request.user = user
        return request

    @staticmethod
    def _removal_of(name) -> list[dict]:
        # The frozen audit snapshot of a row removal: only the old side exists.
        return [{"old": {"colleague_name": name}, "new": None}]

    def test_deleted_hidden_placement_still_gets_the_bdm_note(self):
        # The event names a colleague whose placement no longer exists, so no
        # current row carries a note — the chip must survive on the event's own
        # names instead of vanishing.
        bdm_user = User.objects.create_user(email="bdm@rijksoverheid.nl")
        Colleague.objects.create(name="Bdm", email="bdm@rijksoverheid.nl", source="wies", user=bdm_user)
        grant_bdm(bdm_user)

        note = _team_event_privacy_note(self.assignment, self._request(bdm_user), self._removal_of("Ghost"))

        assert note == PRIVACY_BDM

    def test_placed_bdm_does_not_lend_their_own_note_to_anothers_event(self):
        # The viewer's own ended row carries PRIVACY_OWN; an event about a
        # different hidden colleague must not borrow that "jou" wording.
        bdm_user = User.objects.create_user(email="bdm@rijksoverheid.nl")
        bdm_colleague = Colleague.objects.create(name="Bdm", email="bdm@rijksoverheid.nl", source="wies", user=bdm_user)
        grant_bdm(bdm_user)
        _place(
            self.assignment,
            self.skill,
            bdm_colleague,
            start=self.today - timedelta(days=100),
            end=self.today - timedelta(days=10),
        )

        note = _team_event_privacy_note(self.assignment, self._request(bdm_user), self._removal_of("Ghost"))

        assert note == PRIVACY_BDM

    def test_own_event_keeps_the_own_note_for_the_placed_colleague(self):
        placed_user = User.objects.create_user(email="placed@rijksoverheid.nl")
        placed = Colleague.objects.create(
            name="Placed", email="placed@rijksoverheid.nl", source="wies", user=placed_user
        )
        _place(
            self.assignment,
            self.skill,
            placed,
            start=self.today - timedelta(days=100),
            end=self.today - timedelta(days=10),
        )

        note = _team_event_privacy_note(self.assignment, self._request(placed_user), self._removal_of("Placed"))

        assert note == PRIVACY_OWN

    def test_publicly_visible_names_get_no_note(self):
        bdm_user = User.objects.create_user(email="bdm@rijksoverheid.nl")
        Colleague.objects.create(name="Bdm", email="bdm@rijksoverheid.nl", source="wies", user=bdm_user)
        grant_bdm(bdm_user)

        note = _team_event_privacy_note(self.assignment, self._request(bdm_user), self._removal_of("Active Member"))

        assert note == ""
