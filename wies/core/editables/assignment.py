"""Editables for Assignment. Reused by the inline-edit view and the assignment-create sheet.

Permissions live in ``wies/core/permissions.py``.
"""

import urllib.parse
from types import SimpleNamespace

from django import forms
from django.db import transaction
from django.db.models import Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from wies.core.fields import OrganizationsField
from wies.core.inline_edit import Editable, EditableCollection, EditableGroup, EditableSet
from wies.core.models import Assignment, AssignmentOrganizationUnit, Colleague, Skill
from wies.core.placement_visibility import LABELS, evaluate
from wies.core.services.urls import current_page_path
from wies.core.widgets import ComboBoxSelect


def _bdm_queryset(assignment=None):
    # A callable so `choices` evaluates lazily per request.
    #
    # The current owner is always included, even outside the BDM group: without a
    # matching option the combo box renders empty and saving clears the Business
    # Manager. Most owners are in fact not in that group.
    in_group = Q(user__groups__name="Business Development Manager")
    owner_id = getattr(assignment, "owner_id", None)
    if owner_id is not None:
        in_group |= Q(pk=owner_id)
    return Colleague.objects.filter(in_group).distinct().order_by("name")


def _owner_display_context(assignment, request) -> dict:
    """Builds the link and mailto for the owner display partial.

    Derived only from ``assignment`` and ``request``, never the current page's GET
    params, so both survive an inline-edit/cancel re-render on ``/inline-edit/``
    (#395).
    """
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
    # Atomic so a partial failure rolls back, preserving the existing selection.
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
    choices = [("", " "), ("__new__", "+ Nieuwe rol aanmaken")]
    choices.extend((str(s.public_id), s.name) for s in Skill.objects.order_by("name"))
    return choices


