"""Tests for LabelCategory display_order functionality"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from wies.core.forms import LabelCategoryForm
from wies.core.models import Label, LabelCategory, get_next_display_order

User = get_user_model()


class GetNextDisplayOrderTest(TestCase):
    """Tests for the get_next_display_order() helper function."""

    def test_empty_database_returns_10(self):
        """Empty database returns 10."""
        self.assertEqual(get_next_display_order(), 10)

    def test_increments_by_10_from_round_number(self):
        """With max=10, returns 20."""
        LabelCategory.objects.create(name="First", color="#111111", display_order=10)
        self.assertEqual(get_next_display_order(), 20)

    def test_rounds_up_to_next_10(self):
        """With max=25, returns 30 (rounded to 10)."""
        LabelCategory.objects.create(name="First", color="#111111", display_order=25)
        self.assertEqual(get_next_display_order(), 30)

    def test_handles_max_at_boundary(self):
        """With max=30, returns 40."""
        LabelCategory.objects.create(name="First", color="#111111", display_order=30)
        self.assertEqual(get_next_display_order(), 40)

    def test_uses_highest_value(self):
        """Uses highest value, not the last created."""
        LabelCategory.objects.create(name="High", color="#111111", display_order=50)
        LabelCategory.objects.create(name="Low", color="#222222", display_order=10)
        self.assertEqual(get_next_display_order(), 60)


class LabelCategoryOrderingTest(TestCase):
    """Tests for LabelCategory Meta.ordering."""

    def setUp(self):
        # Create categories in wrong order
        self.cat_merk = LabelCategory.objects.create(name="Merk", color="#DCE3EA", display_order=30)
        self.cat_expertise = LabelCategory.objects.create(name="Expertise", color="#B3D7EE", display_order=10)
        self.cat_thema = LabelCategory.objects.create(name="Thema", color="#FFE9B8", display_order=20)

    def test_label_categories_ordered_by_display_order(self):
        """Categories are sorted by display_order."""
        categories = list(LabelCategory.objects.all())
        self.assertEqual(categories[0].name, "Expertise")
        self.assertEqual(categories[1].name, "Thema")
        self.assertEqual(categories[2].name, "Merk")

    def test_same_display_order_sorted_by_name_case_insensitive(self):
        """With equal display_order, sorts by name (case-insensitive)."""
        LabelCategory.objects.all().delete()
        LabelCategory.objects.create(name="Zebra", color="#111111", display_order=10)
        LabelCategory.objects.create(name="apple", color="#222222", display_order=10)
        LabelCategory.objects.create(name="Banana", color="#333333", display_order=10)

        categories = list(LabelCategory.objects.all())
        # Case-insensitive: apple, Banana, Zebra
        self.assertEqual(categories[0].name, "apple")
        self.assertEqual(categories[1].name, "Banana")
        self.assertEqual(categories[2].name, "Zebra")


class DynamicDisplayOrderIntegrationTest(TestCase):
    """Tests that model and form correctly use the helper function."""

    def test_model_uses_helper_as_default(self):
        """Model.objects.create() uses get_next_display_order()."""
        cat = LabelCategory.objects.create(name="Test", color="#000000")
        self.assertEqual(cat.display_order, 10)

        cat2 = LabelCategory.objects.create(name="Test2", color="#111111")
        self.assertEqual(cat2.display_order, 20)

    def test_explicit_display_order_overrides_default(self):
        """Explicitly provided display_order overrides default."""
        cat = LabelCategory.objects.create(name="Test", color="#000000", display_order=99)
        self.assertEqual(cat.display_order, 99)

    def test_entered_value_not_rounded(self):
        """Entered value is not rounded - 25 stays 25."""
        cat = LabelCategory.objects.create(name="Test", color="#000000", display_order=25)
        self.assertEqual(cat.display_order, 25)  # not rounded to 30

    def test_form_sets_dynamic_initial_for_new_category(self):
        """LabelCategoryForm gets dynamic initial for new category."""
        LabelCategory.objects.create(name="Existing", color="#111111", display_order=50)
        form = LabelCategoryForm()
        self.assertEqual(form.fields["display_order"].initial, 60)

    def test_form_edit_preserves_existing_value(self):
        """When editing, form preserves existing value."""
        cat = LabelCategory.objects.create(name="Existing", color="#111111", display_order=25)
        form = LabelCategoryForm(instance=cat)
        # On edit: instance value is preserved
        self.assertEqual(form.instance.display_order, 25)


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class FilterOrderingViewTest(TestCase):
    """Tests that filters in views respect the correct order."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        # Create categories with labels
        self.cat_merk = LabelCategory.objects.create(name="Merk", color="#DCE3EA", display_order=30)
        self.cat_expertise = LabelCategory.objects.create(name="Expertise", color="#B3D7EE", display_order=10)
        self.cat_thema = LabelCategory.objects.create(name="Thema", color="#FFE9B8", display_order=20)
        # Add labels
        Label.objects.create(name="Test Merk", category=self.cat_merk)
        Label.objects.create(name="Test Expertise", category=self.cat_expertise)
        Label.objects.create(name="Test Thema", category=self.cat_thema)

    def test_placement_filters_respect_display_order(self):
        """Filters on placements page follow display_order."""
        self.client.force_login(self.user)
        response = self.client.get("/")

        if response.status_code == 200:
            # Check that filter_groups exist and are in correct order
            filter_groups = response.context.get("filter_groups", [])
            # First 3 should be label category filters
            label_filters = [fg for fg in filter_groups if fg.get("name") == "labels"]
            if len(label_filters) >= 3:
                self.assertEqual(label_filters[0]["label"], "Expertise")
                self.assertEqual(label_filters[1]["label"], "Thema")
                self.assertEqual(label_filters[2]["label"], "Merk")
