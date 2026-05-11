from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction

from wies.core.models import Assignment, AssignmentOrganizationUnit, Placement, Service, Skill

if TYPE_CHECKING:
    from datetime import date

    from wies.core.models import Colleague


def extract_services_data(service_formset) -> list[dict]:
    """Extract services_data dicts from a validated ServiceFormSet.

    ``id`` and ``placement_id`` round-trip the existing Service / Placement
    PKs on the edit path. Both are ``None`` for rows added on the create
    form. The values come from attacker-controllable hidden inputs, so the
    caller (apply_services_to_assignment) re-verifies ownership before
    writing.
    """
    services_data = []
    for svc_form in service_formset:
        if not svc_form.cleaned_data:
            continue
        cd = svc_form.cleaned_data
        skill_val = cd.get("skill", "")
        new_skill = cd.get("new_skill_name") or None
        has_skill = (skill_val and skill_val != "__new__") or new_skill
        if not has_skill:
            continue
        skill_id = int(skill_val) if skill_val and skill_val != "__new__" else None
        services_data.append(
            {
                "id": cd.get("id"),
                "placement_id": cd.get("placement_id"),
                "description": cd.get("description", ""),
                "skill_id": skill_id,
                "new_skill_name": new_skill if skill_val == "__new__" else None,
                "status": "OPEN",
                "colleague_id": cd["colleague"].id if cd.get("colleague") else None,
            }
        )
    return services_data


def _resolve_skill(svc: dict) -> Skill | None:
    """Resolve the Skill for a services_data row.

    ``new_skill_name`` wins (get_or_create); otherwise ``skill_id`` is
    looked up. Missing / empty → None.
    """
    if svc.get("new_skill_name"):
        skill, _ = Skill.objects.get_or_create(name=svc["new_skill_name"])
        return skill
    if svc.get("skill_id"):
        return Skill.objects.filter(id=svc["skill_id"]).first()
    return None


@transaction.atomic
def apply_services_to_assignment(assignment: Assignment, services_data: list[dict] | None) -> None:
    """Sync an Assignment's Services + Placements to match ``services_data``.

    ``id`` (Service PK) and ``placement_id`` (Placement PK) on each row are
    attacker-controllable hidden inputs. Any PK that doesn't belong to this
    assignment raises ``ValidationError`` instead of silently creating new
    rows — that keeps stale-form races and malicious posts equally visible.

    Diff semantics:

    - Row without ``id``  → new Service created.
    - Row with ``id``     → existing Service updated in-place.
    - Existing Service not referenced by any submitted row → deleted
      (cascades to its Placements via FK on_delete=CASCADE).

    Placement sync per row:

    - ``placement_id`` + ``colleague_id`` → update that Placement's colleague
      (preserves period_source / specific dates / source_id).
    - ``placement_id`` + no colleague     → Placement deleted.
    - no ``placement_id`` + ``colleague_id`` → new Placement created.
    - neither                             → nothing.
    """
    services_data = services_data or []

    existing_service_ids = set(assignment.services.values_list("id", flat=True))
    existing_placement_ids = set(Placement.objects.filter(service__assignment=assignment).values_list("id", flat=True))
    submitted_service_ids = {int(s["id"]) for s in services_data if s.get("id")}

    unknown_services = submitted_service_ids - existing_service_ids
    if unknown_services:
        msg = "Een of meer diensten bestaan niet meer. Herlaad de pagina en probeer opnieuw."
        raise ValidationError(msg)

    to_delete = existing_service_ids - submitted_service_ids
    if to_delete:
        assignment.services.filter(id__in=to_delete).delete()

    for svc in services_data:
        skill = _resolve_skill(svc)

        service_id = svc.get("id")
        if service_id:
            service = assignment.services.get(id=int(service_id))
            service.description = svc.get("description", "")
            service.skill = skill
            service.status = svc.get("status", service.status)
            service.save(update_fields=["description", "skill", "status"])
        else:
            service = Service.objects.create(
                assignment=assignment,
                description=svc.get("description", ""),
                skill=skill,
                status=svc.get("status", "OPEN"),
                source="wies",
            )

        placement_id = svc.get("placement_id")
        colleague_id = svc.get("colleague_id")

        if placement_id:
            placement_id = int(placement_id)
            if placement_id not in existing_placement_ids:
                msg = "Een of meer plaatsingen bestaan niet meer. Herlaad de pagina en probeer opnieuw."
                raise ValidationError(msg)
            placement = Placement.objects.get(id=placement_id)
            if placement.service_id != service.id:
                # The placement exists on this assignment but belongs to a
                # different service — only reachable via tampering.
                msg = "Een plaatsing verwijst naar een andere dienst. Herlaad de pagina en probeer opnieuw."
                raise ValidationError(msg)
            if colleague_id:
                if placement.colleague_id != int(colleague_id):
                    placement.colleague_id = int(colleague_id)
                    placement.save(update_fields=["colleague_id"])
            else:
                placement.delete()
        elif colleague_id:
            Placement.objects.create(
                colleague_id=int(colleague_id),
                service=service,
                source="wies",
            )


@transaction.atomic
def create_assignment_from_form(
    *,
    name: str,
    extra_info: str = "",
    start_date: date | None = None,
    end_date: date | None = None,
    owner: Colleague | None = None,
    primary_organization_id: int | None = None,
    involved_organization_ids: list[int] | None = None,
    services_data: list[dict] | None = None,
) -> Assignment:
    """Create an Assignment with related Services, Placements, and organization links.

    services_data is a list of dicts with keys:
        - description: str (required)
        - skill_id: int | None
        - new_skill_name: str | None (creates new Skill if set)
        - status: str (CONCEPT/OPEN/GESLOTEN, default OPEN)
        - colleague_id: int | None

    Rows coming from the create form carry ``id`` / ``placement_id`` = None,
    so apply_services_to_assignment takes the "create everything" branch.
    """
    assignment = Assignment.objects.create(
        name=name,
        start_date=start_date,
        end_date=end_date,
        extra_info=extra_info,
        owner=owner,
        source="wies",
    )

    if primary_organization_id:
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment,
            organization_id=primary_organization_id,
            role="PRIMARY",
        )

    for org_id in involved_organization_ids or []:
        AssignmentOrganizationUnit.objects.create(
            assignment=assignment,
            organization_id=org_id,
            role="INVOLVED",
        )

    apply_services_to_assignment(assignment, services_data)

    return assignment