def _services_initial(assignment):
    """Returns one row per service, vacancies first."""
    from wies.core.models import Placement  # noqa: PLC0415 — avoids circular import

    # One prefetch for the latest placement per service, instead of a query each.
    services = (
        assignment.services.select_related("skill")
        .prefetch_related(
            Prefetch(
                "placements",
                # service__assignment keeps placement.start_date/end_date, which
                # resolve through service → assignment, from querying per row.
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
        # Compared on the effective period rather than placement.period_source,
        # which lies for a placement inheriting from a service with pinned dates.
        inherits_assignment_period = effective_start == assignment.start_date and effective_end == assignment.end_date
        rows.append(
            {
                # public_id strings: these identify the row across the client
                # boundary (panel URLs, the hidden form inputs, the teamlid
                # resolver). The integer PK never leaves the server; the audit
                # snapshot re-derives it from ``service`` below.
                "service_public_id": str(service.public_id),
                "assignment_public_id": str(assignment.public_id),
                "placement_public_id": str(placement.public_id) if placement else None,
                "skill": str(service.skill.public_id) if service.skill_id else "",
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
    """Returns viewer-filtered team rows for display.

    ``_services_initial`` returns every placement; here a placement that is not
    currently active is hidden from unrelated viewers — only the placed colleague
    and the BM-owner see it, flagged ``historical`` with a label and privacy note.
    """
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
    # prefix="service" matches what the member-edit sheet posts under.
    from wies.core.forms import ServiceFormSet  # noqa: PLC0415 — avoids circular import

    kwargs = {"prefix": "service", "form_kwargs": {"skill_choices": _skill_choices()}}
    if data is not None:
        return ServiceFormSet(data, **kwargs)
    return ServiceFormSet(initial=initial or [], **kwargs)


def _services_form_factory(data=None, initial=None):
    from wies.core.forms import ServiceForm  # noqa: PLC0415 — avoids circular import

    kwargs = {"skill_choices": _skill_choices()}
    if data is not None:
        return ServiceForm(data, **kwargs)
    return ServiceForm(initial=initial, **kwargs)


def _fmt_date(value) -> str | None:
    """Returns an ISO string, since dates are not JSON-serialisable in audit state."""
    return value.isoformat() if value else None


def _service_audit_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "skill_name": row["skill_name"],
        "colleague_name": row["colleague"].name if row["colleague"] else None,
        "description": row["description"] or "",
        # Included so a period-only edit registers as a change (#393).
        "has_custom_period": row["has_custom_period"],
        "start_date": _fmt_date(row["placement_start_date"]),
        "end_date": _fmt_date(row["placement_end_date"]),
    }


def _services_audit_state(assignment) -> list[dict]:
    # The audit snapshot keys on the integer PK; _services_initial rows now carry
    # only the public_id, so re-derive the PK from the row's service instance.
    return [_service_audit_row({**row, "id": row["service"].id}) for row in _services_initial(assignment)]


def placement_audit_row(placement) -> dict:
    """Returns an audit row for one placement, shaped like a services-collection row.

    Lets a period edit made directly on a placement show on the assignment
    timeline, not only via "Team bewerken" (#393).
    """
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
    # `has_custom_period` is inverted: truthy means inherited, not custom. The
    # dates show either way so the old period stays visible (#393).
    if row.get("has_custom_period"):
        return f"{period} (volgt opdracht)"
    return period


def _date_nl(iso: str | None) -> str | None:
    """Converts ISO yyyy-mm-dd to Dutch dd-mm-yyyy for timeline display."""
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
    """Returns the names ``viewer`` may already see on this assignment.

    Cached on the request, keyed by assignment: the timeline calls this once per
    team event and ``visible_service_rows`` costs a query each time. The request
    is the cache key because the answer depends on the viewer, and a request has
    exactly one.
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


def team_changes_are_restricted(assignment, request, changes: list[dict]) -> bool:
    """Returns whether these team rows name anyone not everyone on this assignment sees.

    Drives the note on a timeline row: the BM gets the unfiltered list and should
    know a row is hidden from others. Tested against what an outsider would see,
    not against the viewer's own rights, since their own name would otherwise
    always make the row look visible.
    """
    if not changes:
        return False
    # visible_service_rows only reads request.user, so a bare object without one
    # yields the rows as an outsider sees them.
    public_rows = visible_service_rows(assignment, SimpleNamespace(user=None))
    public_names = {row["colleague"].name for row in public_rows if row["colleague"]}
    return any(not _change_colleague_names(change) <= public_names for change in changes)


def _services_visible_changes(assignment, request, changes: list[dict]) -> list[dict]:
    """Returns viewer-filtered team changes for the audit timeline.

    Mirrors ``visible_service_rows``: a change survives only if every name it
    mentions is one the viewer may already see, so vacancies always survive.
    Matched on the colleague name rather than the row id, because the snapshot is
    frozen and a since-removed or re-filled row would leak the earlier name.
    Changes are dropped whole rather than redacted, so the timeline cannot betray
    that a hidden placement exists.
    """
    viewer = getattr(getattr(request, "user", None), "colleague", None)
    if viewer is not None and assignment.owner_id == viewer.id:
        return changes
    allowed = _visible_colleague_names(assignment, request, viewer)
    return [change for change in changes if _change_colleague_names(change) <= allowed]


def _services_render_change(change: dict) -> dict:
    """Returns one clause per change, phrased to slot into the timeline's running
    sentence ("<auteur> heeft <clause>, <clause> en <clause>.").
    """
    old, new = change.get("old"), change.get("new")
    if old is None:
        return {"text": f"{_service_row_label(new)} toegevoegd"}
    if new is None:
        return {"text": f"{_service_row_label(old)} verwijderd"}
    old_label = _service_row_label(old)
    new_label = _service_row_label(new)
    if old_label != new_label:
        return {"text": f"{old_label} naar {new_label} gewijzigd"}
    old_period = _period_label(old)
    new_period = _period_label(new)
    if old_period != new_period:
        return {"text": f"de periode van {new_label} van {old_period} naar {new_period} gewijzigd"}
    old_desc = old.get("description") or ""
    new_desc = new.get("description") or ""
    if not old_desc:
        return {"text": f'de toelichting "{new_desc}" voor {new_label} toegevoegd'}
    if not new_desc:
        return {"text": f'de toelichting "{old_desc}" voor {new_label} verwijderd'}
    return {"text": f'de toelichting voor {new_label} van "{old_desc}" naar "{new_desc}" gewijzigd'}


def _validate_period(cleaned):
    """Rejects an end date before the start date, across the period group."""
    from django.core.exceptions import ValidationError  # noqa: PLC0415

    start, end = cleaned.get("start_date"), cleaned.get("end_date")
    if start and end and end < start:
        raise ValidationError({"end_date": "Einddatum moet na startdatum liggen."})
    return cleaned


def _save_period(assignment, cleaned):
    """Saves the assignment period."""
    assignment.start_date = cleaned.get("start_date")
    assignment.end_date = cleaned.get("end_date")
    assignment.save(update_fields=["start_date", "end_date"])


class AssignmentEditables(EditableSet):
    class Meta:
        model = Assignment

    audit_events = True

    name = Editable(
        label="Opdrachtnaam",
        error_messages={"required": "Opdrachtnaam is verplicht"},
    )

    extra_info = Editable(
        label="Opdrachtomschrijving",
        widget=forms.Textarea(attrs={"rows": 2}),
        display="forms/displays/textarea.html",
    )

    start_date = Editable(label="Startdatum")

    end_date = Editable(label="Einddatum")

    owner = Editable(
        label="Business Manager",
        choices=_bdm_queryset,
        widget=ComboBoxSelect,
        required=True,
        empty_label=" ",
        error_messages={"required": "Selecteer een business manager."},
        audit_state=lambda c: c.name if c else None,
        display="forms/displays/assignment_owner.html",
        display_context=_owner_display_context,
    )

    period = EditableGroup(
        label="Opdrachtperiode",
        fields=[start_date, end_date],
        clean=_validate_period,
        save=_save_period,
        display="forms/displays/assignment_period.html",
    )

    organizations = Editable(
        label="Opdrachtgever(s)",
        form_field_factory=lambda: OrganizationsField(required=True),
        initial=_organizations_initial,
        save=_save_organizations,
        audit_state=_organizations_audit_state,
        render_change=_organizations_render_change,
        display="forms/displays/organizations.html",
    )

    # No form_template/save: the collection is not edited in place. The per-member
    # sheet (assignment_member_edit_view) uses `form_factory` (one row at a time)
    # and audits via member_audit_event, so the audit hooks below still apply.
    services = EditableCollection(
        label="Team",
        formset_factory=_services_formset_factory,
        form_factory=_services_form_factory,
        initial=_services_initial,
        audit_state=_services_audit_state,
        render_change=_services_render_change,
        visible_changes=_services_visible_changes,
        hide_edit_button=True,
        display="forms/displays/assignment_services.html",
        display_context=_services_display_context,
    )
