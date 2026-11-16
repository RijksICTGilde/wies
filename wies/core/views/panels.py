"""Side-panel data for an opdracht, collega and aanvraag, shared by the list pages."""

import urllib.parse

from django.http import Http404, QueryDict
from django.urls import reverse
from django.utils import timezone

from wies.core.inline_edit.forms import (
    build_combined_form_class,
)
from wies.core.models import (
    DEFAULT_HOURS_PER_WEEK,
    Assignment,
    AssignmentOrganizationUnit,
    Placement,
    Service,
)
from wies.core.permission_engine import Verb, has_permission
from wies.core.querysets import (
    annotate_placement_dates,
    label_categories_for_everyone,
)
from wies.core.roles import (
    can_view_role_hours,
)
from wies.core.services.aanvragen import (
    aanvraag_role,
    team_names_text,
)
from wies.core.services.assignments import (
    assignment_edit_specs,
    external_source,
)
from wies.core.services.dates import request_period_text
from wies.core.services.occupancy import (
    PHASE_BY_TIMING,
    placement_order_key,
)
from wies.core.services.placements import (
    placement_edit_specs,
)
from wies.core.visibility_rules import (
    LABELS,
    evaluate_assignment_visibility,
    evaluate_placement_visibility,
)

from ._common import _build_close_url, _build_panel_url, _is_side_panel_request, _resolve_panel_object, _url_drop_params
from .inline_edit import _spec_label


def _build_assignment_panel_data(assignment, request):
    """Builds the assignment panel context, shared by both views."""
    from wies.core.editables.assignment import (  # noqa: PLC0415
        AssignmentEditables,
        _organizations_initial,
        _owner_display_context,
        visible_service_rows,
    )

    team_rows = visible_service_rows(assignment, request)
    for row in team_rows:
        # The viewer's own row: its menu speaks of "mijn", not "teamlid".
        row["is_viewer"] = bool(row["colleague"]) and row["colleague"].user_id == request.user.id
    data = {
        "panel_content_template": "parts/assignment_panel_content.html",
        "panel_title": assignment.name,
        "close_url": _build_close_url(request),
        "assignment": assignment,
        "team_rows": team_rows,
        # Same human label as the "Externe bron" row, so the intro says "OTYS",
        # not the raw key "otys_iir".
        "team_external_source": external_source(assignment),
        "user_can_edit": bool(assignment_edit_specs(assignment, request.user)),
        "user_can_delete": has_permission(Verb.DELETE, assignment, request.user),
        "user_can_edit_team": has_permission(Verb.UPDATE, assignment, request.user, AssignmentEditables.services),
        "show_updates_tab": assignment.source != "otys_iir",
        "organization_count": assignment.organization_relations.count(),
        # Read-only display context: per-field inline edit was replaced by the
        # edit child sheet, so the panel shows values directly.
        "organization_rows": _organizations_initial(assignment),
        "owner_display": _owner_display_context(assignment, request),
        "edit_panel_url": _build_panel_url(request, opdracht=assignment.public_id, bewerken=1),
        "member_add_aanvraag_url": _build_panel_url(request, opdracht=assignment.public_id, teamlid="nieuw-aanvraag"),
        "member_add_ingevuld_url": _build_panel_url(request, opdracht=assignment.public_id, teamlid="nieuw-ingevuld"),
    }
    # Child sheets: ?bewerken= opens the combined assignment form, ?teamlid= the
    # form for one team member. Without the rights the param falls back to the
    # read-only panel.
    if request.GET.get("bewerken"):
        edit_panel = _build_assignment_edit_panel_data(assignment, request)
        if edit_panel is not None:
            data.update(edit_panel)
    elif request.GET.get("teamlid"):
        member_panel = _build_assignment_member_panel_data(assignment, request) or _build_own_role_panel_data(
            request, team_rows
        )
        if member_panel is not None:
            data.update(member_panel)
    return data


def _build_own_role_panel_data(request, team_rows):
    """The "Taken wijzigen" sheet for a placed consultant's own row
    (``?teamlid=`` without team edit rights), or None when the row is not theirs."""
    teamlid = request.GET.get("teamlid", "")
    row = next((r for r in team_rows if r["service_public_id"] == teamlid and r.get("can_edit_role")), None)
    if row is None:
        return None
    return _build_placement_edit_panel_data(
        row["placement"],
        request,
        only="skill",
        parent_url=_url_drop_params(request.path, request.GET, ("teamlid",)),
    )


