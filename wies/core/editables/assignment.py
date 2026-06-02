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
        for rel in assignment.organization_relations.select_related(
            "organization__parent__parent__parent__parent"
        ).order_by("-role", "organization__name")
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


def _organizations_audit_format(value) -> str:
    """`OrgName (primair), OrgName, ...` for audit events."""
    if not value:
        return "geen"
    parts = []
    for row in value:
        org = row["organization"]
        name = org.label or org.name
        if row["role"] == "PRIMARY":
            parts.append(f"{name} (primair)")
        else:
            parts.append(name)
    return ", ".join(parts)


def _skill_choices():
    # Matches the shape used by assignment-create so service_row.html renders identically.
    choices = [("", " "), ("__new__", "+ Nieuwe rol aanmaken")]
    choices.extend((str(s.id), s.name) for s in Skill.objects.order_by("name"))
    return choices


def _services_initial(assignment):
    """One row per service. Active placement only — historical rows live elsewhere.

    Vacancies (no placement) come before filled rows so users spot open
    aanvragen quickly even on assignments with large teams; FIFO order
    is preserved within each group via the stable sort.

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
    rows.sort(key=lambda r: r["is_filled"])
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


def _services_summary(rows: list[dict]) -> str:
    """Compact "Skill (Colleague-or-open), ..." used in audit events."""
    if not rows:
        return "geen"
    return ", ".join(_service_row_label(r) for r in rows)


def _service_row_label(row: dict) -> str:
    skill = row.get("skill_name") or "?"
    colleague = row.get("colleague")
    return f"{skill} ({colleague.name if colleague else 'open'})"


def _services_diff(before: list[dict], after: list[dict]) -> list[dict]:
    """Bullet entries: added rows, removed rows, and rows whose skill /
    colleague / description changed. Returns [] when nothing changed.

    Each entry is a dict with ``text`` and (for description changes)
    ``old`` + ``new`` so the timeline can render a Van/Naar block.
    """
    before_by_id = {r["id"]: r for r in before}
    after_by_id = {r["id"]: r for r in after}

    entries: list[dict] = [
        {"text": f"Toegevoegd: {_service_row_label(row)}"} for row in after if row["id"] not in before_by_id
    ]
    entries.extend({"text": f"Verwijderd: {_service_row_label(row)}"} for row in before if row["id"] not in after_by_id)
    for sid in before_by_id.keys() & after_by_id.keys():
        b, a = before_by_id[sid], after_by_id[sid]
        b_label, a_label = _service_row_label(b), _service_row_label(a)
        b_desc, a_desc = b.get("description") or "", a.get("description") or ""
        if b_label != a_label:
            entries.append({"text": f"Gewijzigd: {b_label} -> {a_label}"})
        elif b_desc != a_desc:
            entries.append({"text": f"Toelichting gewijzigd op {a_label}", "old": b_desc, "new": a_desc})
    return entries


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
        audit_format=_organizations_audit_format,
        display="rvo/forms/displays/organizations.html",
    )

    services = EditableCollection(
        label="Team",
        formset_factory=_services_formset_factory,
        initial=_services_initial,
        save=_save_services,
        summary=_services_summary,
        diff=_services_diff,
        hide_edit_button=True,
        form_template="parts/assignment_services_form.html",
        display="rvo/forms/displays/assignment_services.html",
    )
