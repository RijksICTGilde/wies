"""Editables for Assignment. Reused by the inline-edit view and AssignmentCreateForm.

Permissions live in ``wies/core/permission_rules.py``.
"""

import urllib.parse

from django import forms
from django.db import transaction
from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone

from wies.core.fields import OrganizationsField
from wies.core.inline_edit import Editable, EditableCollection, EditableGroup, EditableSet
from wies.core.models import Assignment, AssignmentOrganizationUnit, Colleague, Skill
from wies.core.placement_visibility import LABELS, evaluate
from wies.core.services.assignments import apply_services_to_assignment, extract_services_data
from wies.core.services.urls import current_page_path


def _bdm_queryset():
    # Wrapped in a callable so `choices` evaluates lazily per request.
    return Colleague.objects.filter(user__groups__name="Business Development Manager").order_by("name")


def _owner_display_context(assignment, request) -> dict:
    """Link + mailto for the owner display partial. Derived only from
    ``assignment``/``request`` (not the current page's GET params) so they
    survive an inline-edit/cancel re-render on the ``/inline-edit/`` path (#395)."""
    if not assignment.owner:
        return {"owner_url": "", "owner_mailto": ""}

    base_url = current_page_path(request)
    owner_url = f"{base_url}?collega={assignment.owner.public_id}"

    owner_mailto = ""
    if assignment.owner.email:
        opdracht_url = request.build_absolute_uri(reverse("assignment-list") + f"?opdracht={assignment.public_id}")
        subject = urllib.parse.quote(f"Informatieverzoek over opdracht {assignment.name}")
        body_lines = [
            f"Beste {assignment.owner.name},",
            "",
            f"Ik zag deze opdracht {opdracht_url} op WIES."
            + (f" De beschrijving is: {assignment.extra_info}" if assignment.extra_info else ""),
            "",
            "Kun je me hier meer informatie over geven?",
        ]
        consultant_name = getattr(getattr(request.user, "colleague", None), "name", "")
        body_lines += ["", "Met vriendelijke groet,", "", consultant_name]
        body = urllib.parse.quote("\n".join(body_lines))
        owner_mailto = f"mailto:{assignment.owner.email}?subject={subject}&body={body}"

    return {"owner_url": owner_url, "owner_mailto": owner_mailto}


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


def _organizations_audit_state(value) -> list[dict]:
    if not value:
        return []
    return [{"name": (row["organization"].label or row["organization"].name), "role": row["role"]} for row in value]


def _organizations_render_change(state) -> str:
    if not state:
        return "geen"
    parts = []
    for row in state:
        if row["role"] == "PRIMARY":
            parts.append(f"{row['name']} (primair)")
        else:
            parts.append(row["name"])
    return ", ".join(parts)


def _skill_choices():
    # Matches the shape used by assignment-create so service_row.html renders identically.
    choices = [("", " "), ("__new__", "+ Nieuwe rol aanmaken")]
    choices.extend((str(s.id), s.name) for s in Skill.objects.order_by("name"))
    return choices


def _services_initial(assignment):
    """One row per service, vacancies first."""
    from wies.core.models import Placement  # noqa: PLC0415 — avoids circular import

    # Latest placement per service, fetched in one prefetch instead of a query per service.
    services = (
        assignment.services.select_related("skill")
        .prefetch_related(
            Prefetch(
                "placements",
                # service__assignment so placement.start_date/end_date (which resolve
                # through service → assignment) don't each trigger their own query.
                queryset=Placement.objects.select_related("colleague", "service__assignment").order_by("-id"),
                to_attr="ordered_placements",
            )
        )
        .order_by("id")
    )

    rows = []
    for service in services:
        placement = service.ordered_placements[0] if service.ordered_placements else None
        effective_start = placement.start_date if placement else service.start_date
        effective_end = placement.end_date if placement else service.end_date
        # Checkbox renders checked ("Neem opdrachtperiode over") only when
        # the row's effective period equals the assignment period — this
        # also covers placements that inherit from a service which itself
        # has pinned dates (where placement.period_source alone would lie).
        inherits_assignment_period = effective_start == assignment.start_date and effective_end == assignment.end_date
        rows.append(
            {
                "id": service.id,
                "placement_id": placement.id if placement else None,
                "skill": str(service.skill_id) if service.skill_id else "",
                "skill_name": service.skill.name if service.skill else "",
                "description": service.description,
                "is_filled": "ingevuld" if placement is not None else "aanvraag",
                "colleague": placement.colleague if placement else None,
                "has_custom_period": inherits_assignment_period,
                "placement_start_date": effective_start,
                "placement_end_date": effective_end,
                "placement": placement,
                "service": service,
            }
        )
    rows.sort(key=lambda r: r["is_filled"])
    return rows


