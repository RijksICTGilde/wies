from datetime import date

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
    User,
)
from wies.core.views import PlacementListView


class FilterCombiningTestBase(TestCase):
    """Shared setup for filter combining tests."""

    def setUp(self):
        self.auth_user = User.objects.create(username="testuser", email="test@rijksoverheid.nl")
        self.skill_python = Skill.objects.create(name="Python Developer")
        self.skill_java = Skill.objects.create(name="Java Developer")

        # Label categories
        self.cat_merk = LabelCategory.objects.create(name="Merk", color="#DCE3EA")
        self.cat_expertise = LabelCategory.objects.create(name="Expertise", color="#00AA00")

        # Labels
        self.label_rig = Label.objects.create(name="Rijks ICT Gilde", category=self.cat_merk)
        self.label_iir = Label.objects.create(name="I-Interim Rijk", category=self.cat_merk)
        self.label_agile = Label.objects.create(name="Agile", category=self.cat_expertise)
        self.label_cloud = Label.objects.create(name="Cloud", category=self.cat_expertise)

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
            status="INGEVULD",
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
        p_rig = self._create_placement("Alice", self.skill_python, labels=[self.label_rig])
        p_iir = self._create_placement("Bob", self.skill_python, labels=[self.label_iir])
        p_none = self._create_placement("Charlie", self.skill_python)

        ids = self._get_placement_ids({"labels": str(self.label_rig.id)})

        assert p_rig.id in ids
        assert p_iir.id not in ids
        assert p_none.id not in ids

    def test_two_labels_same_category_use_or(self):
        """Selecting RIG + IIR (both Merk) should show colleagues with EITHER label."""
        p_rig = self._create_placement("Alice", self.skill_python, labels=[self.label_rig])
        p_iir = self._create_placement("Bob", self.skill_python, labels=[self.label_iir])
        p_none = self._create_placement("Charlie", self.skill_python)

        ids = self._get_placement_ids({"labels": [str(self.label_rig.id), str(self.label_iir.id)]})

        assert p_rig.id in ids, "RIG colleague should match (OR within Merk)"
        assert p_iir.id in ids, "IIR colleague should match (OR within Merk)"
        assert p_none.id not in ids, "Unlabelled colleague should not match"

    def test_colleague_with_both_labels_appears_once(self):
        """Colleague with both labels in same category should appear exactly once."""
        p_both = self._create_placement("Alice", self.skill_python, labels=[self.label_rig, self.label_iir])

        ids = self._get_placement_ids({"labels": [str(self.label_rig.id), str(self.label_iir.id)]})

        assert ids.count(p_both.id) == 1, "Should appear exactly once, not duplicated"


