import pytest
from django.test import TestCase

from wies.core.models import Config, LabelCategory
from wies.core.services.filter_order import (
    CONFIG_KEY,
    add_label_category_to_filter_order,
    get_default_filter_order,
    get_filter_order,
    get_filters_for_display,
    move_filter_by_position,
    remove_label_category_from_filter_order,
    validate_filter_item,
)


class ValidateFilterItemTest(TestCase):
    """Tests for validate_filter_item function"""

    def test_accepts_valid_simple_filters(self):
        assert validate_filter_item("ministerie")
        assert validate_filter_item("opdrachtgever")
        assert validate_filter_item("rol")
        assert validate_filter_item("periode")

    def test_rejects_unknown_filter_type(self):
        assert not validate_filter_item("onbekend")
        assert not validate_filter_item("invalid")
        assert not validate_filter_item("")

    def test_accepts_valid_label_category(self):
        assert validate_filter_item({"label_category": 1})
        assert validate_filter_item({"label_category": 100})

    def test_rejects_label_category_without_id(self):
        assert not validate_filter_item({"label_category": None})
        assert not validate_filter_item({})
        assert not validate_filter_item({"other": 1})

    def test_rejects_string_label_category_id(self):
        assert not validate_filter_item({"label_category": "1"})
        assert not validate_filter_item({"label_category": "abc"})

    def test_rejects_negative_label_category_id(self):
        assert not validate_filter_item({"label_category": -1})
        assert not validate_filter_item({"label_category": 0})

    def test_rejects_invalid_types(self):
        assert not validate_filter_item(None)
        assert not validate_filter_item(123)
        assert not validate_filter_item([])


class GetDefaultFilterOrderTest(TestCase):
    """Tests for get_default_filter_order function"""

    def test_includes_all_simple_filters(self):
        order = get_default_filter_order()
        assert "ministerie" in order
        assert "opdrachtgever" in order
        assert "rol" in order
        assert "periode" in order

    def test_includes_all_label_categories(self):
        cat1 = LabelCategory.objects.create(name="Test1", color="#000000")
        cat2 = LabelCategory.objects.create(name="Test2", color="#111111")

        order = get_default_filter_order()

        label_category_ids = [item["label_category"] for item in order if isinstance(item, dict)]
        assert cat1.id in label_category_ids
        assert cat2.id in label_category_ids

    def test_periode_is_last(self):
        LabelCategory.objects.create(name="Test", color="#000000")
        order = get_default_filter_order()
        assert order[-1] == "periode"


class LabelCategorySignalTest(TestCase):
    """Tests for label category signal handlers"""

    def test_new_label_category_added_to_filter_order(self):
        """New label category is automatically added via signal."""
        Config.set(CONFIG_KEY, ["ministerie", "periode"])

        cat = LabelCategory.objects.create(name="NewCat", color="#000000")

        order = Config.get(CONFIG_KEY)
        label_category_ids = [item["label_category"] for item in order if isinstance(item, dict)]
        assert cat.id in label_category_ids

    def test_new_label_category_added_before_periode(self):
        """New label category is added before periode."""
        Config.set(CONFIG_KEY, ["ministerie", "periode"])

        cat = LabelCategory.objects.create(name="NewCat", color="#000000")

        order = Config.get(CONFIG_KEY)
        periode_idx = order.index("periode")
        cat_idx = next(
            i for i, item in enumerate(order) if isinstance(item, dict) and item.get("label_category") == cat.id
        )
        assert cat_idx < periode_idx

    def test_deleted_label_category_removed_from_filter_order(self):
        """Deleted label category is automatically removed via signal."""
        cat = LabelCategory.objects.create(name="ToDelete", color="#000000")
        Config.set(CONFIG_KEY, ["ministerie", {"label_category": cat.id}, "periode"])

        cat.delete()

        order = Config.get(CONFIG_KEY)
        label_category_ids = [item["label_category"] for item in order if isinstance(item, dict)]
        assert cat.id not in label_category_ids

    def test_add_label_category_to_filter_order_without_config(self):
        """Adding to non-existent config does nothing (default will include it)."""
        add_label_category_to_filter_order(999)
        assert Config.get(CONFIG_KEY) is None

    def test_remove_label_category_from_filter_order_without_config(self):
        """Removing from non-existent config does nothing."""
        remove_label_category_from_filter_order(999)
        assert Config.get(CONFIG_KEY) is None


