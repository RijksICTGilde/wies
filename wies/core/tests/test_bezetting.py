import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Label, LabelCategory, Placement, Service, Skill, Suborganization
from wies.core.roles import setup_roles
from wies.core.services.occupancy import (
    GILDE_CATEGORY,
    HORIZON_AHEAD_DAYS,
    HORIZON_BACK_DAYS,
    NARROW_BAR_PCT,
    colleague_occupancy,
)

User = get_user_model()


def _consultant(name, email, **kwargs):
    """Create a Colleague whose linked user is in the Consultant group, so it
    appears on the Bezetting page. Requires setup_roles() to have run."""
    user = User.objects.create(email=email)
    user.groups.add(Group.objects.get(name="Consultant"))
    return Colleague.objects.create(name=name, email=email, source="wies", user=user, **kwargs)


def _placement(colleague, name, start, end, role=None):
    """Create an assignment + service + placement with placement-level dates."""
    assignment = Assignment.objects.create(name=name, source="wies")
    skill = Skill.objects.get_or_create(name=role)[0] if role else None
    service = Service.objects.create(assignment=assignment, description=name, skill=skill, source="wies")
    return Placement.objects.create(
        colleague=colleague,
        service=service,
        period_source="PLACEMENT",
        specific_start_date=start,
        specific_end_date=end,
        source="wies",
    )


class BezettingAuthTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.url = reverse("bezetting")

        self.bdm_user = User.objects.create(email="bdm@rijksoverheid.nl", first_name="BDM", last_name="User")
        self.bdm_user.groups.add(Group.objects.get(name="Business Development Manager"))

        self.regular_user = User.objects.create(email="regular@rijksoverheid.nl")

        self.consultant = User.objects.create(email="consultant@rijksoverheid.nl")
        self.consultant.groups.add(Group.objects.get(name="Consultant"))

    def test_anonymous_redirected(self):
        response = self.client.get(self.url)
        assert response.status_code == 302
        assert "/geen-toegang/" in response.url

    def test_non_bdm_redirected(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        assert response.status_code == 302
        assert "/geen-toegang/" in response.url

    def test_consultant_redirected(self):
        # Consultant is a role but not the business-management one.
        self.client.force_login(self.consultant)
        response = self.client.get(self.url)
        assert response.status_code == 302
        assert "/geen-toegang/" in response.url

    def test_bdm_gets_page(self):
        self.client.force_login(self.bdm_user)
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert b"Bezetting" in response.content

    @override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
    def test_staff_gets_page(self):
        # Support staff (STAFF_EMAILS) may reach the business-management section too,
        # even without the Business Development Manager role.
        staff = User.objects.create(email="staff@rijksoverheid.nl")
        self.client.force_login(staff)
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert b"Bezetting" in response.content


class BezettingPanelTest(TestCase):
    """The side panel opens colleague/opdracht/plaatsing details, never the full page."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.url = reverse("bezetting")
        self.bdm_user = User.objects.create(email="bdm@rijksoverheid.nl")
        self.bdm_user.groups.add(Group.objects.get(name="Business Development Manager"))
        self.client.force_login(self.bdm_user)

        today = timezone.now().date()
        self.colleague = _consultant("Fred Full", "f@x.nl")
        self.assignment = Assignment.objects.create(
            name="Optimalisatie API",
            source="wies",
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=20),
        )
        self.service = Service.objects.create(assignment=self.assignment, description="dev", source="wies")
        self.placement = Placement.objects.create(colleague=self.colleague, service=self.service, source="wies")
        self.panel_headers = {"hx-request": "true", "hx-target": "side-panel-content"}

    def test_collega_panel_returns_colleague_fragment(self):
        response = self.client.get(self.url, {"collega": str(self.colleague.public_id)}, headers=self.panel_headers)
        assert response.status_code == 200
        assert b"Fred Full" in response.content
        # Not the full page swapped into the panel.
        assert b"bezetting-timeline" not in response.content

    def test_opdracht_panel_returns_assignment_fragment(self):
        response = self.client.get(self.url, {"opdracht": str(self.assignment.public_id)}, headers=self.panel_headers)
        assert response.status_code == 200
        assert b"Optimalisatie API" in response.content
        assert b"bezetting-timeline" not in response.content

    def test_plaatsing_panel_returns_placement_fragment(self):
        response = self.client.get(self.url, {"plaatsing": str(self.placement.public_id)}, headers=self.panel_headers)
        assert response.status_code == 200
        assert b"bezetting-timeline" not in response.content


class BezettingNavVisibilityTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.bdm_user = User.objects.create(email="bdm@rijksoverheid.nl")
        self.bdm_user.groups.add(Group.objects.get(name="Business Development Manager"))
        self.regular_user = User.objects.create(email="regular@rijksoverheid.nl")

    def test_tab_visible_for_bdm(self):
        self.client.force_login(self.bdm_user)
        # The home page renders the base nav.
        response = self.client.get(reverse("home"))
        assert b"Business management" in response.content

    def test_tab_hidden_for_non_bdm(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("home"))
        assert b"Business management" not in response.content

    @override_settings(STAFF_EMAILS=["staff@rijksoverheid.nl"])
    def test_tab_visible_for_staff(self):
        staff = User.objects.create(email="staff@rijksoverheid.nl")
        self.client.force_login(staff)
        response = self.client.get(reverse("home"))
        assert b"Business management" in response.content


class OccupancyServiceTest(TestCase):
    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.bench = _consultant("Bea Bank", "bea@x.nl")
        self.full = _consultant("Fred Full", "fred@x.nl")

    def test_colleague_without_active_placement_is_bench(self):
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.bench.id].bucket == "bench"

    def test_colleague_with_active_placement_is_full(self):
        _placement(self.full, "Actieve opdracht", self.today - timedelta(days=10), self.today + timedelta(days=30))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.full.id].bucket == "full"

    def test_completed_placement_leaves_colleague_on_bench(self):
        # A placement that already ended does not count as active.
        _placement(self.bench, "Afgerond", self.today - timedelta(days=60), self.today - timedelta(days=10))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.bench.id].bucket == "bench"

    def test_ends_soon_flag(self):
        _placement(self.full, "Loopt bijna af", self.today - timedelta(days=10), self.today + timedelta(days=20))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.full.id].ends_soon is True

    def test_ends_soon_false_for_far_end(self):
        _placement(self.full, "Loopt lang door", self.today - timedelta(days=10), self.today + timedelta(days=200))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.full.id].ends_soon is False

    def test_only_the_ending_placement_is_flagged_ends_soon(self):
        """The flag belongs to the placement, not the person.

        Someone on two opdrachten can have one wrapping up while the other runs
        on for months; a single flag beside their name claimed they were all
        stopping.
        """
        _placement(self.full, "Loopt bijna af", self.today - timedelta(days=10), self.today + timedelta(days=20))
        _placement(self.full, "Loopt lang door", self.today - timedelta(days=10), self.today + timedelta(days=200))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        flagged = {seg.assignment_name: seg.ends_soon for seg in rows[self.full.id].segments}
        assert flagged == {"Loopt bijna af": True, "Loopt lang door": False}
        # The row still reports that something of theirs ends soon.
        assert rows[self.full.id].ends_soon is True

    def test_a_completed_placement_is_never_flagged_ends_soon(self):
        """Already over is not "ending soon", however recent."""
        _placement(self.full, "Afgerond", self.today - timedelta(days=60), self.today - timedelta(days=5))
        _placement(self.full, "Loopt lang door", self.today - timedelta(days=10), self.today + timedelta(days=200))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert all(seg.ends_soon is False for seg in rows[self.full.id].segments)

    def test_ending_level_bands(self):
        """Four urgency bands, so a bar's colour ranks how soon it ends."""
        for days, expected in (
            (5, "critical"),
            (31, "critical"),
            (32, "warning"),
            (62, "warning"),
            (63, "attention"),
            (93, "attention"),
            (94, "calm"),
            (200, "calm"),
        ):
            colleague = _consultant(f"Eind {days}", f"eind{days}@x.nl")
            _placement(
                colleague, f"Opdracht {days}", self.today - timedelta(days=10), self.today + timedelta(days=days)
            )
            rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
            level = rows[colleague.id].segments[0].ending_level
            assert level == expected, f"{days} dagen: {level} != {expected}"

    def test_only_active_placements_carry_an_ending_level(self):
        """A planned placement has not started and a finished one is over, so
        neither says anything about how soon this colleague frees up."""
        planned = _consultant("Nog Beginnen", "planned@x.nl")
        _placement(planned, "Start later", self.today + timedelta(days=10), self.today + timedelta(days=20))
        done = _consultant("Al Klaar", "done@x.nl")
        _placement(done, "Afgerond", self.today - timedelta(days=40), self.today - timedelta(days=5))

        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[planned.id].segments[0].ending_level == "calm"
        assert rows[done.id].segments[0].ending_level == "calm"

    def test_an_open_ended_placement_is_calm(self):
        """No end date is not urgent."""
        colleague = _consultant("Zonder Eind", "open@x.nl")
        _placement(colleague, "Doorlopend", self.today - timedelta(days=10), None)
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[colleague.id].segments[0].ending_level == "calm"

    def test_a_placed_colleague_shows_their_current_role(self):
        _placement(
            self.full, "Actief", self.today - timedelta(days=10), self.today + timedelta(days=30), role="Scrum Master"
        )
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.full.id].role == "Scrum Master"
        assert rows[self.full.id].role_is_past is False

    def test_a_bench_colleague_falls_back_to_the_role_of_their_last_placement(self):
        """No current role to show, and their last one is the best answer to
        "what does this person do" — flagged so it is not passed off as current."""
        _placement(
            self.bench, "Oud", self.today - timedelta(days=100), self.today - timedelta(days=40), role="AI Consultant"
        )
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.bench.id].role == "AI Consultant"
        assert rows[self.bench.id].role_is_past is True

    def test_the_bench_role_comes_from_the_most_recent_placement(self):
        _placement(
            self.bench, "Ouder", self.today - timedelta(days=300), self.today - timedelta(days=200), role="Oude Rol"
        )
        _placement(
            self.bench, "Recenter", self.today - timedelta(days=100), self.today - timedelta(days=40), role="Nieuwe Rol"
        )
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.bench.id].role == "Nieuwe Rol"

    def test_a_service_without_a_skill_leaves_the_role_empty(self):
        """Six of the demo services have no skill, so the empty role is a real
        case, not a theoretical one."""
        _placement(self.full, "Zonder rol", self.today - timedelta(days=10), self.today + timedelta(days=30))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.full.id].role == ""
        assert rows[self.full.id].segments[0].role == ""

    def test_bench_bar_runs_from_the_last_end_up_to_today(self):
        """The free stretch is drawn on the same axis as the placements."""
        _placement(self.bench, "Oud", self.today - timedelta(days=60), self.today - timedelta(days=30))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        row = rows[self.bench.id]
        left, width = row.bench_bar
        assert row.bench_bar_clipped is False
        # Ends at today, which sits at the horizon's back/total ratio.
        today_pct = HORIZON_BACK_DAYS / (HORIZON_BACK_DAYS + HORIZON_AHEAD_DAYS) * 100
        assert abs((left + width) - today_pct) < 0.5

    def test_a_stretch_older_than_the_horizon_is_clipped_at_the_left_edge(self):
        """Most people on the bench have been free longer than the axis reaches
        back; without clipping every one of those bars would look the same."""
        _placement(self.bench, "Lang geleden", self.today - timedelta(days=500), self.today - timedelta(days=400))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        row = rows[self.bench.id]
        assert row.bench_bar[0] == 0.0
        assert row.bench_bar_clipped is True

    def test_a_colleague_never_placed_gets_no_bar(self):
        never = _consultant("Nooit", "nooit2@x.nl")
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[never.id].bench_bar is None
        assert rows[never.id].bench_bar_clipped is False

    def test_a_placed_colleague_gets_no_free_bar(self):
        """Being free is a bench thing; a placed row has nothing to draw."""
        _placement(self.full, "Actief", self.today - timedelta(days=10), self.today + timedelta(days=30))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.full.id].bench_bar is None

    def test_a_narrow_bar_drops_its_label(self):
        """Below the threshold the label is all ellipsis and no word, so it
        renders a stray "I..." beside a wider bar instead of a name."""
        # Two weeks out of a ~six month horizon: well under the threshold.
        _placement(self.full, "Heel Kort", self.today - timedelta(days=3), self.today + timedelta(days=11))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        segment = next(s for s in rows[self.full.id].segments if s.assignment_name == "Heel Kort")
        assert segment.width_pct < NARROW_BAR_PCT
        assert segment.too_narrow is True

    def test_a_wide_bar_keeps_its_label(self):
        _placement(self.full, "Lang Genoeg", self.today - timedelta(days=30), self.today + timedelta(days=90))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        segment = next(s for s in rows[self.full.id].segments if s.assignment_name == "Lang Genoeg")
        assert segment.too_narrow is False

    def test_sorting_bench_before_full(self):
        _placement(self.full, "Actief", self.today - timedelta(days=10), self.today + timedelta(days=30))
        rows = colleague_occupancy(self.today)
        buckets = [r.bucket for r in rows]
        # No 'full' may appear before a 'bench'.
        first_full = buckets.index("full")
        assert "bench" not in buckets[first_full:]

    def test_full_sorted_by_soonest_end(self):
        soon = _consultant("Sam Soon", "sam@x.nl")
        later = _consultant("Lea Later", "lea@x.nl")
        _placement(soon, "Soon", self.today - timedelta(days=5), self.today + timedelta(days=10))
        _placement(later, "Later", self.today - timedelta(days=5), self.today + timedelta(days=100))
        rows = [r for r in colleague_occupancy(self.today) if r.bucket == "full"]
        order = [r.colleague.id for r in rows]
        assert order.index(soon.id) < order.index(later.id)

    def test_segments_built_for_placements(self):
        _placement(self.full, "Met tijdlijn", self.today - timedelta(days=10), self.today + timedelta(days=30))
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        row = rows[self.full.id]
        assert len(row.segments) == 1
        assert row.segments[0].assignment_name == "Met tijdlijn"
        assert row.segments[0].phase == "active"


