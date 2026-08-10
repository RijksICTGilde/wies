from collections import Counter
from datetime import date

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)
from wies.core.views import PlacementListView, _get_top_org_options

User = get_user_model()


class FilterCombiningTestBase(TestCase):
    """Shared setup for filter combining tests."""

    def setUp(self):
        self.auth_user = User.objects.create_user(email="test@rijksoverheid.nl")
        self.skill_python = Skill.objects.create(name="Python Developer")
        self.skill_java = Skill.objects.create(name="Java Developer")

        # Label categories
        self.cat_thema = LabelCategory.objects.create(name="Thema", color="#DCE3EA")
        self.cat_expertise = LabelCategory.objects.create(name="Expertise", color="#00AA00")

        # Labels
        self.label_thema_a = Label.objects.create(name="Digitale weerbaarheid", category=self.cat_thema)
        self.label_thema_b = Label.objects.create(name="Artificiële intelligentie", category=self.cat_thema)
        self.label_expertise_a = Label.objects.create(name="AI", category=self.cat_expertise)
        self.label_expertise_b = Label.objects.create(name="Cloud en platform technologie", category=self.cat_expertise)

        # Orgs
        self.org_a = OrganizationUnit.objects.create(name="Org A", label="Org A")
        self.org_b = OrganizationUnit.objects.create(name="Org B", label="Org B")

    def _create_placement(self, colleague_name, skill, org=None, labels=None):
        """Create an active placement with given parameters."""
        colleague = Colleague.objects.create(
            name=colleague_name,
            email=f"{colleague_name.replace(' ', '').lower()}@rijksoverheid.nl",
            source="wies",
        )
        if labels:
            colleague.labels.add(*labels)

        assignment = Assignment.objects.create(
            name=f"Assignment for {colleague_name}",
            source="wies",
            start_date=date(2025, 1, 1),
            end_date=date(2030, 1, 1),
        )
        if org:
            AssignmentOrganizationUnit.objects.create(assignment=assignment, organization=org)

        service = Service.objects.create(assignment=assignment, description="Service", skill=skill, source="wies")
        return Placement.objects.create(colleague=colleague, service=service, period_source="ASSIGNMENT", source="wies")

    def _get_placement_ids(self, params: dict) -> list[int]:
        factory = RequestFactory()
        request = factory.get("/", params)
        request.user = self.auth_user
        view = PlacementListView()
        view.request = request
        return list(view.get_queryset().values_list("id", flat=True))

    def _get_org_quick_options(self, params: dict) -> list[dict]:
        """Return the opdrachtgever quick options from the rendered context."""
        factory = RequestFactory()
        request = factory.get("/", params)
        request.user = self.auth_user
        view = PlacementListView()
        view.request = request
        view.kwargs = {}
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        org_group = next(g for g in context["filter_groups"] if g.get("type") == "modal")
        return org_group["top_options"]


class LabelORWithinCategoryTest(FilterCombiningTestBase):
    """Labels within the same category combine with OR."""

    def test_single_label_filters_correctly(self):
        p_thema_a = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a])
        p_thema_b = self._create_placement("Bob", self.skill_python, labels=[self.label_thema_b])
        p_none = self._create_placement("Charlie", self.skill_python)

        ids = self._get_placement_ids({"labels": str(self.label_thema_a.public_id)})

        assert p_thema_a.id in ids
        assert p_thema_b.id not in ids
        assert p_none.id not in ids

    def test_two_labels_same_category_use_or(self):
        """Selecting two Thema labels should show colleagues with EITHER label."""
        p_thema_a = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a])
        p_thema_b = self._create_placement("Bob", self.skill_python, labels=[self.label_thema_b])
        p_none = self._create_placement("Charlie", self.skill_python)

        ids = self._get_placement_ids(
            {"labels": [str(self.label_thema_a.public_id), str(self.label_thema_b.public_id)]}
        )

        assert p_thema_a.id in ids, "Thema-A colleague should match (OR within Thema)"
        assert p_thema_b.id in ids, "Thema-B colleague should match (OR within Thema)"
        assert p_none.id not in ids, "Unlabelled colleague should not match"

    def test_colleague_with_both_labels_appears_once(self):
        """Colleague with both labels in same category should appear exactly once."""
        p_both = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a, self.label_thema_b])

        ids = self._get_placement_ids(
            {"labels": [str(self.label_thema_a.public_id), str(self.label_thema_b.public_id)]}
        )

        assert ids.count(p_both.id) == 1, "Should appear exactly once, not duplicated"


