from __future__ import annotations

from contextlib import contextmanager
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

    ``service_public_id`` and ``placement_public_id`` round-trip existing
    Service / Placement public_ids (as canonical strings), and are ``None`` for a
    newly added row. They come from attacker-controllable hidden inputs, so
    add_service_to_assignment re-verifies ownership before writing.
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
        # carries, so add_service_to_assignment drops the placement.
        is_aanvraag = cd.get("is_filled") == "aanvraag"
        colleague = cd.get("colleague")
        services_data.append(
            {
                # UUIDField.clean() yields a uuid.UUID; str() makes it comparable
                # to str(public_id) and safe for filter(public_id=...).
                "service_public_id": str(cd["service_public_id"]) if cd.get("service_public_id") else None,
                "placement_public_id": str(cd["placement_public_id"]) if cd.get("placement_public_id") else None,
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
def add_service_to_assignment(assignment: Assignment, svc: dict) -> Service:
    """Creates or updates a single Service (and its Placement) on ``assignment``.

    ``service_public_id`` and ``placement_public_id`` are attacker-controllable
    hidden inputs; a public_id not belonging to this assignment raises
    ``ValidationError`` rather than silently creating rows, keeping stale-form
    races and malicious posts equally visible.

    Placement per row: ``placement_public_id`` + ``colleague_id`` → updated;
    ``placement_public_id`` alone → deleted (filled→aanvraag); ``colleague_id``
    alone → created.
    """
    skill = _resolve_skill(svc)

    service_public_id = svc.get("service_public_id")
    if service_public_id:
        service = assignment.services.filter(public_id=service_public_id).first()
        if service is None:
            msg = "Een of meer diensten bestaan niet meer. Herlaad de pagina en probeer opnieuw."
            raise ValidationError(msg)
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

    _apply_placement(assignment, service, svc)
    return service


def _apply_placement(assignment: Assignment, service: Service, svc: dict) -> None:
    """Creates, updates or deletes ``service``'s Placement from a services_data row."""
    placement_public_id = svc.get("placement_public_id")
    colleague_id = svc.get("colleague_id")

    if placement_public_id:
        placement = Placement.objects.filter(public_id=placement_public_id, service__assignment=assignment).first()
        if placement is None:
            msg = "Een of meer plaatsingen bestaan niet meer. Herlaad de pagina en probeer opnieuw."
            raise ValidationError(msg)
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
) -> Assignment:
    """Creates an Assignment with its organization links.

    Services and roles are added afterwards, one at a time, via the assignment
    panel (``add_service_to_assignment``), so none are created here.
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


@contextmanager
def member_audit_event(request, assignment):
    """Wraps a single-service mutation, emitting one team-audit event around it.

    The mutation (e.g. ``add_service_to_assignment`` or ``service.delete()``) is
    written plainly inside the ``with`` block. The before/after snapshot stays
    whole-team, so the audit delta still reports exactly the one row that
    changed, keyed on the internal ``service.id``.
    """
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle
    from wies.core.inline_edit.audit import emit_inline_edit_audit_event  # noqa: PLC0415 — avoids import cycle

    spec = AssignmentEditables.services
    before = spec.audit_state(assignment) if spec.audit_state else None
    with transaction.atomic():
        yield
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
