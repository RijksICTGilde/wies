from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count

from wies.core.models import Assignment, AssignmentOrganizationUnit, Placement, Service, Skill
from wies.core.public_id import parse_public_ids

if TYPE_CHECKING:
    from datetime import date

    from wies.core.models import Colleague


def _skill_ids_by_public_id(service_formset) -> dict[str, int]:
    """Maps the submitted skill tokens to internal ids in one query.

    The rol select posts public_ids; everything downstream keys on the internal id.
    """
    tokens = [
        f.cleaned_data.get("skill")
        for f in service_formset
        if f.cleaned_data and f.cleaned_data.get("skill") not in (None, "", "__new__")
    ]
    if not tokens:
        return {}
    rows = Skill.objects.filter(public_id__in=parse_public_ids(tokens)).values_list("public_id", "id")
    return {str(public_id): skill_id for public_id, skill_id in rows}


def extract_services_data(service_formset) -> list[dict]:
    """Extracts services_data dicts from a validated ServiceFormSet.

    ``id`` and ``placement_id`` round-trip existing Service / Placement PKs, and
    are ``None`` for rows added on the create form. They come from
    attacker-controllable hidden inputs, so apply_services_to_assignment
    re-verifies ownership before writing.
    """
    skill_ids = _skill_ids_by_public_id(service_formset)
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
        skill_id = skill_ids.get(skill_val) if skill_val and skill_val != "__new__" else None
        # "aanvraag" marks a vacancy: ignore any colleague the hidden select still
        # carries, so apply_services_to_assignment drops the placement.
        is_aanvraag = cd.get("is_filled") == "aanvraag"
        colleague = cd.get("colleague")
        services_data.append(
            {
                "id": cd.get("id"),
                "placement_id": cd.get("placement_id"),
                "description": cd.get("description", ""),
                "skill_id": skill_id,
                "new_skill_name": new_skill if skill_val == "__new__" else None,
                "status": "OPEN",
                "colleague_id": colleague.id if colleague and not is_aanvraag else None,
                "has_custom_period": cd.get("has_custom_period", False),
                "placement_start_date": cd.get("placement_start_date"),
                "placement_end_date": cd.get("placement_end_date"),
            }
        )
    return services_data


def _resolve_skill(svc: dict) -> Skill | None:
    """Resolves the Skill for a services_data row.

    ``new_skill_name`` wins (get_or_create); otherwise ``skill_id`` is looked up.
    """
    if svc.get("new_skill_name"):
        skill, _ = Skill.objects.get_or_create(name=svc["new_skill_name"])
        return skill
    if svc.get("skill_id"):
        return Skill.objects.filter(id=svc["skill_id"]).first()
    return None


@transaction.atomic
def apply_services_to_assignment(assignment: Assignment, services_data: list[dict] | None) -> None:
    """Syncs an Assignment's Services and Placements to match ``services_data``.

    ``id`` and ``placement_id`` are attacker-controllable hidden inputs; a PK not
    belonging to this assignment raises ``ValidationError`` rather than silently
    creating rows, keeping stale-form races and malicious posts equally visible.

    Services: no ``id`` → created; ``id`` → updated in place; existing but not
    submitted → deleted (cascading to its Placements).

    Placements per row: ``placement_id`` + ``colleague_id`` → updated;
    ``placement_id`` alone → deleted; ``colleague_id`` alone → created.
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
    """Creates an Assignment with related Services, Placements and organization links.

    Each ``services_data`` row holds ``description``, ``skill_id``,
    ``new_skill_name`` (creates a Skill when set), ``status`` and ``colleague_id``.
    Create-form rows carry no ``id`` / ``placement_id``, so
    apply_services_to_assignment takes the create-everything branch.
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


def assignment_create_specs():
    """Returns the create-form specs: the same fields as the edit sheet, but
    without an object and without a per-object permission check — creating is
    gated on ``core.add_assignment``.
    """
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle

    specs = [
        AssignmentEditables.name,
        AssignmentEditables.extra_info,
        AssignmentEditables.organizations,
        AssignmentEditables.period,
        AssignmentEditables.owner,
    ]
    return [(AssignmentEditables, spec, None) for spec in specs]