class LabelANDBetweenCategoriesTest(FilterCombiningTestBase):
    """Labels from different categories combine with AND."""

    def test_labels_from_different_categories_use_and(self):
        """Selecting a Thema + an Expertise label should only show colleagues with BOTH."""
        p_both = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a, self.label_expertise_a])
        p_thema_only = self._create_placement("Bob", self.skill_python, labels=[self.label_thema_a])
        p_expertise_only = self._create_placement("Charlie", self.skill_python, labels=[self.label_expertise_a])

        ids = self._get_placement_ids(
            {"labels": [str(self.label_thema_a.public_id), str(self.label_expertise_a.public_id)]}
        )

        assert p_both.id in ids, "Colleague with both labels should match"
        assert p_thema_only.id not in ids, "Colleague with only the Thema label should not match"
        assert p_expertise_only.id not in ids, "Colleague with only the Expertise label should not match"

    def test_or_within_and_between(self):
        """Thema-A + Thema-B (OR) combined with an Expertise label (AND).

        Should match colleagues who have (Thema-A OR Thema-B) AND the Expertise label.
        """
        p_a_exp = self._create_placement(
            "Alice", self.skill_python, labels=[self.label_thema_a, self.label_expertise_a]
        )
        p_b_exp = self._create_placement("Bob", self.skill_python, labels=[self.label_thema_b, self.label_expertise_a])
        p_thema_only = self._create_placement("Charlie", self.skill_python, labels=[self.label_thema_a])
        p_expertise_only = self._create_placement("Dave", self.skill_python, labels=[self.label_expertise_a])

        ids = self._get_placement_ids(
            {
                "labels": [
                    str(self.label_thema_a.public_id),
                    str(self.label_thema_b.public_id),
                    str(self.label_expertise_a.public_id),
                ]
            }
        )

        assert p_a_exp.id in ids, "Thema-A + Expertise should match"
        assert p_b_exp.id in ids, "Thema-B + Expertise should match"
        assert p_thema_only.id not in ids, "Thema-A without the Expertise label should not match"
        assert p_expertise_only.id not in ids, "Expertise without a Thema label should not match"


class RolFilterCombiningTest(FilterCombiningTestBase):
    """Rol filter uses OR (multi-select) and ANDs with other filters."""

    def test_single_rol_filter(self):
        p_python = self._create_placement("Alice", self.skill_python)
        p_java = self._create_placement("Bob", self.skill_java)

        ids = self._get_placement_ids({"rol": str(self.skill_python.public_id)})

        assert p_python.id in ids
        assert p_java.id not in ids

    def test_multiple_rol_filters_use_or(self):
        """Selecting Python + Java should show placements with EITHER skill."""
        p_python = self._create_placement("Alice", self.skill_python)
        p_java = self._create_placement("Bob", self.skill_java)

        ids = self._get_placement_ids({"rol": [str(self.skill_python.public_id), str(self.skill_java.public_id)]})

        assert p_python.id in ids
        assert p_java.id in ids

    def test_rol_and_label_combine_with_and(self):
        """Rol=Python AND a Thema label should only show placements matching both."""
        p_python_label = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a])
        p_python_no_label = self._create_placement("Bob", self.skill_python)
        p_java_label = self._create_placement("Charlie", self.skill_java, labels=[self.label_thema_a])

        ids = self._get_placement_ids(
            {"rol": str(self.skill_python.public_id), "labels": str(self.label_thema_a.public_id)}
        )

        assert p_python_label.id in ids, "Python + label should match"
        assert p_python_no_label.id not in ids, "Python without the label should not match"
        assert p_java_label.id not in ids, "Java + label should not match (wrong rol)"


