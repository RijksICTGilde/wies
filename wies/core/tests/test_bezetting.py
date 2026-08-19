from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.models import Assignment, Colleague, Label, LabelCategory, Placement, Service, Suborganization
from wies.core.roles import setup_roles
from wies.core.services.occupancy import colleague_occupancy

User = get_user_model()


def _consultant(name, email, **kwargs):
    """Create a Colleague whose linked user is in the Consultant group, so it
    appears on the Bezetting page. Requires setup_roles() to have run."""
    user = User.objects.create(email=email)
    user.groups.add(Group.objects.get(name="Consultant"))
    return Colleague.objects.create(name=name, email=email, source="wies", user=user, **kwargs)


def _placement(colleague, name, start, end):
    """Create an assignment + service + placement with placement-level dates."""
    assignment = Assignment.objects.create(name=name, source="wies")
    service = Service.objects.create(assignment=assignment, description=name, source="wies")
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