class GetFilterOrderTest(TestCase):
    """Tests for get_filter_order function"""

    def test_returns_default_when_no_config(self):
        order = get_filter_order()
        assert "ministerie" in order
        assert "periode" in order

    def test_returns_stored_order(self):
        Config.set(CONFIG_KEY, ["periode", "ministerie"])
        order = get_filter_order()
        assert order[0] == "periode"
        assert order[1] == "ministerie"

    def test_invalid_items_raise_error(self):
        Config.set(CONFIG_KEY, ["ministerie", "invalid", "periode"])
        with pytest.raises(ValueError, match="Invalid filter items"):
            get_filter_order()


class MoveFilterByPositionTest(TestCase):
    """Tests for move_filter_by_position function"""

    def setUp(self):
        Config.set(CONFIG_KEY, ["ministerie", "opdrachtgever", "rol", "periode"])

    def test_move_up_returns_both_positions(self):
        moved_pos, swapped_pos = move_filter_by_position(2, "up")
        assert moved_pos == 1
        assert swapped_pos == 2

    def test_move_down_returns_both_positions(self):
        moved_pos, swapped_pos = move_filter_by_position(2, "down")
        assert moved_pos == 3
        assert swapped_pos == 2

    def test_move_at_top_boundary_returns_same(self):
        moved_pos, swapped_pos = move_filter_by_position(1, "up")
        assert moved_pos == 1
        assert swapped_pos == 1

    def test_move_at_bottom_boundary_returns_same(self):
        moved_pos, swapped_pos = move_filter_by_position(4, "down")
        assert moved_pos == 4
        assert swapped_pos == 4

    def test_invalid_direction_raises_error(self):
        with pytest.raises(ValueError, match="Invalid direction"):
            move_filter_by_position(1, "invalid")

    def test_invalid_position_raises_error(self):
        with pytest.raises(ValueError, match="Invalid position"):
            move_filter_by_position(0, "up")
        with pytest.raises(ValueError, match="Invalid position"):
            move_filter_by_position(100, "up")

    def test_order_persists_after_move(self):
        move_filter_by_position(2, "up")
        order = Config.get(CONFIG_KEY)
        assert order[0] == "opdrachtgever"
        assert order[1] == "ministerie"


class GetFiltersForDisplayTest(TestCase):
    """Tests for get_filters_for_display function"""

    def setUp(self):
        self.cat = LabelCategory.objects.create(name="TestCat", color="#000000")
        Config.set(CONFIG_KEY, ["ministerie", {"label_category": self.cat.id}, "periode"])

    def test_returns_filter_data_with_labels(self):
        filters = get_filters_for_display()

        assert len(filters) == 3
        assert filters[0]["label"] == "Ministerie"
        assert filters[1]["label"] == "TestCat"
        assert filters[2]["label"] == "Periode"

    def test_includes_position_info(self):
        filters = get_filters_for_display()

        assert filters[0]["position"] == 1
        assert filters[0]["is_first"] is True
        assert filters[0]["is_last"] is False

        assert filters[2]["position"] == 3
        assert filters[2]["is_first"] is False
        assert filters[2]["is_last"] is True

    def test_includes_filter_key_info(self):
        filters = get_filters_for_display()

        assert filters[0]["filter_key"] == "ministerie"
        assert filters[1]["filter_key"] == "label_category"
        assert filters[1]["id"] == self.cat.id
        assert filters[2]["filter_key"] == "periode"