def create_assignment_from_specs(cleaned_data: dict) -> Assignment:
    """Creates an Assignment from the combined assignment form's cleaned_data.

    Services and roles are added afterwards via the assignment panel, so no
    services_data is passed here.
    """
    orgs = cleaned_data.get("organizations") or []
    primary_org = next((o["organization"] for o in orgs if o["role"] == "PRIMARY"), None)
    involved_orgs = [o["organization"] for o in orgs if o["role"] == "INVOLVED"]
    return create_assignment_from_form(
        name=cleaned_data["name"],
        extra_info=cleaned_data.get("extra_info", ""),
        start_date=cleaned_data.get("start_date"),
        end_date=cleaned_data.get("end_date"),
        owner=cleaned_data.get("owner"),
        primary_organization_id=primary_org.id if primary_org else None,
        involved_organization_ids=[o.id for o in involved_orgs],
    )


def find_duplicate_groups():
    """Finds assignments that share the same name, owner and primary organization."""
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
    """Merges duplicate assignments into the first (lowest-id) one.

    Services and their placements move to the target with explicit dates pinned,
    the target's period widens to cover all of them, and the emptied duplicates
    are deleted.
    """
    target = assignments[0]
    duplicates = assignments[1:]

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


def initial_row_to_services_data(row) -> dict:
    """Converts a _services_initial row into a services_data dict, for rows a
    member endpoint leaves untouched.

    Mirrors ServiceForm.clean: the row checkbox means "inherit the assignment
    period", while has_custom_period in apply_services_to_assignment means "pin
    these dates".
    """
    inherits = row["has_custom_period"]
    has_dates = bool(row["placement_start_date"] or row["placement_end_date"])
    # ``skill`` is a public_id; resolve it to the internal id.
    skill_id = None
    if row["skill"]:
        skill_id = Skill.objects.filter(public_id=row["skill"]).values_list("id", flat=True).first()
    return {
        "id": row["id"],
        "placement_id": row["placement_id"],
        "description": row["description"],
        "skill_id": skill_id,
        "new_skill_name": None,
        "status": "OPEN",
        "colleague_id": row["colleague"].id if (row["colleague"] and row["is_filled"] == "ingevuld") else None,
        "has_custom_period": (not inherits) and has_dates,
        "placement_start_date": None if inherits else row["placement_start_date"],
        "placement_end_date": None if inherits else row["placement_end_date"],
    }


def apply_team_change(request, assignment, services_data):
    """Syncs the team, emitting the same audit events as the inline-edit route."""
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle
    from wies.core.inline_edit.audit import emit_inline_edit_audit_event  # noqa: PLC0415 — avoids import cycle

    spec = AssignmentEditables.services
    before = spec.audit_state(assignment) if spec.audit_state else None
    with transaction.atomic():
        apply_services_to_assignment(assignment, services_data)
        after = spec.audit_state(assignment) if spec.audit_state else None
        emit_inline_edit_audit_event(
            AssignmentEditables, spec, assignment, before, after, request.user, request=request
        )


def assignment_edit_specs(assignment, user, only=None):
    """Returns the combined assignment form's specs, filtered by permission.

    ``only`` (a spec name) narrows it to one field: a row's ⋯-menu edits just that
    field, while the pencil edits everything.
    """
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle
    from wies.core.permission_engine import Verb, has_permission  # noqa: PLC0415

    candidates = [
        AssignmentEditables.name,
        AssignmentEditables.extra_info,
        AssignmentEditables.organizations,
        AssignmentEditables.period,
        AssignmentEditables.owner,
    ]
    if only is not None:
        candidates = [spec for spec in candidates if spec.name == only]
    return [
        (AssignmentEditables, spec, assignment)
        for spec in candidates
        if has_permission(Verb.UPDATE, assignment, user, spec)
    ]