def _build_assignment_create_panel_data(request, form, *, parent_url=None):
    """Builds panel_data for the empty or invalid create form.

    Shared by the list GET branch (``?nieuwe-opdracht``) and the POST handler.
    ``parent_url`` lets an invalid POST pass the sanitised ``terug_url`` back, so
    the return address survives a failed submit.
    """
    return {
        "form": form,
        "panel_content_template": "parts/assignment_create_panel_content.html",
        "edit_url": reverse("assignment-create-sheet"),  # POST target
        "parent_url": parent_url if parent_url is not None else _build_close_url(request),
        "edit_heading": "Opdracht invoeren",
        "submit_label": "Voer opdracht in",
    }


def _merge_preview_rows(group) -> list[dict]:
    """One row per placement for the merge preview: assignment, consultant, fate.

    The first assignment in the group is the one that stays; everything else
    moves into it. A service without placements is a vacancy and still counts as
    a line, because it moves along too.
    """
    target = group[0]
    rows = []
    for assignment in group:
        keeps = assignment.id == target.id
        # Indicative, not imperative: this describes what happens, it is not a
        # button. Source and destination both sit in the sentence, so a row reads
        # on its own without a separate assignment column.
        action = f"Blijft in opdracht {target.id}" if keeps else f"Van opdracht {assignment.id} naar {target.id}"
        for service in assignment.services.all():
            names = [placement.colleague.name for placement in service.placements.all()]
            if names:
                rows.extend({"consultant": name, "vacant": False, "action": action, "keeps": keeps} for name in names)
            else:
                rows.append({"consultant": "Vacant", "vacant": True, "action": action, "keeps": keeps})
    return rows


def _merge_date_range(existing: dict, start, end):
    """Widen the date range of an assignment entry to include the given start/end."""
    if start and (existing["start_date"] is None or start < existing["start_date"]):
        existing["start_date"] = start
    if end and (existing["end_date"] is None or end > existing["end_date"]):
        existing["end_date"] = end


def _make_assignment_entry(
    name, aid, request, public_id=None, start_date=None, end_date=None, colleague_public_id=None, **extra
):
    """Build a standard assignment dict for panel display.

    With ``colleague_public_id`` the card opens the opdracht panel with that
    colleague's own card unfolded; without it, the plain opdracht panel.
    """
    params = {"opdracht": public_id}
    if colleague_public_id:
        params["collega"] = colleague_public_id
    url = _build_panel_url(request, **params)
    return {
        "name": name,
        "id": aid,
        "public_id": public_id,
        "tags": {},
        "assignment_url": url,
        "start_date": start_date,
        "end_date": end_date,
        "historical": False,
        "privacy_warning_text": None,
        **extra,
    }


