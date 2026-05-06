"""Editables for Service. The ``assignment`` FK is not editable — a service
cannot be reparented.

Permissions live in ``wies/core/permission_rules.py``.
"""

from django import forms

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Service


class ServiceEditables(EditableSet):
    class Meta:
        model = Service

    description = Editable(
        label="Omschrijving",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    skill = Editable(label="Rol")
    period_source = Editable(label="Periode gebaseerd op")
    specific_start_date = Editable(label="Specifieke startdatum")
    specific_end_date = Editable(label="Specifieke einddatum")
    status = Editable(label="Status")
