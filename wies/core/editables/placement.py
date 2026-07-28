"""Editables for Placement. The ``service`` FK is intentionally not editable —
reparenting a placement is a team re-shape, not an edit.

Permissions live in ``wies/core/permission_rules.py``.
"""

from contextlib import contextmanager

from django.core.exceptions import ValidationError

from wies.core.editables.assignment import placement_audit_row
from wies.core.inline_edit import Editable, EditableGroup, EditableSet
from wies.core.models import Placement
from wies.core.services.events import create_event


def _validate_placement_period(cleaned):
    start = cleaned.get("specific_start_date")
    end = cleaned.get("specific_end_date")
    if start and end and end < start:
        raise ValidationError({"specific_end_date": "Einddatum moet na startdatum liggen."})
    return cleaned


@contextmanager
def _mirror_edit_onto_assignment(placement, user, request=None):
    """Record an inline placement edit as a "Team" event on the parent
    assignment. A placement has no audit type of its own, and this way the
    change renders identically to one made through "Team bewerken"."""
    before_row = placement_audit_row(placement)
    yield
    placement.refresh_from_db()
    after_row = placement_audit_row(placement)
    if before_row == after_row:
        return
    create_event(
        object_type="Assignment",
        action="update",
        source="user",
        object_id=placement.service.assignment_id,
        user=user,
        request=request,
        context={
            "field_name": "services",
            "field_label": "Team",
            "changes": [{"old": before_row, "new": after_row}],
        },
    )


class PlacementEditables(EditableSet):
    class Meta:
        model = Placement

    audit_mirror = staticmethod(_mirror_edit_onto_assignment)

    colleague = Editable(label="Collega")
    period_source = Editable(label="Periode")
    specific_start_date = Editable(label="Startdatum")
    specific_end_date = Editable(label="Einddatum")

    period = EditableGroup(
        label="Periode",
        fields=[period_source, specific_start_date, specific_end_date],
        clean=_validate_placement_period,
        display="rvo/forms/displays/placement_period.html",
        form_template="parts/placement_period_form.html",
    )