def _get_colleague_assignments(request, colleague):
    from wies.core.editables.service import ServiceEditables  # noqa: PLC0415 — avoids import cycle

    today = timezone.now().date()

    active_by_id: dict[int, dict] = {}
    historical_by_id: dict[int, dict] = {}

    # --- Placements (both active and ended) ---
    placement_qs = (
        Placement.objects.filter(colleague=colleague)
        .select_related("service__assignment", "service__skill")
        .values(
            "id",
            "public_id",
            "service__assignment__id",
            "service__assignment__public_id",
            "service__assignment__name",
            "service__assignment__source",
            "service__assignment__start_date",
            "service__assignment__end_date",
            "service__skill__name",
            "service__public_id",
            "service__description",
            "service__hours_per_week",
        )
        .distinct()
    )
    placement_qs = annotate_placement_dates(placement_qs)
    # Every placement here is this colleague's, so the hours rule is one answer.
    show_hours = can_view_role_hours(request.user, Placement(colleague_id=colleague.id))
    # Likewise the right to edit the role text: it is the viewer's own row or it
    # is not, the same for every placement on this panel.
    viewer = getattr(request.user, "colleague", None)
    is_own_panel = viewer is not None and viewer.id == colleague.id

    # The pencil asks the rules, so it shows exactly when the sheet would open.
    own_services = (
        Service.objects.select_related("assignment")
        .filter(placements__colleague=colleague)
        .in_bulk(field_name="public_id")
        if is_own_panel
        else {}
    )
    for placement in placement_qs:
        assignment_id = placement["service__assignment__id"]
        start = placement.get("actual_start_date")
        end = placement.get("actual_end_date")
        # Active placements are public; ended or not-yet-started ones are only
        # visible to the placed colleague and the Business Managers.
        result = evaluate_placement_visibility(start, end, colleague.id, request, today)
        if not result.visible:
            continue

        bucket = active_by_id if result.timing == "active" else historical_by_id
        if assignment_id not in bucket:
            bucket[assignment_id] = _make_assignment_entry(
                placement["service__assignment__name"],
                assignment_id,
                request,
                start_date=start,
                end_date=end,
                historical=result.timing != "active",
                privacy_warning_text=result.privacy_note,
                period_label=LABELS.get(result.timing),
                public_id=placement["service__assignment__public_id"],
                colleague_public_id=colleague.public_id,
                phase=PHASE_BY_TIMING[result.timing],
            )
        else:
            _merge_date_range(bucket[assignment_id], start, end)
            # A planned and a finished placement share an entry; it sorts as planned.
            if result.timing == "future":
                bucket[assignment_id]["phase"] = PHASE_BY_TIMING["future"]
        # Per opdracht, not per panel: an externally sourced one is read-only
        # for everyone, so a pencil there would open nothing (#311).
        service = own_services.get(placement["service__public_id"])
        can_edit_own_role = service is not None and has_permission(
            Verb.UPDATE, service, request.user, ServiceEditables.description
        )
        edits_whole_team = can_edit_own_role and has_permission(Verb.UPDATE, service, request.user)
        skill_name = placement["service__skill__name"]
        if skill_name:
            # The open card shows the placement itself: its own dates, hours
            # (under the hours rule) and the role description.
            bucket[assignment_id]["tags"][skill_name] = {
                "description": placement["service__description"],
                "start": start,
                "end": end,
                "hours": placement["service__hours_per_week"] if show_hours else None,
                # The label names the sheet the right opens, not the pencil.
                "edit_url": (
                    _build_panel_url(
                        request,
                        opdracht=placement["service__assignment__public_id"],
                        collega=colleague.public_id,
                        teamlid=placement["service__public_id"],
                    )
                    if can_edit_own_role
                    else None
                ),
                "edit_label": "Mijn rol wijzigen" if edits_whole_team else "Mijn taken wijzigen",
            }

    # BM roles (active and ended)
    bm_assignments = Assignment.objects.filter(owner=colleague).values_list(
        "id", "public_id", "name", "start_date", "end_date"
    )
    for assignment_id, public_id, name, start_date, end_date in bm_assignments:
        # Active and not-yet-started owned assignments are public; ended ones are
        # only shown to a privileged viewer (the Business Manager role).
        result = evaluate_assignment_visibility(start_date, end_date, request, today)

        existing = historical_by_id.get(assignment_id) or active_by_id.get(assignment_id)
        if existing is not None:
            existing["tags"]["Business Manager"] = None
            continue
        if not result.visible:
            continue

        if result.timing == "ended":
            historical_by_id[assignment_id] = _make_assignment_entry(
                name,
                assignment_id,
                request,
                public_id=public_id,
                start_date=start_date,
                end_date=end_date,
                tags={"Business Manager": None},
                historical=True,
                privacy_warning_text=result.privacy_note,
                period_label=LABELS["ended"],
                phase=PHASE_BY_TIMING[result.timing],
            )
        else:
            active_by_id[assignment_id] = _make_assignment_entry(
                name,
                assignment_id,
                request,
                public_id=public_id,
                start_date=start_date,
                end_date=end_date,
                tags={"Business Manager": None},
                phase=PHASE_BY_TIMING[result.timing],
            )

    # Batch-fetch primary organization names for all assignments
    all_ids = set(active_by_id) | set(historical_by_id)
    primary_orgs = dict(
        AssignmentOrganizationUnit.objects.filter(
            assignment_id__in=all_ids,
            role="PRIMARY",
        ).values_list("assignment_id", "organization__name")
    )

    # Convert tag sets to sorted lists for deterministic template rendering
    for assignment in (*active_by_id.values(), *historical_by_id.values()):
        assignment["tags"] = sorted(
            [{"skill": name, **(info or {})} for name, info in assignment["tags"].items()],
            key=lambda t: t["skill"],
        )
        assignment["organization"] = primary_orgs.get(assignment["id"])

    # The order of the bars on Bezetting, so the panel and the timeline agree.
    assignments = sorted(
        (*active_by_id.values(), *historical_by_id.values()),
        key=lambda a: placement_order_key(a["phase"], a["start_date"]),
    )

    # ?uitgeklapt= (the way in from a team row) opens that opdracht's Taken, so
    # the role you came from is in view at once. A single opdracht is always
    # open: collapsed, it reads as if the list itself were cut off.
    opened = request.GET.get("uitgeklapt", "")
    for entry in assignments:
        _add_cv_rows(entry, open_requested=len(assignments) == 1 or str(entry["public_id"]) == opened)
    return assignments


