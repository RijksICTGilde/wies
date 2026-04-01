from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from wies.core.models import Assignment, AssignmentOrganizationUnit, Placement, Service, Skill

if TYPE_CHECKING:
    from datetime import date

    from wies.core.models import Colleague


def extract_services_data(service_formset) -> list[dict]:
    """Extract services_data dicts from a validated ServiceFormSet."""
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
                "description": cd.get("description", ""),
                "skill_id": skill_id,
                "new_skill_name": new_skill if skill_val == "__new__" else None,
                "status": "OPEN",
                "colleague_id": cd["colleague"].id if cd.get("colleague") else None,
            }
        )
    return services_data


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

    for svc in services_data or []:
        # Resolve skill: existing or new
        skill = None
        if svc.get("new_skill_name"):
            skill, _ = Skill.objects.get_or_create(name=svc["new_skill_name"])
        elif svc.get("skill_id"):
            skill = Skill.objects.filter(id=svc["skill_id"]).first()

        service = Service.objects.create(
            assignment=assignment,
            description=svc["description"],
            skill=skill,
            status=svc.get("status", "OPEN"),
            source="wies",
        )

        if svc.get("colleague_id"):
            Placement.objects.create(
                colleague_id=svc["colleague_id"],
                service=service,
                source="wies",
            )

    return assignment