class OccupancyMerkFilterTest(TestCase):
    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.digi = Suborganization.objects.create(name="Digi Gilde")
        self.mindful = Suborganization.objects.create(name="Mindful Rijk")
        self.a = _consultant("Aisha Digi", "a@x.nl", suborganization=self.digi)
        self.b = _consultant("Bram Mindful", "b@x.nl", suborganization=self.mindful)
        self.c = _consultant("Cora Zonder", "c@x.nl")

    def _ids(self, merk_ids):
        return {r.colleague.id for r in colleague_occupancy(self.today, merk_ids=merk_ids)}

    def test_no_filter_shows_everyone(self):
        assert self._ids(None) == {self.a.id, self.b.id, self.c.id}

    def test_single_merk_filters(self):
        assert self._ids([self.digi.id]) == {self.a.id}

    def test_multiple_merken_or(self):
        assert self._ids([self.digi.id, self.mindful.id]) == {self.a.id, self.b.id}


class BezettingMerkFilterViewTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.url = reverse("bezetting")
        # onboarding_completed_at set so the onboarding wizard (which lists every
        # merk) does not render and mask the filter-bar assertions.
        self.bdm_user = User.objects.create(email="bdm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.bdm_user.groups.add(Group.objects.get(name="Business Development Manager"))
        self.client.force_login(self.bdm_user)

        self.digi = Suborganization.objects.create(name="Digi Gilde")
        self.mindful = Suborganization.objects.create(name="Mindful Rijk")
        self.a = _consultant("Aisha Digi", "a@x.nl", suborganization=self.digi)
        self.b = _consultant("Bram Mindful", "b@x.nl", suborganization=self.mindful)

    def test_filter_bar_lists_merken(self):
        response = self.client.get(self.url)
        # The merk facet renders as a select-multi group in the shared filter sheet.
        assert b'data-name="merk"' in response.content
        assert b"Digi Gilde" in response.content
        assert b"Mindful Rijk" in response.content

    def test_unused_merk_not_offered(self):
        # A merk with no colleagues is not a useful filter and must not appear
        # as a checkbox option. (Assert on its public_id so the onboarding wizard,
        # which lists every merk by name, cannot mask the check.)
        unused = Suborganization.objects.create(name="Ongebruikt Merk")
        response = self.client.get(self.url)
        assert str(unused.public_id).encode() not in response.content
        # The used merken are still offered.
        assert str(self.digi.public_id).encode() in response.content

    def test_filtering_hides_other_merk(self):
        response = self.client.get(self.url, {"merk": str(self.digi.public_id)})
        assert b"Aisha Digi" in response.content
        assert b"Bram Mindful" not in response.content

    def test_unknown_merk_token_ignored(self):
        # A bogus public_id resolves to no ids: an empty filter shows everyone.
        response = self.client.get(self.url, {"merk": "not-a-real-uuid"})
        assert response.status_code == 200
        assert b"Aisha Digi" in response.content
        assert b"Bram Mindful" in response.content


class OccupancyLabelFilterTest(TestCase):
    def setUp(self):
        setup_roles()
        self.today = timezone.now().date()
        self.thema = LabelCategory.objects.create(name="Thema", color="#0066CC")
        self.niveau = LabelCategory.objects.create(name="Niveau", color="#00AA00")
        self.ai = Label.objects.create(name="AI", category=self.thema)
        self.data = Label.objects.create(name="Data", category=self.thema)
        self.senior = Label.objects.create(name="Senior", category=self.niveau)

        # Aïsha: AI + Senior; Bram: Data; Cora: AI only.
        self.a = _consultant("Aisha", "a@x.nl")
        self.a.labels.add(self.ai, self.senior)
        self.b = _consultant("Bram", "b@x.nl")
        self.b.labels.add(self.data)
        self.c = _consultant("Cora", "c@x.nl")
        self.c.labels.add(self.ai)

    def _ids(self, labels_by_category):
        return {r.colleague.id for r in colleague_occupancy(self.today, labels_by_category=labels_by_category)}

    def test_no_filter_shows_everyone(self):
        assert self._ids(None) == {self.a.id, self.b.id, self.c.id}

    def test_or_within_category(self):
        # AI OR Data in Thema -> everyone with either.
        assert self._ids({self.thema.id: [self.ai.id, self.data.id]}) == {self.a.id, self.b.id, self.c.id}

    def test_single_label(self):
        assert self._ids({self.thema.id: [self.data.id]}) == {self.b.id}

    def test_and_between_categories(self):
        # Thema=AI AND Niveau=Senior -> only Aïsha (Cora has AI but no Senior).
        assert self._ids({self.thema.id: [self.ai.id], self.niveau.id: [self.senior.id]}) == {self.a.id}


class BezettingLabelFilterViewTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.url = reverse("bezetting")
        self.bdm_user = User.objects.create(email="bdm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.bdm_user.groups.add(Group.objects.get(name="Business Development Manager"))
        self.client.force_login(self.bdm_user)

        self.thema = LabelCategory.objects.create(name="Thema", color="#0066CC")
        self.ai = Label.objects.create(name="AI", category=self.thema)
        self.data = Label.objects.create(name="Data", category=self.thema)
        self.a = _consultant("Aisha AI", "a@x.nl")
        self.a.labels.add(self.ai)
        self.b = _consultant("Bram Data", "b@x.nl")
        self.b.labels.add(self.data)

    def test_category_dropdown_lists_used_labels(self):
        response = self.client.get(self.url)
        content = response.content
        assert b"Thema" in content
        assert str(self.ai.public_id).encode() in content
        assert str(self.data.public_id).encode() in content

    def test_filtering_on_label_hides_others(self):
        response = self.client.get(self.url, {"labels": str(self.ai.public_id)})
        assert b"Aisha AI" in response.content
        assert b"Bram Data" not in response.content

    def test_unused_label_not_offered(self):
        # A label on no colleague is not offered as a filter option.
        unused = Label.objects.create(name="Ongebruikt", category=self.thema)
        response = self.client.get(self.url)
        assert str(unused.public_id).encode() not in response.content

    def test_category_without_used_labels_absent(self):
        # A whole category whose labels are unused does not render a dropdown.
        empty_cat = LabelCategory.objects.create(name="LegeCategorie", color="#00AA00")
        Label.objects.create(name="X", category=empty_cat)
        response = self.client.get(self.url)
        assert b"LegeCategorie" not in response.content


class BezettingStatusFilterViewTest(TestCase):
    """The summary cards act as status filters (bench / full / ends_soon),
    independent OR-toggles applied in-memory on the built rows."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.url = reverse("bezetting")
        self.today = timezone.now().date()
        self.bdm_user = User.objects.create(email="bdm@rijksoverheid.nl", onboarding_completed_at=timezone.now())
        self.bdm_user.groups.add(Group.objects.get(name="Business Development Manager"))
        self.client.force_login(self.bdm_user)

        self.bench = _consultant("Bea Bank", "bea@x.nl")
        self.full = _consultant("Fred Full", "fred@x.nl")
        _placement(self.full, "Loopt lang door", self.today - timedelta(days=10), self.today + timedelta(days=200))
        self.ending = _consultant("Ellen Eind", "ellen@x.nl")
        _placement(self.ending, "Loopt bijna af", self.today - timedelta(days=10), self.today + timedelta(days=20))

    def test_bench_status_shows_only_bench(self):
        response = self.client.get(self.url, {"status": "bench"})
        assert b"Bea Bank" in response.content
        assert b"Fred Full" not in response.content
        assert b"Ellen Eind" not in response.content

    def test_full_status_shows_all_placed(self):
        # ends_soon colleagues are also 'full', so both placed rows appear.
        response = self.client.get(self.url, {"status": "full"})
        assert b"Bea Bank" not in response.content
        assert b"Fred Full" in response.content
        assert b"Ellen Eind" in response.content

    def test_ends_soon_status_is_subset_of_full(self):
        response = self.client.get(self.url, {"status": "ends_soon"})
        assert b"Ellen Eind" in response.content
        assert b"Fred Full" not in response.content
        assert b"Bea Bank" not in response.content

    def test_statuses_compose_as_union(self):
        # bench OR ends_soon: the bench row and the ending row, not the far-future one.
        response = self.client.get(self.url, {"status": ["bench", "ends_soon"]})
        assert b"Bea Bank" in response.content
        assert b"Ellen Eind" in response.content
        assert b"Fred Full" not in response.content

    def test_counts_stay_unfiltered_when_status_active(self):
        # Cards are a stable dashboard: the totals do not shrink to the filtered set.
        # With only the bench row shown, the 'volledig ingezet' card must still read
        # its full population count (2). Match the count and its label within one
        # card, tolerating the markup between them.
        response = self.client.get(self.url, {"status": "bench"})
        content = response.content.decode()
        assert re.search(r">2</span>.*?volledig ingezet", content, re.DOTALL)
        assert re.search(r">1</span>.*?op de bank", content, re.DOTALL)

    def test_empty_result_uses_the_shared_empty_state(self):
        """An nldd-inline-dialog, like the other lists: a bare paragraph read as body copy."""
        # bench and ends_soon are disjoint (a bench colleague has no placement to
        # end), so asking for both at once selects nobody.
        Placement.objects.all().delete()
        response = self.client.get(self.url, {"status": "ends_soon"})
        content = response.content.decode()
        assert "<nldd-inline-dialog" in content
        assert "Geen collega&#39;s gevonden" in content or "Geen collega's gevonden" in content

    def test_bench_and_placed_are_separate_sections(self):
        """Bench first: an unstaffed colleague is what this page is scanned for."""
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "Op de bank (1)" in content
        assert "Ingezet (2)" in content
        assert content.index("Op de bank") < content.index("Ingezet (")
        # Bench rows are compact, placed rows are not.
        assert "bezetting-row--compact" in content

    def test_a_bench_colleague_still_gets_a_bar_for_work_already_booked(self):
        """The reason bench rows keep a timeline: a list of names cannot answer
        whether anything is lined up, which is the point of looking at the bench."""
        _placement(
            self.bench, "Start volgende maand", self.today + timedelta(days=30), self.today + timedelta(days=120)
        )
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        row = rows[self.bench.id]
        # Booked work does not make them placed today...
        assert row.bucket == "bench"
        # ...but it is on their row.
        assert [s.phase for s in row.segments] == ["planned"]

        content = self.client.get(self.url).content.decode()
        assert "Start volgende maand" in content

    def test_bench_strip_reports_how_long_someone_has_been_free(self):
        _placement(self.bench, "Afgerond", self.today - timedelta(days=400), self.today - timedelta(days=200))
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "vrij" in content

    def test_a_colleague_who_was_never_placed_does_not_claim_a_free_since_date(self):
        """No placement on record is a different thing from a long wait, and
        sorting a None alongside ints used to raise."""
        never = _consultant("Nooit Ingezet", "nooit@x.nl")
        response = self.client.get(self.url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "nog niet ingezet" in content
        assert never.name in content

    def test_rows_show_only_the_gilde_category_as_chips(self):
        """The gilde is the subdivision this page is read by; the full expertise
        list would fill the row, so those stay in the filter sheet."""
        gilde = LabelCategory.objects.create(name=GILDE_CATEGORY, color="#DCE3EA")
        expertise = LabelCategory.objects.create(name="Expertise", color="#B3D7EE")
        self.bench.labels.add(Label.objects.create(name="ICT", category=gilde))
        self.bench.labels.add(Label.objects.create(name="Security en privacy", category=expertise))

        content = self.client.get(self.url).content.decode()
        # Category colour, not a hardcoded one: #DCE3EA maps to neutral.
        assert 'color="neutral" text="ICT"' in content
        # The expertise label is still offered in the filter sheet, so assert on
        # the chip markup rather than on the bare name appearing somewhere.
        assert 'text="Security en privacy"></nldd-tag>' not in content

    def test_a_colleague_without_a_gilde_label_gets_no_chip(self):
        LabelCategory.objects.create(name=GILDE_CATEGORY, color="#DCE3EA")
        rows = {r.colleague.id: r for r in colleague_occupancy(self.today)}
        assert rows[self.bench.id].gilde_labels == []
        assert self.client.get(self.url).status_code == 200

    def test_chips_do_not_cost_a_query_per_colleague(self):
        """Labels and merk are prefetched; without that this is an N+1.

        Enough colleagues that a per-row query would clearly exceed the fixed
        set: with only a handful the N+1 hides under any round threshold.
        """
        category = LabelCategory.objects.create(name="Expertise", color="#B3D7EE")
        label = Label.objects.create(name="AI", category=category)
        merk = Suborganization.objects.create(name="Rijks ICT Gilde")
        for i in range(25):
            colleague = _consultant(f"Chip {i}", f"chip{i}@x.nl")
            colleague.suborganization = merk
            colleague.save()
            colleague.labels.add(label)

        with CaptureQueriesContext(connection) as queries:
            rows = colleague_occupancy(self.today)
            for row in rows:
                list(row.colleague.labels.all())
                _ = row.colleague.suborganization

        assert len(rows) >= 25
        # A fixed handful, not one per colleague: without the prefetch this runs
        # well past 50.
        assert len(queries) < 15, f"{len(queries)} queries for {len(rows)} rows — prefetch lost?"

    def test_unknown_status_ignored(self):
        response = self.client.get(self.url, {"status": "not-a-status"})
        assert response.status_code == 200
        assert b"Bea Bank" in response.content
        assert b"Fred Full" in response.content

    def test_active_status_renders_dismiss_chip(self):
        response = self.client.get(self.url, {"status": "bench"})
        assert b'data-filter-name="status"' in response.content
        assert b'data-filter-value="bench"' in response.content