# Three clamped lines at roughly 90 characters on a wide panel. Past this the
# toggle is certain, also without JavaScript; below it cv_clamp.js shows the
# toggle when a narrow screen clamps a shorter text.
_CV_PREVIEW_CHARS = 240


_CV_ROLE_NAMES = 3


def _add_cv_rows(entry: dict, *, open_requested: bool) -> None:
    """Adds the Rol and Taken rows of a cv entry.

    A placement tag carries dates; the "Business Manager" tag does not: it is
    an ownership tag that shares the Rol line, and it has no Taken.
    """
    names = [tag["skill"] for tag in entry["tags"]]
    roles = [tag for tag in entry["tags"] if "start" in tag]
    more = len(names) - _CV_ROLE_NAMES
    entry["role_text"] = ", ".join(names[:_CV_ROLE_NAMES]) + (f" +{more} meer" if more > 0 else "")
    entry["role_hours"] = f"{roles[0]['hours']} uur per week" if len(roles) == 1 and roles[0]["hours"] else ""
    entry["taken"] = _cv_taken(roles, open_requested=open_requested) if roles else None


def _cv_taken(roles: list[dict], *, open_requested: bool) -> dict:
    """The Taken row: every role's text run together as the preview, one block
    per role behind "Toon meer", and the viewer's own pencil."""
    described = [role for role in roles if role["description"]]
    preview = " ".join(role["description"] for role in described)
    has_more = len(preview) > _CV_PREVIEW_CHARS
    # The sheet is per role, so with several roles the pencil could not say which.
    own = roles[0] if len(roles) == 1 and roles[0]["edit_url"] else None
    return {
        "preview": preview,
        "has_more": has_more,
        "open": has_more and open_requested,
        "blocks": [
            {"label": role["skill"] if len(roles) > 1 else None, "text": role["description"]} for role in described
        ],
        "edit_url": own["edit_url"] if own else None,
        "edit_label": own["edit_label"] if own else None,
    }


def _build_colleague_panel_data(colleague, request):
    """Builds the colleague panel context, shared by both views."""
    assignments = _get_colleague_assignments(request, colleague)
    return {
        "panel_content_template": "parts/colleague_panel_content.html",
        "panel_title": colleague.name,
        "close_url": _build_close_url(request),
        "colleague": colleague,
        "labels": list(colleague.labels.filter(category__in=label_categories_for_everyone())),
        "assignments": assignments,
    }


def _resolve_aanvraag_panel(request, public_id):
    """Resolves ``?aanvraag=`` to an open role, through the viewer's own rows.

    Only a vacancy has this panel: a filled row's hours and role text follow
    the team-row rules this read view does not apply, so resolving one here
    would hand out what the team list withholds (#693). Same gate as
    ``visible_service_or_404`` uses for mutations (#655). Not-found, hidden and
    filled are indistinguishable.
    """
    # Deferred: wies.core.editables imports from views at module level.
    from wies.core.editables.assignment import visible_service_rows  # noqa: PLC0415

    service = _resolve_panel_object(request, Service, public_id, select_related=("assignment", "skill"))
    if service is not None:
        row = next(
            (r for r in visible_service_rows(service.assignment, request) if r["service_public_id"] == str(public_id)),
            None,
        )
        if row is not None and row["placement"] is None:
            return service
    if _is_side_panel_request(request):
        raise Http404 from None
    return None