class OrgFilterCombiningTest(FilterCombiningTestBase):
    """Org filter ANDs with other filters."""

    def test_org_and_rol_combine_with_and(self):
        p_org_a_python = self._create_placement("Alice", self.skill_python, org=self.org_a)
        p_org_a_java = self._create_placement("Bob", self.skill_java, org=self.org_a)
        p_org_b_python = self._create_placement("Charlie", self.skill_python, org=self.org_b)

        ids = self._get_placement_ids({"org_self": str(self.org_a.public_id), "rol": str(self.skill_python.public_id)})

        assert p_org_a_python.id in ids, "Org A + Python should match"
        assert p_org_a_java.id not in ids, "Org A + Java should not match"
        assert p_org_b_python.id not in ids, "Org B + Python should not match"

    def test_org_and_label_combine_with_and(self):
        p_org_a_label = self._create_placement("Alice", self.skill_python, org=self.org_a, labels=[self.label_thema_a])
        p_org_a_no_label = self._create_placement("Bob", self.skill_python, org=self.org_a)
        p_org_b_label = self._create_placement(
            "Charlie", self.skill_python, org=self.org_b, labels=[self.label_thema_a]
        )

        ids = self._get_placement_ids(
            {"org_self": str(self.org_a.public_id), "labels": str(self.label_thema_a.public_id)}
        )

        assert p_org_a_label.id in ids, "Org A + label should match"
        assert p_org_a_no_label.id not in ids, "Org A without label should not match"
        assert p_org_b_label.id not in ids, "Org B + label should not match (wrong org)"


class TopOrgOptionsTest(FilterCombiningTestBase):
    """`_get_top_org_options` always surfaces selected orgs — including a
    "direct onder…" self-node (org_self) and an org-type group (org_type) —
    as checked quick options, each carrying its own param. Regression for the
    self/type selections that previously got no checkmark in the sidebar list.
    """

    def test_org_selection_is_checked_with_org_param(self):
        # Selections come in as internal ids; the rendered option value is the public_id.
        opts = _get_top_org_options("placements", [], {self.org_a.id})
        match = [o for o in opts if o["value"] == str(self.org_a.public_id)]
        assert match, "selected org must appear as a quick option"
        assert match[0]["param"] == "org"
        assert match[0]["selected"] is True

    def test_self_selection_is_checked_with_org_self_param(self):
        opts = _get_top_org_options("placements", [], set(), selected_self_ids={self.org_a.id})
        match = [o for o in opts if o["param"] == "org_self" and o["value"] == str(self.org_a.public_id)]
        assert match, "selected self-node must appear as a quick option"
        assert match[0]["selected"] is True
        assert "(direct)" in match[0]["label"]

    def test_type_selection_is_checked_with_org_type_param(self):
        opts = _get_top_org_options("placements", [], set(), selected_type_labels={"Ministerie"})
        match = [o for o in opts if o["param"] == "org_type" and o["value"] == "Ministerie"]
        assert match, "selected org-type must appear as a quick option"
        assert match[0]["selected"] is True

    def test_selecting_does_not_reorder_by_selection(self):
        # Org B has the higher count, Org A none. Selecting the low-count Org A
        # must NOT push it above Org B: the order is count/label, not "selected
        # first", so a tick never makes a row jump to the top.
        self._create_placement("Alice", self.skill_python, org=self.org_b)
        self._create_placement("Bob", self.skill_python, org=self.org_b)
        opts = _get_top_org_options("placements", [], {self.org_a.id})
        values = [o["value"] for o in opts if o["param"] == "org"]
        assert values.index(str(self.org_b.public_id)) < values.index(str(self.org_a.public_id))

    def test_selecting_outside_top_n_appends_without_dropping_a_top_option(self):
        # Five orgs by descending count; with limit=2 the top-N is org0, org1.
        orgs = [OrganizationUnit.objects.create(name=f"O{i}", label=f"O{i}") for i in range(5)]
        counts = Counter({o.id: c for o, c in zip(orgs, [5, 4, 3, 2, 1], strict=True)})
        top = [orgs[0].id, orgs[1].id]

        baseline = _get_top_org_options("placements", [], set(), org_counts=counts, limit=2)
        base_ids = [o["value"] for o in baseline if o["param"] == "org"]

        # Selecting the lowest-count org (outside the top-2) must keep both top
        # options and append the pick — the list grows, nothing is dropped.
        picked = _get_top_org_options("placements", [], {orgs[4].id}, org_counts=counts, limit=2)
        picked_ids = [o["value"] for o in picked if o["param"] == "org"]

        for top_id in top:
            assert str(OrganizationUnit.objects.get(id=top_id).public_id) in picked_ids
        assert str(orgs[4].public_id) in picked_ids
        assert len(picked_ids) == len(base_ids) + 1


