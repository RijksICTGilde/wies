from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction

from django.db.models import Count

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
                "has_custom_period": cd.get("has_custom_period", False),
                "placement_start_date": cd.get("placement_start_date"),
                "placement_end_date": cd.get("placement_end_date"),
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
            update_fields = ["description", "skill", "status"]
            if svc.get("has_custom_period"):
                service.period_source = Service.SERVICE
                service.specific_start_date = svc.get("placement_start_date")
                service.specific_end_date = svc.get("placement_end_date")
            else:
                service.period_source = Service.ASSIGNMENT
                service.specific_start_date = None
                service.specific_end_date = None
            update_fields.extend(["period_source", "specific_start_date", "specific_end_date"])
            service.save(update_fields=update_fields)
        else:
            create_kwargs = {
                "assignment": assignment,
                "description": svc.get("description", ""),
                "skill": skill,
                "status": svc.get("status", "OPEN"),
                "source": "wies",
            }
            if svc.get("has_custom_period"):
                create_kwargs["period_source"] = Service.SERVICE
                create_kwargs["specific_start_date"] = svc.get("placement_start_date")
                create_kwargs["specific_end_date"] = svc.get("placement_end_date")
            service = Service.objects.create(**create_kwargs)

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
                update_fields = []
                if placement.colleague_id != int(colleague_id):
                    placement.colleague_id = int(colleague_id)
                    update_fields.append("colleague_id")

                if svc.get("has_custom_period"):
                    new_source = Placement.PLACEMENT
                    new_start = svc.get("placement_start_date")
                    new_end = svc.get("placement_end_date")
                else:
                    new_source = Placement.SERVICE
                    new_start = None
                    new_end = None

                if placement.period_source != new_source:
                    placement.period_source = new_source
                    update_fields.append("period_source")
                if placement.specific_start_date != new_start:
                    placement.specific_start_date = new_start
                    update_fields.append("specific_start_date")
                if placement.specific_end_date != new_end:
                    placement.specific_end_date = new_end
                    update_fields.append("specific_end_date")

                if update_fields:
                    placement.save(update_fields=update_fields)
            else:
                placement.delete()
        elif colleague_id:
            create_kwargs = {
                "colleague_id": int(colleague_id),
                "service": service,
                "source": "wies",
            }
            if svc.get("has_custom_period"):
                create_kwargs["period_source"] = Placement.PLACEMENT
                create_kwargs["specific_start_date"] = svc.get("placement_start_date")
                create_kwargs["specific_end_date"] = svc.get("placement_end_date")
            Placement.objects.create(**create_kwargs)


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


def find_duplicate_groups():
    """Find assignments that share the same name, owner, and primary organization."""
    qs = (
        Assignment.objects.filter(
            organization_relations__role="PRIMARY",
        )
        .values(
            "name",
            "owner",
            "organization_relations__organization",
        )
        .annotate(
            count=Count("id"),
        )
        .filter(
            count__gt=1,
        )
        .order_by("name")
    )

    groups = []
    for dupe in qs:
        assignments = (
            Assignment.objects.filter(
                name=dupe["name"],
                owner=dupe["owner"],
                organization_relations__role="PRIMARY",
                organization_relations__organization=dupe["organization_relations__organization"],
            )
            .select_related("owner")
            .prefetch_related(
                "services__placements__colleague",
                "services__skill",
                "organization_relations__organization",
            )
            .order_by("id")
        )
        group = list(assignments)
        # Avoid adding the same group twice (can happen with multiple orgs).
        if group and not any(g[0].id == group[0].id for g in groups):
            groups.append(group)
    return groups


@transaction.atomic
def merge_group(assignments):
    """Merge a group of duplicate assignments into the first (oldest) one.

    Strategy:
    - Keep the assignment with the lowest ID as the target.
    - Move all services (and their placements) to the target, pinning explicit dates.
    - Pick the widest date range across all assignments.
    - Delete the now-empty duplicate assignments.
    """
    target = assignments[0]
    duplicates = assignments[1:]

    # Widen the date range to cover all assignments.
    all_starts = [a.start_date for a in assignments if a.start_date]
    all_ends = [a.end_date for a in assignments if a.end_date]
    new_start = min(all_starts) if all_starts else None
    new_end = max(all_ends) if all_ends else None

    if new_start != target.start_date or new_end != target.end_date:
        target.start_date = new_start
        target.end_date = new_end
        target.save(update_fields=["start_date", "end_date"])

    for dupe in duplicates:
        for svc in dupe.services.all():
            start, end = svc.start_date, svc.end_date
            svc.period_source = "SERVICE"
            svc.specific_start_date = start
            svc.specific_end_date = end
            svc.assignment = target
            svc.save(
                update_fields=[
                    "assignment",
                    "period_source",
                    "specific_start_date",
                    "specific_end_date",
                ]
            )

        dupe.organization_relations.all().delete()
        dupe.delete()
