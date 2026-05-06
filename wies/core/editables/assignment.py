"""Editables for Assignment. Reused by the inline-edit view and AssignmentCreateForm.

Permissions live in ``wies/core/permission_rules.py``.
"""

from django import forms
from django.db import transaction

from wies.core.fields import OrganizationsField
from wies.core.inline_edit import Editable, EditableCollection, EditableGroup, EditableSet
from wies.core.models import Assignment, AssignmentOrganizationUnit, Colleague, Skill
from wies.core.services.assignments import apply_services_to_assignment, extract_services_data


def _bdm_queryset():
    # Wrapped in a callable so `choices` evaluates lazily per request.
    return Colleague.objects.filter(user__groups__name="Business Development Manager").order_by("name")


def _organizations_initial(assignment):
    return [
        {"organization": rel.organization, "role": rel.role}
        for rel in assignment.organization_relations.select_related("organization").order_by(
            "-role", "organization__name"
        )
    ]


def _save_organizations(assignment, value):
    # Atomic: a partial failure rolls back, preserving the existing selection.
    with transaction.atomic():
        AssignmentOrganizationUnit.objects.filter(assignment=assignment).delete()
        for row in value:
            AssignmentOrganizationUnit.objects.create(
                assignment=assignment,
                organization=row["organization"],
                role=row["role"],
            )


def _skill_choices():
    # Matches the shape used by assignment-create so service_row.html renders identically.
    choices = [("", " "), ("__new__", "+ Nieuwe rol aanmaken")]
    choices.extend((str(s.id), s.name) for s in Skill.objects.order_by("name"))
    return choices


def _services_initial(assignment):
    """One row per service. Active placement only — historical rows live elsewhere.

    ``skill_name`` / ``service`` are extras for the display partial; the
    formset ignores unknown keys in ``initial``.
    """
    from wies.core.models import Placement  # noqa: PLC0415 — avoids circular import

    rows = []
    for service in assignment.services.select_related("skill").order_by("id"):
        placement = Placement.objects.filter(service=service).select_related("colleague").order_by("-id").first()
        rows.append(
            {
                "id": service.id,
                "placement_id": placement.id if placement else None,
                "skill": str(service.skill_id) if service.skill_id else "",
                "skill_name": service.skill.name if service.skill else "",
                "description": service.description,
                "is_filled": placement is not None,
                "colleague": placement.colleague if placement else None,
                "service": service,
            }
        )
    return rows


def _services_formset_factory(data=None, initial=None):
    # prefix="service" matches assignment_create.html / service_row.html / assignment_form.js
    # so the same row partial renders identically on create and inline-edit.
    from wies.core.forms import ServiceFormSet  # noqa: PLC0415 — avoids circular import

    kwargs = {"prefix": "service", "form_kwargs": {"skill_choices": _skill_choices()}}
    if data is not None:
        return ServiceFormSet(data, **kwargs)
    return ServiceFormSet(initial=initial or [], **kwargs)


def _save_services(assignment, formset):
    services_data = extract_services_data(formset)
    apply_services_to_assignment(assignment, services_data)


def _validate_period(cleaned):
    """Reject end-before-start. Cross-field validation for the period group."""
    from django.core.exceptions import ValidationError  # noqa: PLC0415

    start, end = cleaned.get("start_date"), cleaned.get("end_date")
    if start and end and end < start:
        raise ValidationError({"end_date": "Einddatum moet na startdatum liggen."})
    return cleaned


class AssignmentEditables(EditableSet):
    class Meta:
        model = Assignment

    name = Editable(
        label="Opdracht naam",
        error_messages={"required": "Opdracht naam is verplicht"},
    )

    extra_info = Editable(
        label="Beschrijving",
        widget=forms.Textarea(attrs={"rows": 4}),
        display="rvo/forms/displays/textarea.html",
    )

    start_date = Editable(label="Startdatum")

    end_date = Editable(label="Einddatum")

    owner = Editable(
        label="Business Manager",
        choices=_bdm_queryset,
        required=True,
        empty_label=" ",
        error_messages={"required": "Selecteer een business manager."},
        display="rvo/forms/displays/assignment_owner.html",
    )

    period = EditableGroup(
        label="Looptijd",
        fields=[start_date, end_date],
        clean=_validate_period,
        display="rvo/forms/displays/assignment_period.html",
    )

    organizations = Editable(
        label="Opdrachtgever(s)",
        form_field_factory=lambda: OrganizationsField(required=True),
        initial=_organizations_initial,
        save=_save_organizations,
        display="rvo/forms/displays/organizations.html",
    )

    services = EditableCollection(
        label="Team",
        formset_factory=_services_formset_factory,
        initial=_services_initial,
        save=_save_services,
        form_template="parts/assignment_services_form.html",
        display="rvo/forms/displays/assignment_services.html",
    )
