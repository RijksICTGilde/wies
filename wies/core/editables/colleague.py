"""Editables for Colleague. Permissions live in ``wies/core/permissions.py``."""

from django.db import transaction

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Colleague, LabelCategory, Suborganization
from wies.core.widgets import ComboBoxSelect, MultiselectDropdown

LABELS_PREFIX = "labels_"


def _suborganization_choices():
    # A callable so the queryset evaluates per request, not at registration time.
    return Suborganization.objects.all()


def _save_labels_for_category(category_id):
    """Returns a save that replaces labels in this category only."""

    @transaction.atomic
    def _save(colleague, selected_labels):
        current = colleague.labels.filter(category_id=category_id)
        colleague.labels.remove(*current)
        colleague.labels.add(*selected_labels)

    return _save


def _labels_choices(category):
    # A callable so the queryset evaluates at form-build time, not registration time.
    def _get():
        return category.labels.all().order_by("name")

    return _get


def _labels_initial_for_category(category_id):
    # Filtered per category, symmetrical with _save_labels_for_category: otherwise
    # the concurrency token hashes every label and a save in one category makes
    # the tokens of the others stale.
    def _get(colleague):
        return list(colleague.labels.filter(category_id=category_id))

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
        initial=_labels_initial_for_category(category.id),
        save=_save_labels_for_category(category.id),
        display="forms/displays/colleague_labels.html",
    )
    editable.name = name
    editable.category = category  # read by the display partial
    return editable


class ColleagueEditables(EditableSet):
    class Meta:
        model = Colleague

    suborganization = Editable(
        label="Merk",
        choices=_suborganization_choices,
        required=False,
        empty_label=" ",
        widget=ComboBoxSelect,
        display="forms/displays/colleague_suborganization.html",
    )

    @classmethod
    def resolve_dynamic(cls, name):
        # None when the name doesn't match or the category isn't found → view 404s.
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