class OrgQuickCountsTest(FilterCombiningTestBase):
    """Opdrachtgever quick-option counts reflect the OTHER active filters
    (like rol/labels), not a global baseline. Regression for stale counts.
    """

    def test_org_count_reflects_active_rol_filter(self):
        # Org A: one Python placement + one Java placement (count 2 unfiltered).
        self._create_placement("Alice", self.skill_python, org=self.org_a)
        self._create_placement("Bob", self.skill_java, org=self.org_a)

        baseline = {o["value"]: o["count"] for o in self._get_org_quick_options({})}
        assert baseline.get(str(self.org_a.public_id)) == 2, "unfiltered count should be 2"

        # With rol=Python active, Org A's count must drop to 1.
        with_rol = {
            o["value"]: o["count"] for o in self._get_org_quick_options({"rol": str(self.skill_python.public_id)})
        }
        assert with_rol.get(str(self.org_a.public_id)) == 1, "count must reflect the active rol filter"


class AllFiltersCombinedTest(FilterCombiningTestBase):
    """Test all filter types combined: org AND rol AND labels (OR within, AND between)."""

    def test_all_filters_combined(self):
        """org + rol + labels from two categories should all AND together."""
        # This colleague matches everything
        p_match = self._create_placement(
            "Alice", self.skill_python, org=self.org_a, labels=[self.label_thema_a, self.label_expertise_a]
        )
        # Wrong org
        p_wrong_org = self._create_placement(
            "Bob", self.skill_python, org=self.org_b, labels=[self.label_thema_a, self.label_expertise_a]
        )
        # Wrong rol
        p_wrong_rol = self._create_placement(
            "Charlie", self.skill_java, org=self.org_a, labels=[self.label_thema_a, self.label_expertise_a]
        )
        # Missing expertise label
        p_missing_label = self._create_placement("Dave", self.skill_python, org=self.org_a, labels=[self.label_thema_a])

        ids = self._get_placement_ids(
            {
                "org_self": str(self.org_a.public_id),
                "rol": str(self.skill_python.public_id),
                "labels": [str(self.label_thema_a.public_id), str(self.label_expertise_a.public_id)],
            }
        )

        assert p_match.id in ids, "Should match all filters"
        assert p_wrong_org.id not in ids, "Wrong org should be excluded"
        assert p_wrong_rol.id not in ids, "Wrong rol should be excluded"
        assert p_missing_label.id not in ids, "Missing cross-category label should be excluded"

    def test_no_filters_returns_all(self):
        """Without any filters, all active placements are returned."""
        p1 = self._create_placement("Alice", self.skill_python, org=self.org_a, labels=[self.label_thema_a])
        p2 = self._create_placement("Bob", self.skill_java, org=self.org_b, labels=[self.label_thema_b])
        p3 = self._create_placement("Charlie", self.skill_python)

        ids = self._get_placement_ids({})

        assert p1.id in ids
        assert p2.id in ids
        assert p3.id in ids

    def test_invalid_label_id_returns_empty(self):
        """Non-existent label ID should return no results."""
        self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a])

        ids = self._get_placement_ids({"labels": "99999"})

        assert len(ids) == 0, "Non-existent label should return no results"
