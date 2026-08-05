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
from wies.core.views import PlacementListView

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


class LabelORWithinCategoryTest(FilterCombiningTestBase):
    """Labels within the same category combine with OR."""

    def test_single_label_filters_correctly(self):
        p_thema_a = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a])
        p_thema_b = self._create_placement("Bob", self.skill_python, labels=[self.label_thema_b])
        p_none = self._create_placement("Charlie", self.skill_python)

        ids = self._get_placement_ids({"labels": str(self.label_thema_a.id)})

        assert p_thema_a.id in ids
        assert p_thema_b.id not in ids
        assert p_none.id not in ids

    def test_two_labels_same_category_use_or(self):
        """Selecting two Thema labels should show colleagues with EITHER label."""
        p_thema_a = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a])
        p_thema_b = self._create_placement("Bob", self.skill_python, labels=[self.label_thema_b])
        p_none = self._create_placement("Charlie", self.skill_python)

        ids = self._get_placement_ids({"labels": [str(self.label_thema_a.id), str(self.label_thema_b.id)]})

        assert p_thema_a.id in ids, "Thema-A colleague should match (OR within Thema)"
        assert p_thema_b.id in ids, "Thema-B colleague should match (OR within Thema)"
        assert p_none.id not in ids, "Unlabelled colleague should not match"

    def test_colleague_with_both_labels_appears_once(self):
        """Colleague with both labels in same category should appear exactly once."""
        p_both = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a, self.label_thema_b])

        ids = self._get_placement_ids({"labels": [str(self.label_thema_a.id), str(self.label_thema_b.id)]})

        assert ids.count(p_both.id) == 1, "Should appear exactly once, not duplicated"


class LabelANDBetweenCategoriesTest(FilterCombiningTestBase):
    """Labels from different categories combine with AND."""

    def test_labels_from_different_categories_use_and(self):
        """Selecting a Thema + an Expertise label should only show colleagues with BOTH."""
        p_both = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a, self.label_expertise_a])
        p_thema_only = self._create_placement("Bob", self.skill_python, labels=[self.label_thema_a])
        p_expertise_only = self._create_placement("Charlie", self.skill_python, labels=[self.label_expertise_a])

        ids = self._get_placement_ids({"labels": [str(self.label_thema_a.id), str(self.label_expertise_a.id)]})

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
            {"labels": [str(self.label_thema_a.id), str(self.label_thema_b.id), str(self.label_expertise_a.id)]}
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

        ids = self._get_placement_ids({"rol": str(self.skill_python.id)})

        assert p_python.id in ids
        assert p_java.id not in ids

    def test_multiple_rol_filters_use_or(self):
        """Selecting Python + Java should show placements with EITHER skill."""
        p_python = self._create_placement("Alice", self.skill_python)
        p_java = self._create_placement("Bob", self.skill_java)

        ids = self._get_placement_ids({"rol": [str(self.skill_python.id), str(self.skill_java.id)]})

        assert p_python.id in ids
        assert p_java.id in ids

    def test_rol_and_label_combine_with_and(self):
        """Rol=Python AND a Thema label should only show placements matching both."""
        p_python_label = self._create_placement("Alice", self.skill_python, labels=[self.label_thema_a])
        p_python_no_label = self._create_placement("Bob", self.skill_python)
        p_java_label = self._create_placement("Charlie", self.skill_java, labels=[self.label_thema_a])

        ids = self._get_placement_ids({"rol": str(self.skill_python.id), "labels": str(self.label_thema_a.id)})

        assert p_python_label.id in ids, "Python + label should match"
        assert p_python_no_label.id not in ids, "Python without the label should not match"
        assert p_java_label.id not in ids, "Java + label should not match (wrong rol)"


class OrgFilterCombiningTest(FilterCombiningTestBase):
    """Org filter ANDs with other filters."""

    def test_org_and_rol_combine_with_and(self):
        p_org_a_python = self._create_placement("Alice", self.skill_python, org=self.org_a)
        p_org_a_java = self._create_placement("Bob", self.skill_java, org=self.org_a)
        p_org_b_python = self._create_placement("Charlie", self.skill_python, org=self.org_b)

        ids = self._get_placement_ids({"org_self": str(self.org_a.id), "rol": str(self.skill_python.id)})

        assert p_org_a_python.id in ids, "Org A + Python should match"
        assert p_org_a_java.id not in ids, "Org A + Java should not match"
        assert p_org_b_python.id not in ids, "Org B + Python should not match"

    def test_org_and_label_combine_with_and(self):
        p_org_a_label = self._create_placement("Alice", self.skill_python, org=self.org_a, labels=[self.label_thema_a])
        p_org_a_no_label = self._create_placement("Bob", self.skill_python, org=self.org_a)
        p_org_b_label = self._create_placement(
            "Charlie", self.skill_python, org=self.org_b, labels=[self.label_thema_a]
        )

        ids = self._get_placement_ids({"org_self": str(self.org_a.id), "labels": str(self.label_thema_a.id)})

        assert p_org_a_label.id in ids, "Org A + label should match"
        assert p_org_a_no_label.id not in ids, "Org A without label should not match"
        assert p_org_b_label.id not in ids, "Org B + label should not match (wrong org)"


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
                "org_self": str(self.org_a.id),
                "rol": str(self.skill_python.id),
                "labels": [str(self.label_thema_a.id), str(self.label_expertise_a.id)],
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
