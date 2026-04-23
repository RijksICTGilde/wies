"""Editables for Service. Permission chains up to the parent assignment;
the ``assignment`` FK is not editable — a service cannot be reparented."""

from django import forms

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Placement, Service
from wies.core.roles import user_can_edit_assignment, user_is_assignment_owner_or_admin


def _can_edit_service(user, service):
    return user_can_edit_assignment(user, service.assignment)


def _can_edit_service_description(user, service):
    """Only the consultant placed on this specific service. The BM uses the team editor."""
    if not getattr(user, "is_authenticated", False) or not hasattr(user, "colleague"):
        return False
    if service.assignment.source not in ("wies", ""):
        return False
    return Placement.objects.filter(service=service, colleague=user.colleague).exists()


def _bdm_can_edit_service_field(user, service):
    return user_is_assignment_owner_or_admin(user, service.assignment)


class ServiceEditables(EditableSet):
    model = Service
    object_permission = staticmethod(_can_edit_service)

    description = Editable(
        label="Omschrijving",
        widget=forms.Textarea(attrs={"rows": 4}),
        permission=_can_edit_service_description,
    )
    skill = Editable(label="Rol", permission=_bdm_can_edit_service_field)
    period_source = Editable(label="Periode gebaseerd op", permission=_bdm_can_edit_service_field)
    specific_start_date = Editable(label="Specifieke startdatum", permission=_bdm_can_edit_service_field)
    specific_end_date = Editable(label="Specifieke einddatum", permission=_bdm_can_edit_service_field)
    status = Editable(label="Status", permission=_bdm_can_edit_service_field)