def visible_service_rows(assignment, request) -> list[dict]:
    """Viewer-filtered team rows for display. ``_services_initial`` (used by the
    formset and audit state) returns every placement; here a placement that is
    not currently active (ended or not yet started) is hidden from unrelated
    viewers — only the placed colleague and the BM-owner see it, flagged
    ``historical`` with a chip label and a privacy note."""
    today = timezone.now().date()
    viewer = getattr(getattr(request, "user", None), "colleague", None)
    viewer_is_bm = viewer is not None and assignment.owner_id == viewer.id

    visible = []
    for row in _services_initial(assignment):
        placement = row["placement"]
        if placement is None:  # vacancy → visible to everyone
            visible.append(row)
            continue
        result = evaluate(
            row["placement_start_date"], row["placement_end_date"], placement.colleague_id, viewer, viewer_is_bm, today
        )
        if not result.visible:
            continue
        if result.timing == "active":
            visible.append(row)
        else:
            visible.append(
                {
                    **row,
                    "historical": True,
                    "period_label": LABELS[result.timing],
                    "privacy_warning_text": result.privacy_note,
                }
            )
    return visible


def _services_display_context(assignment, request) -> dict:
    return {"value": visible_service_rows(assignment, request)}


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


def _fmt_date(value) -> str | None:
    """ISO string for JSON-serialisable audit state (dates aren't JSON-native)."""
    return value.isoformat() if value else None


def _service_audit_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "skill_name": row["skill_name"],
        "colleague_name": row["colleague"].name if row["colleague"] else None,
        "description": row["description"] or "",
        # Period included so a period-only edit registers as a change (#393).
        "has_custom_period": row["has_custom_period"],
        "start_date": _fmt_date(row["placement_start_date"]),
        "end_date": _fmt_date(row["placement_end_date"]),
    }


def _services_audit_state(assignment) -> list[dict]:
    return [_service_audit_row(row) for row in _services_initial(assignment)]


def placement_audit_row(placement) -> dict:
    """Audit row for a single placement, shaped like a services-collection
    row so the same timeline renderer applies. Lets a period edit made
    directly on a placement (via the profile) show on the opdracht
    timeline, not only via "Team bewerken" (#393)."""
    from wies.core.models import Placement  # noqa: PLC0415 — avoids circular import

    service = placement.service
    return _service_audit_row(
        {
            "id": service.id,
            "skill_name": service.skill.name if service.skill else "",
            "colleague": placement.colleague,
            "description": service.description,
            "has_custom_period": placement.period_source != Placement.PLACEMENT,
            "placement_start_date": placement.start_date,
            "placement_end_date": placement.end_date,
        }
    )


def _service_row_label(row: dict) -> str:
    skill = row.get("skill_name") or "?"
    name = row.get("colleague_name")
    return f"{skill} ({name if name else 'open'})"


def _period_label(row: dict) -> str:
    start = _date_nl(row.get("start_date"))
    end = _date_nl(row.get("end_date"))
    period = f"{start or '?'} t/m {end or '?'}"
    # `has_custom_period` is inverted: truthy means inherited, not custom.
    # Show the dates either way so the old period stays visible (#393).
    if row.get("has_custom_period"):
        return f"{period} (volgt opdracht)"
    return period


def _date_nl(iso: str | None) -> str | None:
    """ISO yyyy-mm-dd → Dutch dd-mm-yyyy for timeline display."""
    if not iso:
        return None
    y, m, d = iso.split("-")
    return f"{d}-{m}-{y}"


def _change_colleague_names(change: dict) -> set[str]:
    names = set()
    for side in ("old", "new"):
        row = change.get(side)
        if row and row.get("colleague_name"):
            names.add(row["colleague_name"])
    return names


