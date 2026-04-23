"""Editables for Colleague — one labels field per LabelCategory, built dynamically."""

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Colleague, LabelCategory
from wies.core.widgets import MultiselectDropdown

LABELS_PREFIX = "labels_"


def _save_labels_for_category(category_id):
    """Replace labels in this category only; leave other categories untouched."""

    def _save(colleague, selected_labels):
        current = colleague.labels.filter(category_id=category_id)
        colleague.labels.remove(*current)
        colleague.labels.add(*selected_labels)

    return _save


def _labels_choices(category):
    # Callable so the queryset evaluates at form-build time, not registration time.
    def _get():
        return category.labels.all().order_by("name")

    return _get


def _build_label_editable(category):
    name = f"{LABELS_PREFIX}{category.id}"
    editable = Editable(
        model=Colleague,
        field="labels",
        label=category.name,
        required=False,
        widget=MultiselectDropdown,
        choices=_labels_choices(category),
        save=_save_labels_for_category(category.id),
        display="parts/inline_edit/displays/colleague_labels.html",
    )
    editable.name = name
    editable.category = category  # read by the display partial
    return editable


class ColleagueEditables(EditableSet):
    model = Colleague
    object_permission = staticmethod(
        lambda user, colleague: (
            user.is_authenticated
            and (user.has_perm("core.change_colleague") or getattr(user, "colleague", None) == colleague)
        )
    )

    @classmethod
    def resolve_dynamic(cls, name):
        # Returns None when the name doesn't match or the category isn't found → view 404s.
        if not name.startswith(LABELS_PREFIX):
            return None
        try:
            category_id = int(name[len(LABELS_PREFIX) :])
        except ValueError:
            return None
        category = LabelCategory.objects.filter(pk=category_id).first()
        if category is None:
            return None
        return _build_label_editable(category)
