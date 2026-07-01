"""Editables for Placement. The ``service`` FK is intentionally not editable —
reparenting a placement is a team re-shape, not an edit.

Permissions live in ``wies/core/permission_rules.py``.
"""

from django.core.exceptions import ValidationError

from wies.core.inline_edit import Editable, EditableGroup, EditableSet
from wies.core.models import Placement


def _validate_placement_period(cleaned):
    start = cleaned.get("specific_start_date")
    end = cleaned.get("specific_end_date")
    if start and end and end < start:
        raise ValidationError({"specific_end_date": "Einddatum moet na startdatum liggen."})
    return cleaned


class PlacementEditables(EditableSet):
    class Meta:
        model = Placement

    colleague = Editable(label="Collega")
    period_source = Editable(label="Periode")
    specific_start_date = Editable(label="Startdatum")
    specific_end_date = Editable(label="Einddatum")

    period = EditableGroup(
        label="Periode",
        fields=[period_source, specific_start_date, specific_end_date],
        clean=_validate_placement_period,
        display="nldd/forms/displays/placement_period.html",
        form_template="parts/placement_period_form.html",
    )
