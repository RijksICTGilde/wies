from typing import TypedDict

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from wies.core.models import Config, LabelCategory

CONFIG_KEY = "filter_order_plaatsingen"

SIMPLE_FILTER_TYPES = {"ministerie", "opdrachtgever", "rol", "periode"}

FILTER_LABELS = {
    "ministerie": "Ministerie",
    "opdrachtgever": "Opdrachtgever",
    "rol": "Rollen",
    "periode": "Periode",
}


class LabelCategoryFilter(TypedDict):
    label_category: int


FilterItem = str | LabelCategoryFilter


def get_default_filter_order() -> list[FilterItem]:
    """Return default filter order with all current filters."""
    result: list[FilterItem] = [
        "ministerie",
        "opdrachtgever",
        "rol",
    ]
    result.extend({"label_category": lc.id} for lc in LabelCategory.objects.only("id"))
    result.append("periode")
    return result


def validate_filter_item(item) -> bool:
    """Check if a filter item is valid."""
    if isinstance(item, str):
        return item in SIMPLE_FILTER_TYPES

    if isinstance(item, dict):
        label_category_id = item.get("label_category")
        return isinstance(label_category_id, int) and label_category_id > 0

    return False


def get_filter_order() -> list[FilterItem]:
    """Get stored filter order or default."""
    order = Config.get(CONFIG_KEY)
    if order is None:
        return get_default_filter_order()

    invalid_items = [item for item in order if not validate_filter_item(item)]
    if invalid_items:
        msg = f"Invalid filter items in config: {invalid_items}"
        raise ValueError(msg)

    return order


def add_label_category_to_filter_order(label_category_id: int) -> None:
    """Add a new label category to the filter order, before periode."""
    order = Config.get(CONFIG_KEY)
    if order is None:
        return  # Will be included in default order

    new_item: FilterItem = {"label_category": label_category_id}
    periode_idx = next((i for i, item in enumerate(order) if item == "periode"), len(order))
    order = [*order[:periode_idx], new_item, *order[periode_idx:]]
    Config.set(CONFIG_KEY, order)


def remove_label_category_from_filter_order(label_category_id: int) -> None:
    """Remove a label category from the filter order."""
    order = Config.get(CONFIG_KEY)
    if order is None:
        return

    order = [item for item in order if not (isinstance(item, dict) and item.get("label_category") == label_category_id)]
    Config.set(CONFIG_KEY, order)


@receiver(post_save, sender=LabelCategory)
def on_label_category_created(sender, instance, created, **kwargs):
    """Add new label category to filter order."""
    if created:
        add_label_category_to_filter_order(instance.id)


@receiver(post_delete, sender=LabelCategory)
def on_label_category_deleted(sender, instance, **kwargs):
    """Remove deleted label category from filter order."""
    remove_label_category_from_filter_order(instance.id)


@transaction.atomic
def move_filter_by_position(position: int, direction: str) -> tuple[int, int]:
    """
    Move filter at given position up or down.

    Args:
        position: 1-based position in the list
        direction: "up" or "down"

    Returns:
        Tuple of (moved_position, swapped_position), both 1-based.

    Raises:
        ValueError: if position or direction is invalid.
    """
    if direction not in ("up", "down"):
        msg = f"Invalid direction: {direction}"
        raise ValueError(msg)

    order = get_filter_order()
    idx = position - 1

    if idx < 0 or idx >= len(order):
        msg = f"Invalid position: {position}"
        raise ValueError(msg)

    new_idx = idx
    swapped_idx = idx
    if direction == "up" and idx > 0:
        order[idx], order[idx - 1] = order[idx - 1], order[idx]
        new_idx = idx - 1
        swapped_idx = idx
    elif direction == "down" and idx < len(order) - 1:
        order[idx], order[idx + 1] = order[idx + 1], order[idx]
        new_idx = idx + 1
        swapped_idx = idx

    Config.set(CONFIG_KEY, order)
    return new_idx + 1, swapped_idx + 1


def get_filter_labels_bulk() -> dict:
    """Fetch all filter labels in a single query."""
    return {
        **FILTER_LABELS,
        **{("label_category", lc.id): lc.name for lc in LabelCategory.objects.only("id", "name")},
    }


def get_filters_for_display() -> list[dict]:
    """Get filters with labels for display."""
    order = get_filter_order()
    labels = get_filter_labels_bulk()

    result = []
    for i, item in enumerate(order):
        if isinstance(item, str):
            filter_key = item
            lookup_key = item
            filter_id = None
        else:
            filter_key = next(iter(item))
            filter_id = item[filter_key]
            lookup_key = (filter_key, filter_id)

        result.append(
            {
                "filter_key": filter_key,
                "id": filter_id,
                "label": labels.get(lookup_key, str(item)),
                "position": i + 1,
                "is_first": i == 0,
                "is_last": i == len(order) - 1,
            }
        )

    return result
