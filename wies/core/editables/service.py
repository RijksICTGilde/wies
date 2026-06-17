"""Editables for Service. The ``assignment`` FK is not editable — a service
cannot be reparented.

Permissions live in ``wies/core/permission_rules.py``.
"""

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Service
from wies.core.prose import prose_form_field


class ServiceEditables(EditableSet):
    class Meta:
        model = Service

    description = Editable(
        # Explicit `field` keeps the 1:1 model-field binding (so the value is
        # saved) while form_field_factory supplies the ProseEditorFormField —
        # which sanitises the HTML server-side (nh3) on clean, since the
        # display renders it with |safe. Without `field`, form_field_factory
        # would mark this as an unbound editable and the save would fail.
        field="description",
        label="Omschrijving rol",
        form_field_factory=lambda: prose_form_field(label="Omschrijving rol"),
        display="rvo/forms/displays/prose_editor.html",
    )
    skill = Editable(label="Rol")
    period_source = Editable(label="Periode")
    specific_start_date = Editable(label="Specifieke startdatum")
    specific_end_date = Editable(label="Specifieke einddatum")
    status = Editable(label="Status", display=lambda s: s.get_status_display())