def _visible_colleague_names(assignment, request, viewer) -> set[str]:
    """Names ``viewer`` may already see on this opdracht.

    Cached on the request, keyed by opdracht: the timeline calls this once per
    team event and ``visible_service_rows`` costs a query each time. Keyed on
    the request rather than the assignment instance because the answer depends
    on the viewer, and a request has exactly one.
    """
    if not hasattr(request, "wies_visible_colleague_names"):
        request.wies_visible_colleague_names = {}
    cache = request.wies_visible_colleague_names
    if assignment.id not in cache:
        names = {row["colleague"].name for row in visible_service_rows(assignment, request) if row["colleague"]}
        if viewer is not None:
            names.add(viewer.name)
        cache[assignment.id] = names
    return cache[assignment.id]


def _services_visible_changes(assignment, request, changes: list[dict]) -> list[dict]:
    """Viewer-filtered team changes for the audit timeline, mirroring
    ``visible_service_rows``: a name the team list hides must not resurface
    here. Keyed on the colleague *name* in the snapshot, not the row id: the
    snapshot is frozen, so a row whose placement was since removed or re-filled
    would otherwise leak the earlier name.

    A change survives only if every name it mentions is one the viewer may
    already see on this opdracht. Vacancies name nobody and always survive.
    Dropped whole rather than redacted, so the timeline cannot betray that a
    hidden placement exists (same reason ``team_count`` is filtered)."""
    viewer = getattr(getattr(request, "user", None), "colleague", None)
    if viewer is not None and assignment.owner_id == viewer.id:
        return changes
    allowed = _visible_colleague_names(assignment, request, viewer)
    return [change for change in changes if _change_colleague_names(change) <= allowed]


def _services_render_change(change: dict) -> dict:
    old, new = change.get("old"), change.get("new")
    if old is None:
        return {"text": f"Toegevoegd: {_service_row_label(new)}"}
    if new is None:
        return {"text": f"Verwijderd: {_service_row_label(old)}"}
    old_label = _service_row_label(old)
    new_label = _service_row_label(new)
    if old_label != new_label:
        return {"text": f"Gewijzigd: van {old_label} naar {new_label}"}
    old_period = _period_label(old)
    new_period = _period_label(new)
    if old_period != new_period:
        return {"text": f"Periode gewijzigd van {new_label}", "old": old_period, "new": new_period}
    old_desc = old.get("description") or ""
    new_desc = new.get("description") or ""
    if not old_desc:
        return {"text": f"Toelichting toegevoegd voor {new_label}", "new": new_desc}
    if not new_desc:
        return {"text": f"Toelichting verwijderd voor {new_label}", "old": old_desc}
    return {"text": f"Toelichting gewijzigd voor {new_label}", "old": old_desc, "new": new_desc}


def _validate_period(cleaned):
    """Reject end-before-start. Cross-field validation for the period group."""
    from django.core.exceptions import ValidationError  # noqa: PLC0415

    start, end = cleaned.get("start_date"), cleaned.get("end_date")
    if start and end and end < start:
        raise ValidationError({"end_date": "Einddatum moet na startdatum liggen."})
    return cleaned


def _save_period(assignment, cleaned):
    """Save assignment period."""
    assignment.start_date = cleaned.get("start_date")
    assignment.end_date = cleaned.get("end_date")
    assignment.save(update_fields=["start_date", "end_date"])


class AssignmentEditables(EditableSet):
    class Meta:
        model = Assignment

    audit_events = True

    name = Editable(
        label="Opdracht naam",
        error_messages={"required": "Opdracht naam is verplicht"},
    )

    extra_info = Editable(
        label="Opdrachtomschrijving",
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
        audit_state=lambda c: c.name if c else None,
        display="rvo/forms/displays/assignment_owner.html",
        display_context=_owner_display_context,
    )

    period = EditableGroup(
        label="Opdrachtperiode",
        fields=[start_date, end_date],
        clean=_validate_period,
        save=_save_period,
        display="rvo/forms/displays/assignment_period.html",
    )

    organizations = Editable(
        label="Opdrachtgever(s)",
        form_field_factory=lambda: OrganizationsField(required=True),
        initial=_organizations_initial,
        save=_save_organizations,
        audit_state=_organizations_audit_state,
        render_change=_organizations_render_change,
        display="rvo/forms/displays/organizations.html",
    )

    services = EditableCollection(
        label="Team",
        formset_factory=_services_formset_factory,
        initial=_services_initial,
        save=_save_services,
        audit_state=_services_audit_state,
        render_change=_services_render_change,
        visible_changes=_services_visible_changes,
        hide_edit_button=True,
        form_template="parts/assignment_services_form.html",
        display="rvo/forms/displays/assignment_services.html",
        display_context=_services_display_context,
    )