def _build_aanvraag_panel_data(service, request):
    """Builds the aanvraag panel: the read view of one open role on an opdracht.

    A team row for a placement opens that colleague's panel; an aanvraag has no
    colleague, so it opens this one. Reached only through
    ``_resolve_aanvraag_panel``, which keeps this to real vacancies.
    """
    # Deferred like the other panel builders: wies.core.editables imports from
    # views at module level, so a top-level import here is circular.
    from wies.core.editables.assignment import AssignmentEditables, visible_service_rows  # noqa: PLC0415

    assignment = service.assignment
    role = aanvraag_role(service)
    return {
        "team_text": team_names_text(visible_service_rows(assignment, request)),
        "panel_content_template": "parts/aanvraag_panel_content.html",
        "panel_title": f"Aanvraag: {role}" if role else "Aanvraag",
        "heading": role or "Rol niet ingevuld",
        "close_url": _build_close_url(request),
        "service": service,
        "assignment": assignment,
        "assignment_url": _build_panel_url(request, opdracht=assignment.public_id),
        "period_text": request_period_text(service) or "Geen periode opgegeven",
        "user_can_edit_team": has_permission(Verb.UPDATE, assignment, request.user, AssignmentEditables.services),
        "external_source": external_source(assignment),
        # Keeps ?aanvraag=, so saving or going back lands on this panel again.
        "edit_url": _build_panel_url(
            request, opdracht=assignment.public_id, aanvraag=service.public_id, teamlid=service.public_id
        ),
    }


def _assignment_create_button(request):
    """The "Opdracht invoeren" action, or None without the permission.

    Same button and same ``?nieuwe-opdracht`` panel as the Aanvragen list, so
    entering an assignment works identically wherever a business manager is.
    """
    if not request.user.has_perm("core.add_assignment"):
        return None
    return {
        "button_text": "Opdracht invoeren",
        "attrs": {
            "hx-get": _build_panel_url(request, **{"nieuwe-opdracht": ""}),
            "hx-target": "#side-panel-content",
            "hx-swap": "innerHTML",
            "hx-push-url": "true",
        },
    }


def _assignment_create_panel(request):
    """panel_data for the empty create form, or None when it does not apply.

    Without the permission it falls away silently: these are list pages, not a
    403.
    """
    if request.GET.get("nieuwe-opdracht") is None or not request.user.has_perm("core.add_assignment"):
        return None
    from wies.core.services.assignments import (  # noqa: PLC0415 (import not at top level) — avoids import cycle
        assignment_create_specs,
    )

    form_cls, initial = build_combined_form_class(assignment_create_specs())
    # Prefill: the creator is usually the BM themselves.
    if getattr(request.user, "colleague", None):
        initial["owner"] = request.user.colleague
    return _build_assignment_create_panel_data(request, form_cls(initial=initial))


def _build_placement_edit_panel_data(placement, request, *, only=None, form=None, parent_url=None):
    """Context for the placement edit child sheet, or None without edit rights.

    The single source for this sheet: the open-GET path merges the returned dict
    onto the opdracht panel, and the invalid-POST path renders it directly. Pass
    the bound ``form`` (and the sanitised ``parent_url``) to re-render a submitted
    form with its errors instead of a fresh one. ``only`` narrows the form to one
    row of the panel (``?veld=`` on a POST).
    """
    only = only or request.GET.get("veld") or None
    if parent_url is None:
        parent_url = _url_drop_params(request.path, request.GET, ("bewerken", "veld", "teamlid"))
    specs = placement_edit_specs(placement, request.user, only=only)
    if not specs:
        return None
    if form is None:
        form_cls, initial = build_combined_form_class(specs)
        form = form_cls(initial=initial)
    # only="skill" reaches here from the own-role sheet alone, whose viewer
    # lacks the UPDATE the skill field needs: it is always the taken sheet.
    heading = "Taken wijzigen" if only == "skill" else "Teamlid wijzigen"
    return {
        "panel_content_template": "parts/placement_edit_panel_content.html",
        "colleague": placement.colleague,
        "service": placement.service,
        "form": form,
        "edit_heading": heading,
        # The sheet is a child of the opdracht panel; the back button names it.
        "back_text": placement.service.assignment.name,
        "parent_url": parent_url,
        "edit_url": reverse("placement-edit", args=[placement.public_id]) + (f"?veld={only}" if only else ""),
    }