class LabelANDBetweenCategoriesTest(FilterCombiningTestBase):
    """Labels from different categories combine with AND."""

    def test_labels_from_different_categories_use_and(self):
        """Selecting RIG (Merk) + Agile (Expertise) should only show colleagues with BOTH."""
        p_both = self._create_placement("Alice", self.skill_python, labels=[self.label_rig, self.label_agile])
        p_merk_only = self._create_placement("Bob", self.skill_python, labels=[self.label_rig])
        p_expertise_only = self._create_placement("Charlie", self.skill_python, labels=[self.label_agile])

        ids = self._get_placement_ids({"labels": [str(self.label_rig.id), str(self.label_agile.id)]})

        assert p_both.id in ids, "Colleague with both labels should match"
        assert p_merk_only.id not in ids, "Colleague with only Merk label should not match"
        assert p_expertise_only.id not in ids, "Colleague with only Expertise label should not match"

    def test_or_within_and_between(self):
        """RIG+IIR (Merk, OR) combined with Agile (Expertise, AND).

        Should match colleagues who have (RIG OR IIR) AND Agile.
        """
        p_rig_agile = self._create_placement("Alice", self.skill_python, labels=[self.label_rig, self.label_agile])
        p_iir_agile = self._create_placement("Bob", self.skill_python, labels=[self.label_iir, self.label_agile])
        p_rig_only = self._create_placement("Charlie", self.skill_python, labels=[self.label_rig])
        p_agile_only = self._create_placement("Dave", self.skill_python, labels=[self.label_agile])

        ids = self._get_placement_ids(
            {"labels": [str(self.label_rig.id), str(self.label_iir.id), str(self.label_agile.id)]}
        )

        assert p_rig_agile.id in ids, "RIG + Agile should match"
        assert p_iir_agile.id in ids, "IIR + Agile should match"
        assert p_rig_only.id not in ids, "RIG without Agile should not match"
        assert p_agile_only.id not in ids, "Agile without Merk label should not match"


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
        """Rol=Python AND Label=RIG should only show placements matching both."""
        p_python_rig = self._create_placement("Alice", self.skill_python, labels=[self.label_rig])
        p_python_no_label = self._create_placement("Bob", self.skill_python)
        p_java_rig = self._create_placement("Charlie", self.skill_java, labels=[self.label_rig])

        ids = self._get_placement_ids({"rol": str(self.skill_python.id), "labels": str(self.label_rig.id)})

        assert p_python_rig.id in ids, "Python + RIG should match"
        assert p_python_no_label.id not in ids, "Python without RIG should not match"
        assert p_java_rig.id not in ids, "Java + RIG should not match (wrong rol)"


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
        p_org_a_rig = self._create_placement("Alice", self.skill_python, org=self.org_a, labels=[self.label_rig])
        p_org_a_no_label = self._create_placement("Bob", self.skill_python, org=self.org_a)
        p_org_b_rig = self._create_placement("Charlie", self.skill_python, org=self.org_b, labels=[self.label_rig])

        ids = self._get_placement_ids({"org_self": str(self.org_a.id), "labels": str(self.label_rig.id)})

        assert p_org_a_rig.id in ids, "Org A + RIG should match"
        assert p_org_a_no_label.id not in ids, "Org A without label should not match"
        assert p_org_b_rig.id not in ids, "Org B + RIG should not match (wrong org)"


class AllFiltersCombinedTest(FilterCombiningTestBase):
    """Test all filter types combined: org AND rol AND labels (OR within, AND between)."""

    def test_all_filters_combined(self):
        """org + rol + labels from two categories should all AND together."""
        # This colleague matches everything
        p_match = self._create_placement(
            "Alice", self.skill_python, org=self.org_a, labels=[self.label_rig, self.label_agile]
        )
        # Wrong org
        p_wrong_org = self._create_placement(
            "Bob", self.skill_python, org=self.org_b, labels=[self.label_rig, self.label_agile]
        )
        # Wrong rol
        p_wrong_rol = self._create_placement(
            "Charlie", self.skill_java, org=self.org_a, labels=[self.label_rig, self.label_agile]
        )
        # Missing expertise label
        p_missing_label = self._create_placement("Dave", self.skill_python, org=self.org_a, labels=[self.label_rig])

        ids = self._get_placement_ids(
            {
                "org_self": str(self.org_a.id),
                "rol": str(self.skill_python.id),
                "labels": [str(self.label_rig.id), str(self.label_agile.id)],
            }
        )

        assert p_match.id in ids, "Should match all filters"
        assert p_wrong_org.id not in ids, "Wrong org should be excluded"
        assert p_wrong_rol.id not in ids, "Wrong rol should be excluded"
        assert p_missing_label.id not in ids, "Missing cross-category label should be excluded"

    def test_no_filters_returns_all(self):
        """Without any filters, all active placements are returned."""
        p1 = self._create_placement("Alice", self.skill_python, org=self.org_a, labels=[self.label_rig])
        p2 = self._create_placement("Bob", self.skill_java, org=self.org_b, labels=[self.label_iir])
        p3 = self._create_placement("Charlie", self.skill_python)

        ids = self._get_placement_ids({})

        assert p1.id in ids
        assert p2.id in ids
        assert p3.id in ids

    def test_invalid_label_id_returns_empty(self):
        """Non-existent label ID should return no results."""
        self._create_placement("Alice", self.skill_python, labels=[self.label_rig])

        ids = self._get_placement_ids({"labels": "99999"})

        assert len(ids) == 0, "Non-existent label should return no results"
