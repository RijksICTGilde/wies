"""Editables for Service. The ``assignment`` FK is not editable — a service
cannot be reparented.

Permissions live in ``wies/core/permission_rules.py``.
"""

from django_prose_editor.widgets import ProseEditorWidget

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Service


class ServiceEditables(EditableSet):
    class Meta:
        model = Service

    description = Editable(
        label="Omschrijving rol",
        widget=ProseEditorWidget(),
        display="rvo/forms/displays/prose_editor.html",
    )
    skill = Editable(label="Rol")
    period_source = Editable(label="Periode")
    specific_start_date = Editable(label="Specifieke startdatum")
    specific_end_date = Editable(label="Specifieke einddatum")
    status = Editable(label="Status", display=lambda s: s.get_status_display())