def _build_assignment_edit_panel_data(assignment, request, *, form=None, parent_url=None):
    """Context for the assignment edit child sheet, or None without edit rights.

    The team is a formset and does not fit this flat form, so it keeps a child
    sheet of its own.

    The single source for this sheet (see ``_build_placement_edit_panel_data``):
    pass the bound ``form`` + sanitised ``parent_url`` to re-render an invalid
    submission instead of a fresh form.
    """
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle

    only = request.GET.get("veld") or None
    specs = assignment_edit_specs(assignment, request.user, only=only)
    if not specs:
        return None
    if form is None:
        form_cls, initial = build_combined_form_class(specs)
        form = form_cls(initial=initial)
    return {
        "panel_content_template": "parts/assignment_edit_panel_content.html",
        "assignment": assignment,
        "form": form,
        # Single-field sheet: the title names that field ("Business Manager wijzigen").
        "edit_heading": f"{_spec_label(AssignmentEditables, specs[0][1])} wijzigen" if only else "Opdracht wijzigen",
        "parent_url": parent_url
        if parent_url is not None
        else _url_drop_params(request.path, request.GET, ("bewerken", "veld")),
        "edit_url": reverse("assignment-edit", args=[assignment.public_id]) + (f"?veld={only}" if only else ""),
    }


def _build_assignment_member_panel_data(assignment, request, *, member_form=None, member_heading=None, parent_url=None):
    """Context for the team member child sheet, or None without rights.

    The single source for this sheet. On open (GET), ``?teamlid=<service public_id>``
    edits an existing member and ``nieuw-aanvraag``/``nieuw-ingevuld`` add a row
    with the status preselected — the form and heading are derived here. On an
    invalid POST, pass the bound ``member_form`` + its ``member_heading`` +
    sanitised ``parent_url`` to re-render; the ``teamlid`` lookup is then skipped.
    """
    from wies.core.editables.assignment import AssignmentEditables, skill_choices, visible_service_rows  # noqa: PLC0415
    from wies.core.forms import ServiceForm  # noqa: PLC0415 — avoids circular import

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return None

    if member_form is None:
        teamlid = request.GET.get("teamlid", "")
        if teamlid in ("nieuw-aanvraag", "nieuw-ingevuld"):
            filled = teamlid == "nieuw-ingevuld"
            initial_row = {
                "is_filled": "ingevuld" if filled else "aanvraag",
                "has_custom_period": True,
                "hours_per_week": DEFAULT_HOURS_PER_WEEK,
            }
            member_heading = "Geplaatste consultant toevoegen" if filled else "Aanvraag toevoegen"
        else:
            # teamlid is a Service public_id (UUID string); match it against the row
            # identity. A non-matching or malformed value just misses → 404 panel.
            # Resolved against the viewer-filtered rows to enforce proper visibility rules
            initial_row = next(
                (r for r in visible_service_rows(assignment, request) if r["service_public_id"] == teamlid), None
            )
            if initial_row is None:
                return None
            member_heading = "Teamlid wijzigen"
        member_form = ServiceForm(initial=initial_row, skill_choices=skill_choices())

    if parent_url is None:
        # Opened from the aanvraag panel, back is that panel alone; the sheet
        # itself needed ?opdracht=.
        dropped = ("teamlid", "opdracht") if request.GET.get("aanvraag") else ("teamlid",)
        parent_url = _url_drop_params(request.path, request.GET, dropped)
    from_aanvraag = QueryDict(urllib.parse.urlparse(parent_url).query).get("aanvraag")
    return {
        "panel_content_template": "parts/assignment_member_edit_panel_content.html",
        "assignment": assignment,
        "member_form": member_form,
        "member_heading": member_heading,
        "parent_url": parent_url,
        # Opened from the aanvraag panel, the sheet returns there, so the back
        # button names it.
        "back_text": "Aanvraag" if from_aanvraag else assignment.name,
        "member_edit_url": reverse("assignment-member-edit", args=[assignment.public_id]),
    }
