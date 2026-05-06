"""Editables for Placement. The ``service`` FK is intentionally not editable —
reparenting a placement is a team re-shape, not an edit.

Permissions live in ``wies/core/permission_rules.py``.
"""

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Placement


class PlacementEditables(EditableSet):
    class Meta:
        model = Placement

    colleague = Editable(label="Collega")
    period_source = Editable(label="Periode gebaseerd op")
    specific_start_date = Editable(label="Specifieke startdatum")
    specific_end_date = Editable(label="Specifieke einddatum")
