"""Editables for Placement. The ``service`` FK is intentionally not editable —
reparenting a placement is a team re-shape, not an edit."""

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Placement
from wies.core.roles import user_can_edit_assignment


def _can_edit_placement(user, placement):
    return user_can_edit_assignment(user, placement.service.assignment)


class PlacementEditables(EditableSet):
    model = Placement
    object_permission = staticmethod(_can_edit_placement)

    colleague = Editable(label="Collega")
    period_source = Editable(label="Periode gebaseerd op")
    specific_start_date = Editable(label="Specifieke startdatum")
    specific_end_date = Editable(label="Specifieke einddatum")
