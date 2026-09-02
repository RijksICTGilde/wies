import hashlib
import json
import logging
import urllib.parse
from collections import Counter
from contextlib import nullcontext
from datetime import date, timedelta
from functools import cached_property

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required, login_required, permission_required, user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core import management
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, Exists, F, Model, OuterRef, Prefetch, Q, Subquery, Value, When
from django.db.models.functions import Concat, Lower
from django.forms.utils import ErrorDict
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views.decorators.http import require_POST
from django.views.generic.list import ListView

from wies.core.editables import REGISTRY
from wies.core.inline_edit.base import (
    Editable,
    EditableCollection,
    EditableGroup,
    EditableSet,
)
from wies.core.inline_edit.forms import (
    _current_value,
    build_combined_form_class,
    build_form_class,
    resolve_editables,
)
from wies.core.permission_engine import Verb, has_permission
from wies.core.placement_visibility import LABELS, PRIVACY_TEAM, evaluate_placement_visibility
from wies.core.public_id import FacetResolver, ResolvedFacet, parse_public_ids, resolve_facet
from wies.rijksauth.services.usage import get_usage_stats

from .forms import (
    LabelCategoryFormSet,
    LabelForm,
    ProfileLabelsForm,
    ProfileNameForm,
    SuborganizationForm,
    UserForm,
)
from .models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    ErrorEvent,
    Event,
    Label,
    LabelCategory,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    Suborganization,
)
from .permissions import can_access_business_management, is_staff_member
from .querysets import (
    annotate_placement_dates,
    annotate_suborganization_usage_counts,
    annotate_usage_counts,
)
from .services.assignments import (
    assignment_edit_specs,
    member_audit_event,
    save_service_from_form,
)
from .services.events import create_event
from .services.inline_edit_save import save_edit_specs
from .services.occupancy import (
    CONSULTANT_GROUP as BEZETTING_CONSULTANT_GROUP,
)
from .services.occupancy import (
    HORIZON_AHEAD_DAYS,
    HORIZON_BACK_DAYS,
    STATUS_VALUES,
    colleague_occupancy,
    row_has_status,
)
from .services.organizations import (
    find_orgs_by_abbreviation,
    get_excluded_org_ids,
    get_org_breadcrumb,
    get_org_descendant_ids,
)
from .services.placements import (
    create_assignments_from_csv,
    filter_visible_placements,
    placement_edit_specs,
    save_placement_edit,
)
from .services.tasks import create_task, get_latest_tasks, has_active_task
from .services.users import create_user, create_users_from_csv, is_allowed_email_domain, update_user

logger = logging.getLogger(__name__)

User = get_user_model()

# Singular → plural display names for organization type group headers.
ORG_TYPE_PLURAL: dict[str, str] = {
    "Adviescollege": "Adviescolleges",
    "Agentschap": "Agentschappen",
    "Caribisch openbaar lichaam": "Caribische openbare lichamen",
    "Externe commissie": "Externe commissies",
    "Gemeente": "Gemeenten",
    "Grensoverschrijdend regionaal samenwerkingsorgaan": "Grensoverschrijdende regionale samenwerkingsorganen",
    "Hoog College van Staat": "Hoge Colleges van Staat",
    "Inspectie": "Inspecties",
    "Interdepartementale commissie": "Interdepartementale commissies",
    "Koepelorganisatie": "Koepelorganisaties",
    "Ministerie": "Ministeries",
    "Openbaar lichaam voor beroep en bedrijf": "Openbare lichamen voor beroep en bedrijf",
    "Organisatie met overheidsbemoeienis": "Organisaties met overheidsbemoeienis",
    "Organisatieonderdeel": "Organisatieonderdelen",
    "Overheidsstichting of -vereniging": "Overheidsstichtingen of -verenigingen",
    "Provinciale Rekenkamer": "Provinciale Rekenkamers",
    "Provincie": "Provincies",
    "Regionaal samenwerkingsorgaan": "Regionale samenwerkingsorganen",
    "Waterschap": "Waterschappen",
    "Zelfstandig bestuursorgaan": "Zelfstandige bestuursorganen",
}


# Query params that drive the side panel; stripped when (re)building a page URL.
# ``bewerken`` puts the panel in edit mode (the child sheet).
PANEL_PARAMS = ("pagina", "collega", "opdracht", "plaatsing", "bewerken", "teamlid", "veld", "nieuwe-opdracht")


def _url_drop_params(path, query, names, **overrides):
    """Rebuild ``path`` from ``query`` (a QueryDict) with ``names`` dropped and
    ``overrides`` applied. Returns ``path`` alone when no params remain."""
    params = query.copy()
    for name in names:
        params.pop(name, None)
    for key, value in overrides.items():
        params[key] = value
    encoded = params.urlencode()
    return f"{path}?{encoded}" if encoded else path


def _build_panel_url(request, **overrides):
    """Build a URL on the current path, preserving filters but replacing panel params."""
    return _url_drop_params(request.path, request.GET, PANEL_PARAMS, **overrides)


def _build_close_url(request):
    """Build close URL preserving current filters."""
    return _url_drop_params(request.path, request.GET, PANEL_PARAMS)


def _is_side_panel_request(request):
    """True for the HTMX requests that render a panel partial.

    Lets a view 404 an unresolved panel target instead of rendering a template
    with no ``panel_data``; a full-page load stays graceful and shows no panel.
    """
    return request.headers.get("HX-Target") in ("side-panel-content", "side-panel-container")


def _resolve_panel_object(request, model, public_id, *, select_related=()):
    """Looks up a side-panel object (Assignment, Colleague, ...) by its public_id.

    A miss (including a malformed public_id) raises Http404 only for the HTMX
    panel request; a full-page load gets None and renders without a panel. Only
    for models whose panel has no per-object visibility rule — Placement has one
    and keeps ``_resolve_placement_panel``.
    """
    qs = model.objects.select_related(*select_related) if select_related else model.objects.all()
    try:
        return qs.get(public_id=public_id)
    except model.DoesNotExist, ValidationError, ValueError:
        if _is_side_panel_request(request):
            raise Http404 from None
        return None


def _build_assignment_panel_data(assignment, request):
    """Builds the assignment panel context, shared by both views."""
    from wies.core.editables.assignment import (  # noqa: PLC0415
        AssignmentEditables,
        _organizations_initial,
        _owner_display_context,
        visible_service_rows,
    )

    team_rows = visible_service_rows(assignment, request)
    data = {
        "panel_content_template": "parts/assignment_panel_content.html",
        "panel_title": assignment.name,
        "close_url": _build_close_url(request),
        "assignment": assignment,
        "team_rows": team_rows,
        # Same human label as the "Externe bron" row, so the intro says "OTYS
        # IIR", not the raw key "OTYS_IIR".
        "team_external_source": assignment.get_source_display() if assignment.source not in ("wies", "") else "",
        # One privacy note above the list instead of one per row. The wording
        # comes from placement_visibility, already tailored to the viewer.
        "team_privacy_note": next(
            (note for row in team_rows if (note := row.get("privacy_warning_text"))),
            "",
        ),
        "user_can_edit": bool(assignment_edit_specs(assignment, request.user)),
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
        member_panel = _build_assignment_member_panel_data(assignment, request)
        if member_panel is not None:
            data.update(member_panel)
    return data


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
    name, aid, request, public_id=None, start_date=None, end_date=None, placement_id=None, **extra
):
    """Build a standard assignment dict for panel display."""
    url = (
        _build_panel_url(request, plaatsing=placement_id)
        if placement_id
        else _build_panel_url(request, opdracht=public_id)
    )
    return {
        "name": name,
        "id": aid,
        "tags": {},
        "assignment_url": url,
        "start_date": start_date,
        "end_date": end_date,
        "historical": False,
        "privacy_warning_text": None,
        **extra,
    }


def _get_colleague_assignments(request, colleague, viewer):

    today = timezone.now().date()
    viewer_is_colleague = viewer and colleague.id == viewer.id

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
            "service__assignment__name",
            "service__assignment__start_date",
            "service__assignment__end_date",
            "service__assignment__owner_id",
            "service__skill__name",
            "service__description",
        )
        .distinct()
    )
    placement_qs = annotate_placement_dates(placement_qs)
    for placement in placement_qs:
        assignment_id = placement["service__assignment__id"]
        owner_id = placement["service__assignment__owner_id"]
        start = placement.get("actual_start_date")
        end = placement.get("actual_end_date")
        # Active placements are public; ended or not-yet-started ones are only
        # visible to the placed colleague and the assignment's BM-owner.
        result = evaluate_placement_visibility(start, end, colleague.id, viewer, owner_id, today)
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
                placement_id=placement["public_id"],
            )
        else:
            _merge_date_range(bucket[assignment_id], start, end)
        skill_name = placement["service__skill__name"]
        if skill_name:
            bucket[assignment_id]["tags"][skill_name] = placement["service__description"]

    # BM roles (active and ended)
    bm_assignments = Assignment.objects.filter(owner=colleague).values_list(
        "id", "public_id", "name", "start_date", "end_date"
    )
    for assignment_id, public_id, name, start_date, end_date in bm_assignments:
        assignment_is_active = end_date is None or today <= end_date

        if assignment_is_active:
            if assignment_id not in active_by_id:
                active_by_id[assignment_id] = _make_assignment_entry(
                    name,
                    assignment_id,
                    request,
                    public_id=public_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            active_by_id[assignment_id]["tags"]["Business Manager"] = None
        elif viewer_is_colleague:
            # Only the colleague sees their own ended BM assignments; an
            # assignment has exactly one business manager.
            if assignment_id not in historical_by_id:
                historical_by_id[assignment_id] = _make_assignment_entry(
                    name,
                    assignment_id,
                    request,
                    public_id=public_id,
                    start_date=start_date,
                    end_date=end_date,
                    tags={"Business Manager": None},
                    historical=True,
                    privacy_warning_text=PRIVACY_TEAM,
                )
            historical_by_id[assignment_id]["tags"]["Business Manager"] = None
        else:
            continue

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
            [{"skill": name, "description": desc} for name, desc in assignment["tags"].items()],
            key=lambda t: t["skill"],
        )
        assignment["organization"] = primary_orgs.get(assignment["id"])

    # Build final sorted list: active first, then historical; within each block by start_date desc
    active_list = sorted(active_by_id.values(), key=lambda a: a["start_date"] or date.min, reverse=True)
    historical_list = sorted(historical_by_id.values(), key=lambda a: a["start_date"] or date.min, reverse=True)
    return active_list + historical_list


def _build_colleague_panel_data(colleague, request):
    """Builds the colleague panel context, shared by both views."""
    viewer = getattr(request.user, "colleague", None)

    assignments = _get_colleague_assignments(request, colleague, viewer)

    return {
        "panel_content_template": "parts/colleague_panel_content.html",
        "panel_title": colleague.name,
        "close_url": _build_close_url(request),
        "colleague": colleague,
        "assignments": assignments,
    }


def _build_placement_panel_data(placement, request, *, visibility=None):
    """Builds the panel context for a single placement.

    ``visibility`` (a PlacementVisibility) flags a non-active placement so the
    card shows the timing chip and privacy note. Access control is the caller's
    job — see ``_resolve_placement_panel``.
    """
    assignment = placement.service.assignment
    colleague = placement.colleague
    service = placement.service
    today = timezone.now().date()

    # Build assignment card in the same format as colleague_assignment_cards.html expects
    primary_org = (
        AssignmentOrganizationUnit.objects.filter(assignment=assignment, role="PRIMARY")
        .values_list("organization__name", flat=True)
        .first()
    )

    # Only currently-active colleagues, so the avatar list can't leak ended or
    # not-yet-started placements of others.
    team_members = list(
        annotate_placement_dates(Placement.objects.filter(service__assignment=assignment))
        .filter(Q(actual_start_date__isnull=True) | Q(actual_start_date__lte=today))
        .filter(Q(actual_end_date__isnull=True) | Q(actual_end_date__gte=today))
        .select_related("colleague")
        .values_list("colleague__name", flat=True)
        .distinct()
    )

    assignment_card = {
        "name": assignment.name,
        "id": assignment.id,
        "assignment_url": _build_panel_url(request, opdracht=assignment.public_id),
        "start_date": None,
        "end_date": None,
        "organization": primary_org,
        "tags": [],
        "historical": visibility is not None and visibility.timing != "active",
        "privacy_warning_text": visibility.privacy_note if visibility else None,
        "period_label": LABELS.get(visibility.timing) if visibility else None,
        "team_members": team_members,
        "show_read_more": True,
    }

    # The colleague's other assignments live in this same panel, under the same
    # visibility rules as the colleague panel — it is the same source.
    viewer = getattr(request.user, "colleague", None)
    other_assignments = [
        entry for entry in _get_colleague_assignments(request, colleague, viewer) if entry["id"] != assignment.id
    ]

    return {
        "panel_content_template": "parts/placement_panel_content.html",
        "panel_title": f"{colleague.name} - {assignment.name}",
        "close_url": _build_close_url(request),
        "placement": placement,
        "colleague": colleague,
        "service": service,
        "assignment_card": assignment_card,
        "other_active_assignments": [a for a in other_assignments if not a["historical"]],
        "past_assignments": [a for a in other_assignments if a["historical"]],
        "can_edit_period": bool(placement_edit_specs(placement, request.user, only="period")),
        "can_edit_role": bool(placement_edit_specs(placement, request.user, only="skill")),
        "edit_panel_url": _build_panel_url(request, plaatsing=placement.public_id, bewerken=1),
    }


def _resolve_placement_panel(request, public_id):
    """Fetches a placement for the side panel, enforcing the team list's rule.

    Ended or not-yet-started placements are only shown to the placed colleague
    and the assignment's BM-owner. Not-found, malformed and not-visible are
    indistinguishable — all raise Http404 for the HTMX panel request, so a hidden
    placement's existence is never revealed, and return None for a full-page load.
    """
    try:
        placement = Placement.objects.select_related("colleague", "service__assignment", "service__skill").get(
            public_id=public_id
        )
    except Placement.DoesNotExist, ValidationError, ValueError:
        # A malformed or unknown ?plaatsing= is treated as "not found" (see the
        # anti-oracle below) rather than escaping as a 500.
        placement = None
    result = None
    if placement is not None:
        assignment = placement.service.assignment
        viewer = getattr(request.user, "colleague", None)
        result = evaluate_placement_visibility(
            placement.start_date,
            placement.end_date,
            placement.colleague_id,
            viewer,
            assignment.owner_id,
            timezone.now().date(),
        )
    if result is None or not result.visible:
        if _is_side_panel_request(request):
            raise Http404 from None
        return None
    panel_data = _build_placement_panel_data(placement, request, visibility=result)
    if request.GET.get("bewerken"):
        edit_panel = _build_placement_edit_panel_data(placement, request)
        # Without edit rights, ?bewerken= falls back to the read-only panel
        # instead of an empty or forbidden sheet.
        if edit_panel is not None:
            panel_data.update(edit_panel)
    return panel_data


@login_not_required  # page cannot require login because you land on this after unsuccesful login
def no_access(request):
    email = request.session.pop("failed_login_email", None)
    is_allowed_domain = email and is_allowed_email_domain(email)
    return render(request, "no_access.html", {"email": email, "is_allowed_domain": is_allowed_domain})


def staff_required(view_func):
    return user_passes_test(is_staff_member, login_url="/geen-toegang/")(view_func)


def business_management_access_required(view_func):
    """Gate the "Business management" section: Business Development Managers plus
    support staff (see ``can_access_business_management``)."""
    return user_passes_test(can_access_business_management, login_url="/geen-toegang/")(view_func)


def _bezetting_today_pct():
    """Horizontal position of the 'today' marker within the timeline horizon."""
    return round(HORIZON_BACK_DAYS / (HORIZON_BACK_DAYS + HORIZON_AHEAD_DAYS) * 100, 2)


def _bezetting_month_ticks(today):
    """First-of-month gridline labels across the horizon, as {label, month, left%}."""
    horizon_start = today - timedelta(days=HORIZON_BACK_DAYS)
    horizon_end = today + timedelta(days=HORIZON_AHEAD_DAYS)
    span = (horizon_end - horizon_start).days or 1
    ticks = []
    year, month = horizon_start.year, horizon_start.month
    # Advance to the first month boundary on or after the horizon start.
    if horizon_start.day != 1:
        month += 1
        if month > 12:  # noqa: PLR2004 (12 = months per year)
            month = 1
            year += 1
    cursor = date(year, month, 1)
    while cursor <= horizon_end:
        left = (cursor - horizon_start).days / span * 100
        ticks.append({"label": cursor.strftime("%b"), "month": cursor.month, "left": round(left, 2)})
        month += 1
        if month > 12:  # noqa: PLR2004 (12 = months per year)
            month = 1
            year += 1
        cursor = date(year, month, 1)
    return ticks


@business_management_access_required
def bezetting(request):
    """ "Bezetting" — the business-manager occupancy timeline.

    Rows are colleagues, sorted most-pressing first (bench → full). A row click
    opens the shared colleague side panel via the ``collega`` param, exactly like
    the "Wie zit waar?" table.
    """
    today = timezone.now().date()

    # Side panel: reuse the shared machinery. A row click opens the colleague
    # panel (?collega); links inside that panel open an opdracht (?opdracht) or
    # plaatsing (?plaatsing) panel, exactly like on "Wie zit waar?".
    placement_id = request.GET.get("plaatsing")
    assignment_id = request.GET.get("opdracht")
    colleague_id = request.GET.get("collega")
    panel_data = None
    if placement_id:
        panel_data = _resolve_placement_panel(request, placement_id)
    elif assignment_id:
        assignment = _resolve_panel_object(request, Assignment, assignment_id)
        if assignment is not None:
            panel_data = _build_assignment_panel_data(assignment, request)
    elif colleague_id:
        colleague = _resolve_panel_object(request, Colleague, colleague_id)
        if colleague is not None:
            panel_data = _build_colleague_panel_data(colleague, request)

    # HTMX panel requests return just the panel content, like WZW.
    if "HX-Request" in request.headers:
        hx_target = request.headers.get("HX-Target")
        if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container") and panel_data:
            return render(request, panel_data["panel_content_template"], {"panel_data": panel_data})

    # Merk (suborganisation) and label-category filters, resolved from the URL.
    # Labels are OR within a category and AND between categories (like "Wie zit
    # waar?"); each label category becomes its own filter group under the shared
    # ``labels`` param, and merk is its own group.
    merk = resolve_facet(Suborganization, request.GET.getlist("merk"))
    labels = resolve_facet(Label, request.GET.getlist("labels"))
    labels_by_category = _labels_by_category(labels)

    rows = colleague_occupancy(today, merk_ids=merk.ids, labels_by_category=labels_by_category)
    for row in rows:
        row.colleague.panel_url = _build_panel_url(request, collega=row.colleague.public_id)

    # Summary-card counts are the full population within the merk/label selection —
    # they stay a stable dashboard regardless of which cards are toggled, so they
    # are computed before the status filter narrows the rows.
    bench_count = sum(1 for r in rows if r.bucket == "bench")
    full_count = sum(1 for r in rows if r.bucket == "full")
    ends_soon_count = sum(1 for r in rows if r.ends_soon)

    # Status facet: the three summary cards, as independent OR-toggles. Derived
    # from the built rows (not a queryset column), so it filters here in-memory.
    selected_statuses = [s for s in request.GET.getlist("status") if s in STATUS_VALUES]
    if selected_statuses:
        rows = [r for r in rows if any(row_has_status(r, s) for s in selected_statuses)]

    # Filter sheet: one select-multi group per facet, with cross-filtered counts,
    # driving the shared filter panel (parts/filter_sidebar.html). No "Rol" group —
    # everyone on this page is a consultant.
    filter_groups = _bezetting_filter_groups(merk, labels, labels_by_category)
    _finalize_filter_groups(filter_groups)

    active_filters = {}
    if merk.active_values:
        active_filters["merk"] = merk.active_values
    if labels.active_values:
        active_filters["labels"] = labels.active_values
    if selected_statuses:
        active_filters["status"] = selected_statuses

    # Bench colleagues get their own section above the placed ones, but keep a
    # timeline row: they have nothing running today, yet they can have work
    # already booked for next month, and "is anything lined up for this person"
    # is the reason to look at the bench at all. The row is compact (no lane
    # stack to make room for) and shows how long they have been free as a bar.
    #
    # Longest-free first, which is the order a business manager reads this in.
    # Sorted here rather than in the template: Jinja's sort filter cannot order a
    # list where some bench_days are None (never placed), and comparing None to an
    # int raises. Those go last — "never placed" is not a long wait, it is a
    # different thing.
    bench_rows = sorted(
        (r for r in rows if r.bucket == "bench"),
        key=lambda r: (r.bench_days is None, -(r.bench_days or 0)),
    )
    timeline_rows = [r for r in rows if r.bucket != "bench"]

    context = {
        "rows": timeline_rows,
        "bench_rows": bench_rows,
        "panel_data": panel_data,
        "today_pct": _bezetting_today_pct(),
        "today": today,
        "month_ticks": _bezetting_month_ticks(today),
        "bench_count": bench_count,
        "full_count": full_count,
        "ends_soon_count": ends_soon_count,
        "selected_statuses": selected_statuses,
        "filter_groups": filter_groups,
        "active_filters": active_filters,
        "filter_target_url": reverse("bezetting"),
        "filter_modal_group_id": request.GET.get("filter_modal", ""),
        "filter_active": bool(merk.active_values or labels.active_values or selected_statuses),
        # What the "Alle filters" button counts: the facets that live inside the
        # sheet, not the status cards. A status shows it is on by the card being
        # pressed, so counting it here made the button claim a filter the user
        # could already see was applied — and read as "(1)" over an untouched
        # sheet. Values, not groups: two labels from one group are two filters
        # to the reader.
        "active_filter_values": len(merk.active_values) + len(labels.active_values),
    }

    # HTMX filter change: return just the results block; the filter sheet swaps
    # back OOB (see parts/bezetting_results.html). The "Meer…" sheet reuses the
    # shared template, exactly like the user list.
    if "HX-Request" in request.headers:
        if request.GET.get("filter_modal"):
            return render(request, "parts/filter_options_modal.html", context)
        return render(request, "parts/bezetting_results.html", context)

    return render(request, "bezetting.html", context)


def _labels_by_category(labels):
    """Group a resolved ``labels`` facet's ids by their category id."""
    by_category: dict[int, list[int]] = {}
    for label in Label.objects.filter(id__in=labels.ids).values("id", "category_id"):
        by_category.setdefault(label["category_id"], []).append(label["id"])
    return by_category


def _bezetting_consultant_colleagues():
    """Base colleague queryset for the Bezetting page: only consultants, matching
    the occupancy service (colleagues whose linked user is in that group)."""
    return Colleague.objects.filter(user__groups__name=BEZETTING_CONSULTANT_GROUP)


def _bezetting_apply_filters(qs, merk, labels_by_category, *, exclude_filter=None):
    """Apply the merk + label filters to a consultant-colleague queryset.

    ``exclude_filter`` leaves one facet out so a facet's own counts don't collapse
    to its current selection: "merk" for the merk group, or a label ``category_id``
    (int) for that category's group. Labels are OR within a category, AND between.
    """
    for cat_id, cat_label_ids in labels_by_category.items():
        if exclude_filter != cat_id:
            qs = qs.filter(labels__id__in=cat_label_ids)
    if exclude_filter != "merk" and merk.ids:
        qs = qs.filter(suborganization_id__in=merk.ids)
    return qs.distinct()


def _bezetting_filter_groups(merk, labels, labels_by_category):
    """Build the select-multi filter groups for the Bezetting sheet.

    One group per label category (only labels used by a consultant; empty
    categories dropped) plus one merk group. Each option carries a cross-filtered
    count — the number of consultants that would remain if only this value were
    added to the other active filters — like the "Gebruikers" filter sheet.
    """
    base_qs = _bezetting_consultant_colleagues()
    selected_label_ids = set(labels.public_ids)
    selected_merk_ids = set(merk.public_ids)

    groups = []

    # Label categories: one group each, only labels actually used by a consultant.
    used_labels = (
        Label.objects.filter(colleagues__user__groups__name=BEZETTING_CONSULTANT_GROUP)
        .distinct()
        .select_related("category")
        .order_by("category__name", Lower("name"))
    )
    labels_by_cat: dict[int, list] = {}
    category_names: dict[int, str] = {}
    for label in used_labels:
        labels_by_cat.setdefault(label.category_id, []).append(label)
        category_names[label.category_id] = label.category.name

    for cat_id, cat_labels in labels_by_cat.items():
        cat_qs = _bezetting_apply_filters(base_qs, merk, labels_by_category, exclude_filter=cat_id)
        counts = Counter(lid for lid in cat_qs.values_list("labels__id", flat=True) if lid is not None)
        options = [{"value": "", "label": ""}]
        selected_values = []
        for label in cat_labels:
            value = str(label.public_id)
            option = {"value": value, "label": label.name, "count": counts.get(label.id, 0)}
            if value in selected_label_ids:
                option["selected"] = True
                selected_values.append(value)
            options.append(option)
        groups.append(
            {
                "type": "select-multi",
                "name": "labels",
                "label": category_names[cat_id],
                "options": options,
                "selected_values": selected_values,
            }
        )

    # Merk: only suborganisations that have at least one consultant.
    merk_qs = _bezetting_apply_filters(base_qs, merk, labels_by_category, exclude_filter="merk")
    merk_counts = Counter(mid for mid in merk_qs.values_list("suborganization_id", flat=True) if mid is not None)
    merk_options = [{"value": "", "label": ""}]
    merk_selected = []
    used_suborgs = Suborganization.objects.filter(colleagues__user__groups__name=BEZETTING_CONSULTANT_GROUP).distinct()
    for suborganization in used_suborgs:
        value = str(suborganization.public_id)
        option = {"value": value, "label": suborganization.name, "count": merk_counts.get(suborganization.id, 0)}
        if value in selected_merk_ids:
            option["selected"] = True
            merk_selected.append(value)
        merk_options.append(option)
    groups.append(
        {
            "type": "select-multi",
            "name": "merk",
            "label": "Merk",
            "options": merk_options,
            "selected_values": merk_selected,
        }
    )

    return groups


ERRORS_PER_PAGE = 10


@staff_required
def staff_dashboard(request):
    return render(
        request,
        "staff_dashboard.html",
        {"usage": get_usage_stats(), **_error_table_context(page_number=None)},
    )


def _error_table_context(page_number):
    """Context for the paginated error table (shared by the dashboard and the endpoint)."""
    paginator = Paginator(ErrorEvent.objects.select_related("user"), ERRORS_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    def page_url(number):
        return f"{reverse('error-table')}?pagina={number}"

    return {
        "object_list": page_obj.object_list,
        "page_obj": page_obj,
        "previous_page_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        "next_page_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
    }


def _render_error_table(request, page_number):
    """Render the paginated error table fragment for the given page."""
    return render(request, "parts/error_table.html", _error_table_context(page_number))


@staff_required
def error_table(request):
    """Paginated error table fragment, loaded via HTMX by the dashboard."""
    return _render_error_table(request, request.GET.get("pagina"))


@staff_required
def error_detail(request, public_id):

    error = get_object_or_404(ErrorEvent, public_id=public_id)
    return render(request, "error_detail.html", {"error": error})


@staff_required
def delete_error(request, public_id):
    """Confirms (GET → modal) and performs (POST) deletion of a single error."""
    error = get_object_or_404(ErrorEvent, public_id=public_id)
    if request.method == "GET":
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Foutmelding verwijderen?",
                "dialog_supporting": (
                    "Weet je zeker dat je deze foutmelding wilt verwijderen? "
                    "Verwijderen is permanent en niet terug te draaien."
                ),
                "confirm_label": "Verwijder foutmelding",
                "cancel_label": "Behoud foutmelding",
                "form_post_url": reverse("delete-error", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        error.delete()
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("staff-dashboard")
        return response
    return HttpResponse(status=405)


@staff_required
def staff_database(request):
    context = {
        "assignment_count": Assignment.objects.count(),
        "colleague_count": Colleague.objects.count(),
        "organization_count": OrganizationUnit.objects.count(),
        "latest_tasks": get_latest_tasks(limit=3),
        "destructive_actions_enabled": settings.ENABLE_DESTRUCTIVE_STAFF_ACTIONS,
    }
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "clear_data":
            if not settings.ENABLE_DESTRUCTIVE_STAFF_ACTIONS:
                return HttpResponse(status=405)
            # not using flush, since that would clear users
            Assignment.objects.all().delete()
            Colleague.objects.all().delete()
            Skill.objects.all().delete()
            Placement.objects.all().delete()
            Service.objects.all().delete()
            LabelCategory.objects.all().delete()
            Label.objects.all().delete()
            OrganizationUnit.objects.update(parent=None)
            OrganizationUnit.objects.all().delete()
            OrganizationType.objects.all().delete()
        elif action == "load_base_data":
            if not settings.ENABLE_DESTRUCTIVE_STAFF_ACTIONS:
                return HttpResponse(status=405)
            management.call_command("loaddata", "base_dummy_data.json")
            messages.success(request, "Data geladen uit base_dummy_data.json")
        elif action == "reset_onboarding":
            request.user.onboarding_completed_at = None
            request.user.save(update_fields=["onboarding_completed_at"])
            # No message: the wizard reopens right after the redirect, and a
            # notification would fall behind it — the wizard is a modal in the
            # top layer, the notification region is not.
        elif action == "sync_organizations":
            # Check if there's already an active task
            if has_active_task("sync_organizations"):
                messages.error(request, "Er is al een sync_organizations taak actief. Wacht tot deze is afgerond.")
            else:
                # Create a new task
                create_task(
                    command="sync_organizations",
                    created_by=request.user,
                    timeout_minutes=5,
                )
                messages.success(request, "Organisatiesynchronisatie is gestart")

            # If this is an HTMX request, return partial HTML
            if request.headers.get("HX-Request"):
                context["latest_tasks"] = get_latest_tasks(limit=3)
                return render(request, "parts/task_list.html", context)

        elif action == "merge_duplicates_preview":
            from wies.core.services.assignments import find_duplicate_groups  # noqa: PLC0415

            groups = find_duplicate_groups()
            # The sheet opens even without duplicates: the empty case is handled
            # inside it. Rows are flat (one per placement) because a reviewer
            # reads per line, so the overview needs no nested loops.
            context["merge_groups"] = [
                {
                    "name": group[0].name,
                    "owner": str(group[0].owner),
                    "count": len(group),
                    "target_id": group[0].id,
                    "rows": _merge_preview_rows(group),
                }
                for group in groups
            ]
            return render(request, "parts/merge_duplicates_sheet.html", context)

        elif action == "merge_duplicates_apply":
            from wies.core.services.assignments import (  # noqa: PLC0415 — conditional import for rare admin action
                find_duplicate_groups,
                merge_group,
            )

            groups = find_duplicate_groups()
            if not groups:
                messages.info(request, "Geen dubbele opdrachten gevonden.")
            else:
                with transaction.atomic():
                    # Both numbers count assignments, in the same wording as the
                    # sheet that was just confirmed; "in 2 groep(en)" left it
                    # unclear whether groups or assignments were meant.
                    samengevoegd = sum(len(g) for g in groups)
                    overgebleven = len(groups)
                    for group in groups:
                        target = group[0]
                        deleted_ids = [a.id for a in group[1:]]
                        merge_group(group)
                        create_event(
                            object_type="Assignment",
                            action="update",
                            source="user",
                            object_id=target.id,
                            user=request.user,
                            request=request,
                            context={
                                "merge": True,
                                "merged_ids": deleted_ids,
                                "name": target.name,
                            },
                        )
                    messages.success(
                        request,
                        f"{samengevoegd} opdrachten samengevoegd tot {overgebleven} "
                        f"{'opdracht' if overgebleven == 1 else 'opdrachten'}.",
                    )

        return redirect("staff-database")

    return render(request, "staff_database.html", context)


# Shown for a filter value that matches no row (a deleted or edited bookmark).
# The chip has to be there: it explains why the list is empty and lets the user
# click the filter away.
UNKNOWN_FACET_LABELS = {
    "org": "Onbekende opdrachtgever",
    "org_self": "Onbekende opdrachtgever",
    "rol": "Onbekende rol",
    "labels": "Onbekend label",
    "merk": "Onbekend merk",
}


def _org_chip_data(org: ResolvedFacet, org_self: ResolvedFacet, type_labels: list[str]) -> list[dict]:
    """Chips for the opdrachtgever facets, in the order they appear in the URL."""
    labels: dict[str, str] = {}
    if org.ids or org_self.ids:
        labels = {
            str(public_id): label
            for public_id, label in OrganizationUnit.objects.filter(id__in=[*org.ids, *org_self.ids]).values_list(
                "public_id", "label"
            )
        }
    chips: list[dict] = [
        {
            "param_name": "org",
            "param_value": public_id,
            "label": labels.get(public_id, UNKNOWN_FACET_LABELS["org"]),
        }
        for public_id in org.active_values
    ]
    chips.extend(
        {
            "param_name": "org_self",
            "param_value": public_id,
            "label": f"{labels[public_id]} (direct)" if public_id in labels else UNKNOWN_FACET_LABELS["org_self"],
        }
        for public_id in org_self.active_values
    )
    chips.extend(
        {
            "param_name": "org_type",
            "param_value": type_label,
            "label": ORG_TYPE_PLURAL.get(type_label, type_label),
        }
        for type_label in type_labels
    )
    return chips


class PublicIdFacetsMixin:
    """Resolves the public_id filter params of a list view once per request.

    Every facet fails closed: a param that resolves to no row filters everything
    away instead of being dropped, and still counts as an active filter so the
    user gets a chip rather than an unexplained empty list. See ``ResolvedFacet``.
    """

    @cached_property
    def facets(self) -> FacetResolver:
        return FacetResolver(self.request)

    @cached_property
    def org_type_filter(self) -> list[str]:
        return [x for x in self.request.GET.getlist("org_type") if x]

    def apply_org_filter(self, qs, lookup: str):
        """Applies the opdrachtgever facets (``org``/``org_self``/``org_type``).

        ``lookup`` is the queryset path to the organization id, which differs per
        list view. ``org`` matches the whole subtree, ``org_self`` only the org
        itself, ``org_type`` every org of that type plus its subtree.
        """
        org = self.facets("org", OrganizationUnit)
        org_self = self.facets("org_self", OrganizationUnit)
        if not (org.requested or org_self.requested or self.org_type_filter):
            return qs
        matching_ids: set[int] = set(org_self.ids)
        if org.ids:
            matching_ids |= get_org_descendant_ids(org.ids)
        if self.org_type_filter:
            type_root_ids = list(
                OrganizationUnit.objects.filter(organization_types__label__in=self.org_type_filter).values_list(
                    "id", flat=True
                )
            )
            matching_ids |= get_org_descendant_ids(type_root_ids)
        return qs.filter(**{lookup: matching_ids})

    def add_org_filter_context(self, context: dict, active_filters: dict) -> None:
        """Registers the opdrachtgever facets as active filters and builds their chips."""
        org = self.facets("org", OrganizationUnit)
        org_self = self.facets("org_self", OrganizationUnit)
        if org.active_values:
            active_filters["org"] = org.active_values
        if org_self.active_values:
            active_filters["org_self"] = org_self.active_values
        if self.org_type_filter:
            active_filters["org_type"] = self.org_type_filter
        context["org_chip_data"] = _org_chip_data(org, org_self, self.org_type_filter)

    def add_unknown_filter_chips(self, context: dict, facets: dict[str, type[Model]]) -> None:
        """Chips for the values of ``facets`` that match no row.

        Regular chips are rendered by matching an active value against the filter
        group's options, so a value that no longer exists would render nothing at
        all. The org facets build their own chips and are excluded here.
        """
        context["unknown_chip_data"] = [
            {
                "param_name": param,
                "param_value": value,
                "label": UNKNOWN_FACET_LABELS[param],
            }
            for param, model in facets.items()
            for value in self.facets(param, model).unresolved
        ]

    @cached_property
    def labels_by_category(self) -> dict[int, list[int]]:
        """Selected label ids grouped by their category id."""
        labels = self.facets("labels", Label)
        if not labels.ids:
            return {}
        by_category: dict[int, list[int]] = {}
        for label in Label.objects.filter(id__in=labels.ids).values("id", "category_id"):
            by_category.setdefault(label["category_id"], []).append(label["id"])
        return by_category

    @property
    def labels_match_nothing(self) -> bool:
        """A ``?labels=`` was given but none of its values exist."""
        return self.facets("labels", Label).requested and not self.labels_by_category


class PlacementListView(PublicIdFacetsMixin, ListView):
    """Placements as cards, grouped per person or per assignment."""

    model = Placement
    template_name = "placements.html"
    paginate_by = 60
    page_kwarg = "pagina"

    VIEW_DEFAULT = "persoon"
    VIEW_OPTIONS = [
        {"value": "persoon", "label": "Persoon", "icon": "person"},
        {"value": "opdracht", "label": "Opdracht", "icon": "business-suitcase"},
    ]

    # Pagination runs over these groups, not over placements, so a group never
    # straddles a page boundary and shows up half.
    GROUP_FIELD = {
        "persoon": "colleague_id",
        "opdracht": "service__assignment_id",
    }

    # Sorting on colleague name says nothing in the opdracht view, where one card
    # is a whole team.
    SORT_OPTIONS = {
        "persoon": ["name", "-name", "assignment", "-assignment", "end_date", "-end_date"],
        "opdracht": ["assignment", "-assignment", "end_date", "-end_date"],
    }
    SORT_LABELS = {
        "name": "Naam (A-Z)",
        "-name": "Naam (Z-A)",
        "assignment": "Opdracht (A-Z)",
        "-assignment": "Opdracht (Z-A)",
        "-end_date": "Einddatum (nieuwste eerst)",
        "end_date": "Einddatum (oudste eerst)",
    }
    # The default order is the absence of ?order=, so it has no value to label.
    DEFAULT_SORT_LABEL = {
        "persoon": "Startdatum (nieuwste eerst)",
        "opdracht": "Laatst gewijzigd",
    }

    @property
    def active_view(self) -> str:
        """The requested ?weergave=, falling back to the default for unknown values."""
        requested = self.request.GET.get("weergave") or ""
        valid = {option["value"] for option in self.VIEW_OPTIONS}
        return requested if requested in valid else self.VIEW_DEFAULT

    def _get_base_queryset(self):
        """Base queryset with search, ordering, and date filters applied."""
        excluded_org_ids = get_excluded_org_ids()
        qs = (
            Placement.objects.select_related("colleague", "service", "service__skill")
            .prefetch_related(
                "colleague__labels",
                Prefetch(
                    "service__assignment__organization_relations",
                    queryset=AssignmentOrganizationUnit.objects.annotate(
                        role_order=Case(
                            When(role="PRIMARY", then=0),
                            default=1,
                        )
                    )
                    .order_by("role_order")
                    .select_related("organization"),
                    to_attr="sorted_clients",
                ),
            )
            .order_by("-service__assignment__start_date")
        )
        if excluded_org_ids:
            qs = qs.exclude(service__assignment__organizations__id__in=excluded_org_ids)

        search_filter = self.request.GET.get("zoek")
        if search_filter:
            qs = qs.filter(
                Q(colleague__name__icontains=search_filter)
                | Q(service__assignment__name__icontains=search_filter)
                | Q(service__assignment__extra_info__icontains=search_filter)
                | Q(service__assignment__organizations__label__icontains=search_filter)
            )

        order_mapping = {
            "name": "colleague__name",
            "assignment": "service__assignment__name",
            "end_date": "service__assignment__end_date",
        }

        active_view = self.active_view
        sort_field = None
        order_param = self.request.GET.get("order")
        # A shared url can carry an order this view does not have.
        if order_param and order_param in self.SORT_OPTIONS[active_view]:
            descending = order_param.startswith("-")
            order_by = order_mapping.get(order_param.lstrip("-"))
            if order_by:
                sort_field = f"-{order_by}" if descending else order_by
        if sort_field is None:
            if active_view == "opdracht":
                # No modified-at on the model, so the audit log stands in. Nulls last:
                # events age out of retention.
                qs = qs.annotate(
                    last_change=Subquery(
                        Event.objects.filter(object_type="Assignment", object_id=OuterRef("service__assignment_id"))
                        .order_by("-timestamp")
                        .values("timestamp")[:1]
                    )
                )
                sort_field = F("last_change").desc(nulls_last=True)
            else:
                # Nulls last: a placement without a start date says nothing about
                # how recent it is.
                sort_field = F("actual_start_date").desc(nulls_last=True)

        qs = annotate_placement_dates(qs)

        # The group as tiebreaker keeps one person's or opdracht's placements
        # together when the sort itself ties.
        qs = qs.order_by(sort_field, self.GROUP_FIELD[active_view])

        # The list is a current-state overview: only active placements, for every
        # viewer alike. History and planned placements live on the profile and the
        # side panels, not here.
        return filter_visible_placements(qs, timezone.now().date())

    def _get_loopt_af_options(self, base_qs):
        """Builds the 'loopt af' filter options with cumulative counts.

        Counts distinct groups, not placements, so the number matches the cards
        the list will show: two colleagues on one assignment are two cards in the
        person view and one in the assignment view.
        """
        today = timezone.now().date()
        group_field = self.GROUP_FIELD[self.active_view]
        filtered_qs = self._apply_filters(base_qs, exclude_filter="loopt_af").distinct()

        def group_count(qs):
            return qs.values(group_field).distinct().count()

        presets = [
            ("3m", "Binnen 3 maanden", 91),
            ("6m", "Binnen 6 maanden", 182),
        ]
        options = [{"value": "", "label": ""}]
        for value, label, days in presets:
            end_date = today + timedelta(days=days)
            count = group_count(filtered_qs.filter(service__assignment__end_date__lte=end_date))
            options.append({"value": value, "label": label, "count": count})
        # "Longer than 6 months"
        half_year = today + timedelta(days=182)
        count_beyond = group_count(filtered_qs.filter(service__assignment__end_date__gt=half_year))
        options.append({"value": "6m+", "label": "Langer dan 6 maanden", "count": count_beyond})
        return options

    def _apply_filters(self, qs, *, exclude_filter=None):
        """Applies all selection filters, optionally excluding one filter type.

        ``exclude_filter`` is "rol", "org", "merk", "loopt_af", or a category_id
        (int) for labels.
        """
        rol = self.facets("rol", Skill)
        if exclude_filter != "rol" and rol.requested:
            qs = qs.filter(service__skill_id__in=rol.ids)

        if exclude_filter != "org":
            qs = self.apply_org_filter(qs, "service__assignment__organizations__id__in")

        # Label filter: OR within category, AND between categories
        for cat_id, cat_label_ids in self.labels_by_category.items():
            if exclude_filter != cat_id:
                qs = qs.filter(colleague__labels__id__in=cat_label_ids)

        # Merk filter: OR within the merk group (one merk per colleague)
        merk = self.facets("merk", Suborganization)
        if exclude_filter != "merk" and merk.requested:
            qs = qs.filter(colleague__suborganization_id__in=merk.ids)

        # Filter by assignment end date (preset period)
        if exclude_filter != "loopt_af":
            loopt_af_values = set(self.request.GET.getlist("loopt_af"))
            if loopt_af_values:
                today = timezone.now().date()
                preset_days = {"3m": 91, "6m": 182}
                has_beyond = "6m+" in loopt_af_values
                bounded = {v for v in loopt_af_values if v in preset_days}
                half_year = today + timedelta(days=182)
                if bounded and has_beyond:
                    max_days = max(preset_days[v] for v in bounded)
                    end_date = today + timedelta(days=max_days)
                    qs = qs.filter(
                        Q(service__assignment__end_date__lte=end_date) | Q(service__assignment__end_date__gt=half_year)
                    )
                elif bounded:
                    max_days = max(preset_days[v] for v in bounded)
                    end_date = today + timedelta(days=max_days)
                    qs = qs.filter(service__assignment__end_date__lte=end_date)
                elif has_beyond:
                    qs = qs.filter(service__assignment__end_date__gt=half_year)

        return qs

    def get_queryset(self):
        """Applies the filters to the placements queryset."""
        if self.labels_match_nothing:
            return Placement.objects.none()
        return self._apply_filters(self._get_base_queryset()).distinct()

    def paginate_queryset(self, queryset, page_size):
        """Paginate on groups (persons or assignments), not on placements.

        A card shows one person or one assignment with all their placements, so
        paginating on placements would cut a group in half at the page boundary.
        """
        group_field = self.GROUP_FIELD[self.active_view]
        # A DISTINCT on the group field would have to select every sort column too.
        seen: set[int] = set()
        ordered_group_ids = [
            group_id
            for group_id in queryset.values_list(group_field, flat=True)
            if group_id not in seen and not seen.add(group_id)
        ]

        paginator = self.get_paginator(
            ordered_group_ids, page_size, orphans=self.get_paginate_orphans(), allow_empty_first_page=True
        )
        page = paginator.page(self._validated_page_number(paginator))
        page_group_ids = list(page.object_list)
        placements = list(queryset.filter(**{f"{group_field}__in": page_group_ids})) if page_group_ids else []
        return paginator, page, placements, page.has_other_pages()

    def _validated_page_number(self, paginator) -> int:
        """The requested ?pagina=, clamped to an existing page (1 on nonsense input)."""
        raw = self.kwargs.get(self.page_kwarg) or self.request.GET.get(self.page_kwarg) or 1
        try:
            number = int(raw)
        except TypeError, ValueError:
            return 1
        return max(1, min(number, paginator.num_pages))

    def get_template_names(self):
        """Returns the template for this request type."""
        if "HX-Request" in self.request.headers:
            if self.request.GET.get("filter_modal"):
                return ["parts/filter_options_modal.html"]
            hx_target = self.request.headers.get("HX-Target", "")
            if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container"):
                # panel_data picks its own template (e.g. the edit child sheet);
                # get_context_data has already stored it.
                panel_data = getattr(self, "_panel_data", None)
                if panel_data:
                    return [panel_data["panel_content_template"]]
                return ["parts/placement_panel_content.html"]
            if self.request.GET.get("pagina"):
                return ["parts/placement_cards.html"]
            return ["parts/filter_and_table_container.html"]
        return ["placements.html"]

    def _view_url(self, value: str) -> str:
        """URL for a weergave: keeps the filters and search, drops page and order.

        The sort options differ per view, so an ?order= from the other view would
        not resolve here.
        """
        params = self.request.GET.copy()
        params.pop(self.page_kwarg, None)
        params.pop("order", None)
        if value == self.VIEW_DEFAULT:
            params.pop("weergave", None)
        else:
            params["weergave"] = value
        query = params.urlencode()
        return f"{reverse('home')}?{query}" if query else reverse("home")

    def _person_cards(self, placements) -> list[dict]:
        """One card per colleague, with the assignments they are placed on.

        A person on exactly one assignment opens that placement's panel; on more
        than one the card opens the colleague panel instead.
        """
        grouped: dict[int, list] = {}
        for placement in placements:
            grouped.setdefault(placement.colleague_id, []).append(placement)

        cards = []
        for rows in grouped.values():
            assignments = list(dict.fromkeys(row.service.assignment for row in rows))
            roles = list(dict.fromkeys(row.service.skill.name for row in rows if row.service.skill))
            single = assignments[0] if len(assignments) == 1 else None
            cards.append(
                {
                    "name": rows[0].colleague.name,
                    "assignment": single,
                    "assignments": assignments,
                    "roles": roles,
                    "panel_url": _build_panel_url(
                        self.request,
                        **({"plaatsing": rows[0].public_id} if single else {"collega": rows[0].colleague.public_id}),
                    ),
                }
            )
        return cards

    def _assignment_cards(self, placements) -> list[dict]:
        """One card per assignment, showing its FULL team.

        The team is prefetched separately rather than read off the filtered
        placements: a filter on role or label would otherwise silently shrink the
        team shown on the card to the people that matched the filter.

        Sidestepping the selection filters is the point here; sidestepping the
        visibility filter is not. This page is a current-state overview, so the
        team is the team as it stands today — the same rule the list itself
        follows, and without it a card would name people who left months ago or
        have not started yet.
        """
        assignments = list(dict.fromkeys(p.service.assignment for p in placements))
        teams: dict[int, list[dict]] = {a.id: [] for a in assignments}
        seen: set[tuple[int, int]] = set()
        team_rows = (
            filter_visible_placements(
                annotate_placement_dates(Placement.objects.filter(service__assignment_id__in=teams)),
                timezone.now().date(),
            )
            .select_related("colleague", "service__skill")
            .order_by("colleague__name")
        )
        for row in team_rows:
            key = (row.service.assignment_id, row.colleague_id)
            if key not in seen:
                seen.add(key)
                role = row.service.skill.name if row.service.skill else ""
                teams[row.service.assignment_id].append({"name": row.colleague.name, "role": role})

        cards = []
        for assignment in assignments:
            clients = getattr(assignment, "sorted_clients", [])
            cards.append(
                {
                    "name": assignment.name,
                    "assignment": assignment,
                    "client": (clients[0].organization.label or clients[0].organization.name) if clients else "",
                    "extra_clients": max(len(clients) - 1, 0),
                    "panel_url": _build_panel_url(self.request, opdracht=assignment.public_id),
                    "team": teams[assignment.id],
                }
            )
        return cards

    def get_context_data(self, **kwargs):
        """Adds the dynamic filter options."""
        context = super().get_context_data(**kwargs)
        context["render_filter_fields_oob"] = "HX-Request" in self.request.headers

        active_view = self.active_view
        context["active_view"] = active_view
        # The template compares against it rather than hardcoding the name, so
        # changing the default does not silently break the hidden field.
        context["default_view"] = self.VIEW_DEFAULT
        counts = {active_view: context["paginator"].count}
        filtered = self.get_queryset()
        context["view_options"] = [
            {
                **option,
                "url": self._view_url(option["value"]),
                "selected": option["value"] == active_view,
                "count": counts.get(option["value"])
                if option["value"] in counts
                else filtered.values(self.GROUP_FIELD[option["value"]]).distinct().count(),
            }
            for option in self.VIEW_OPTIONS
        ]
        placements = context["object_list"]
        if active_view == "opdracht":
            context["cards"] = self._assignment_cards(placements)
        else:
            context["cards"] = self._person_cards(placements)

        order_param = self.request.GET.get("order")
        active_order = order_param if order_param in self.SORT_OPTIONS[active_view] else ""
        context["active_order"] = active_order
        # Value and label travel together: keeping the labels in the template
        # meant maintaining the same list in two places.
        context["sort_options"] = [
            {"value": value, "label": self.SORT_LABELS[value]} for value in self.SORT_OPTIONS[active_view]
        ]
        context["default_sort_label"] = self.DEFAULT_SORT_LABEL[active_view]
        context["active_sort_label"] = self.SORT_LABELS.get(active_order) or self.DEFAULT_SORT_LABEL[active_view]

        context["filter_target_url"] = reverse("home")
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters: dict = {}

        loopt_af_values = set(self.request.GET.getlist("loopt_af"))
        if loopt_af_values:
            active_filters["loopt_af"] = loopt_af_values

        # Multi-select facets carry public_ids. A value that resolves to nothing
        # still counts, so an empty list always comes with a way to clear it.
        rol_filter = self.facets("rol", Skill).active_values
        if rol_filter:
            active_filters["rol"] = rol_filter

        label_filter = self.facets("labels", Label).active_values
        if label_filter:
            active_filters["labels"] = label_filter

        suborganization_filter = self.facets("merk", Suborganization).active_values
        if suborganization_filter:
            active_filters["merk"] = suborganization_filter

        # Organization filter (multi-select via modal)
        self.add_org_filter_context(context, active_filters)
        self.add_unknown_filter_chips(context, {"rol": Skill, "labels": Label, "merk": Suborganization})

        # For each filter category, count on a queryset excluding that category's filter
        base_qs = self._get_base_queryset()
        group_field = self.GROUP_FIELD[active_view]

        label_filter_groups = []
        for category in LabelCategory.objects.all():
            # Count with all filters EXCEPT this label category
            cat_filtered_qs = self._apply_filters(base_qs, exclude_filter=category.id).distinct()
            cat_label_counts = _facet_counts(cat_filtered_qs, "colleague__labels__id", group_field)

            options = [{"value": "", "label": ""}]
            selected_values = []
            for label in Label.objects.filter(category=category):
                options.append(
                    {
                        "value": str(label.public_id),
                        "label": f"{label.name}",
                        "category_color": category.color,
                        "count": cat_label_counts.get(label.id, 0),
                    }
                )
                if str(label.public_id) in active_filters.get("labels", set()):
                    options[-1]["selected"] = True
                    selected_values.append(str(label.public_id))

            label_filter_groups.append(
                {
                    "type": "select-multi",
                    "name": "labels",
                    "label": category.name,
                    "options": options,
                    "selected_values": selected_values,
                }
            )

        # Merk filter group (one merk per colleague; counts exclude the merk filter)
        suborg_filtered_qs = self._apply_filters(base_qs, exclude_filter="merk").distinct()
        suborg_counts = _facet_counts(suborg_filtered_qs, "colleague__suborganization_id", group_field)

        suborganization_options = [{"value": "", "label": ""}]
        suborganization_selected_values = []
        for suborganization in Suborganization.objects.all():
            suborganization_options.append(
                {
                    "value": str(suborganization.public_id),
                    "label": suborganization.name,
                    "count": suborg_counts.get(suborganization.id, 0),
                }
            )
            if str(suborganization.public_id) in active_filters.get("merk", set()):
                suborganization_options[-1]["selected"] = True
                suborganization_selected_values.append(str(suborganization.public_id))

        suborganization_filter_group = {
            "type": "select-multi",
            "name": "merk",
            "label": "Merk",
            "options": suborganization_options,
            "selected_values": suborganization_selected_values,
        }

        # Skill/role counts: exclude role filter
        skill_filtered_qs = self._apply_filters(base_qs, exclude_filter="rol").distinct()
        skill_counts = _facet_counts(skill_filtered_qs, "service__skill__id", group_field)

        skill_options = [{"value": "", "label": ""}]
        skill_selected_values = []
        for skill in Skill.objects.order_by("name"):
            option = {"value": str(skill.public_id), "label": skill.name, "count": skill_counts.get(skill.id, 0)}
            if str(skill.public_id) in active_filters.get("rol", set()):
                option["selected"] = True
                skill_selected_values.append(str(skill.public_id))
            skill_options.append(option)

        # Org counts exclude the org filter, so the numbers reflect the other
        # active filters.
        org_counts = _org_counts_from_filtered(
            self._apply_filters(base_qs, exclude_filter="org").distinct(),
            Placement,
            "service__assignment__organizations__id",
            group_field=group_field,
        )

        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)
        context["client_modal_count_mode"] = "placements"

        # TODO: this can be become an object to help defining correctly and performing extra preprocessing on context
        # introduce value_key, label_key:
        context["filter_groups"] = [
            {
                "type": "modal",
                "name": "organisatie",
                "label": "Opdrachtgever",
                "top_options": _get_top_org_options(
                    set(self.facets("org", OrganizationUnit).ids),
                    org_counts,
                    selected_self_ids=set(self.facets("org_self", OrganizationUnit).ids),
                    selected_type_labels=set(self.org_type_filter),
                ),
            },
            {
                "type": "select-multi",
                "name": "rol",
                "label": "Rol",
                "options": skill_options,
                "selected_values": skill_selected_values,
            },
            suborganization_filter_group,
            *label_filter_groups,
            {
                "type": "select-multi",
                "name": "loopt_af",
                "label": "Loopt af",
                "options": self._get_loopt_af_options(base_qs),
                "selected_values": list(loopt_af_values),
            },
        ]
        _finalize_filter_groups(context["filter_groups"])
        context["filter_modal_group_id"] = self.request.GET.get("filter_modal", "")

        # Build next page URL with all current filters
        if context.get("page_obj") and context["page_obj"].has_next():
            params = self.request.GET.copy()
            params["pagina"] = context["page_obj"].next_page_number()
            context["next_page_url"] = f"?{params.urlencode()}"
        else:
            context["next_page_url"] = None

        placement_id = self.request.GET.get("plaatsing")
        colleague_id = self.request.GET.get("collega")
        assignment_id = self.request.GET.get("opdracht")

        if placement_id:
            panel_data = _resolve_placement_panel(self.request, placement_id)
            if panel_data is not None:
                context["panel_data"] = panel_data
        elif colleague_id and not assignment_id:
            colleague = _resolve_panel_object(self.request, Colleague, colleague_id)
            if colleague is not None:
                context["panel_data"] = _build_colleague_panel_data(colleague, self.request)
        elif assignment_id:
            assignment = _resolve_panel_object(self.request, Assignment, assignment_id)
            if assignment is not None:
                context["panel_data"] = _build_assignment_panel_data(assignment, self.request)
        # get_context_data runs before get_template_names, which reads the panel
        # template from here instead of deriving it again.
        self._panel_data = context.get("panel_data")
        return context


class AssignmentListView(PublicIdFacetsMixin, ListView):
    """Vacancy assignments as cards, with infinite scroll pagination."""

    model = Assignment
    template_name = "assignments.html"
    paginate_by = 60
    page_kwarg = "pagina"

    def _get_base_queryset(self):
        has_unfilled_open_service = Exists(
            Service.objects.filter(
                assignment=OuterRef("pk"),
                status="OPEN",
                placements__isnull=True,
            )
        )
        # Een net ingevoerde opdracht heeft nog geen rollen en zou anders meteen
        # uit de lijst verdwijnen: aangemaakt en nergens meer terug te vinden.
        # `~Exists` en niet `services__isnull=True`, want dat laatste is een LEFT
        # JOIN en levert dubbele rijen zodra er ook op organisaties gezocht wordt.
        has_no_service_yet = ~Exists(Service.objects.filter(assignment=OuterRef("pk")))
        qs = Assignment.objects.filter(has_unfilled_open_service | has_no_service_yet).order_by(
            F("created_at").desc(nulls_last=True)
        )
        # Hide intelligence-service orgs from the list and its counts, as the
        # placement list already does (see PlacementListView._get_base_queryset).
        excluded_org_ids = get_excluded_org_ids()
        if excluded_org_ids:
            qs = qs.exclude(organizations__id__in=excluded_org_ids)
        search_filter = self.request.GET.get("zoek")
        if search_filter:
            qs = qs.filter(
                Q(name__icontains=search_filter)
                | Q(extra_info__icontains=search_filter)
                | Q(organizations__name__icontains=search_filter)
                | Q(organizations__label__icontains=search_filter)
                | Q(organizations__abbreviations__icontains=search_filter)
            )
        beschikbaar_vanaf = self.request.GET.get("beschikbaar_vanaf")
        if beschikbaar_vanaf:
            try:
                vanaf_date = date.fromisoformat(beschikbaar_vanaf)
                qs = qs.filter(start_date__gte=vanaf_date)
            except ValueError:
                pass
        return qs

    def _apply_filters(self, qs, *, exclude_filter=None):
        rol = self.facets("rol", Skill)
        if exclude_filter != "rol" and rol.requested:
            qs = qs.filter(
                services__skill_id__in=rol.ids,
                services__status="OPEN",
                services__placements__isnull=True,
            )

        if exclude_filter != "org":
            qs = self.apply_org_filter(qs, "organizations__id__in")

        return qs

    def get_queryset(self):
        qs = self._get_base_queryset()
        qs = self._apply_filters(qs)
        # `has_no_roles` en niet "services_with_skills is leeg": die prefetch laadt
        # alleen open, onbezette rollen mét skill, dus een opdracht met een
        # skill-loze rol zou anders ook als "nog geen rollen" op het scherm komen.
        # Een Exists-annotatie is een subquery: geen join, dus geen wisselwerking
        # met de distinct() hierboven.
        return (
            qs.distinct()
            .annotate(has_no_roles=~Exists(Service.objects.filter(assignment=OuterRef("pk"))))
            .prefetch_related(
                Prefetch(
                    "services",
                    queryset=Service.objects.filter(
                        skill__isnull=False,
                        status="OPEN",
                        placements__isnull=True,
                    ).select_related("skill"),
                    to_attr="services_with_skills",
                )
            )
        )

    def get_template_names(self):
        if "HX-Request" in self.request.headers:
            if self.request.GET.get("filter_modal"):
                return ["parts/filter_options_modal.html"]
            hx_target = self.request.headers.get("HX-Target", "")
            if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container"):
                # See PlacementListView.get_template_names.
                panel_data = getattr(self, "_panel_data", None)
                if panel_data:
                    return [panel_data["panel_content_template"]]
                return ["parts/assignment_panel_content.html"]
            if self.request.GET.get("pagina"):
                return ["parts/assignment_card_rows.html"]
            return ["parts/filter_and_card_container_assignments.html"]
        return ["assignments.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["render_filter_fields_oob"] = "HX-Request" in self.request.headers

        base_url = reverse("assignment-list")
        for assignment in context["object_list"]:
            assignment.panel_url = _build_panel_url(self.request, opdracht=assignment.public_id)
            first_org = assignment.organizations.select_related("parent__parent__parent__parent").first()
            assignment.org_breadcrumb = get_org_breadcrumb(first_org, base_url) if first_org else None

        context["filter_target_url"] = reverse("assignment-list")
        context["search_field"] = "zoek"
        context["search_placeholder"] = "Zoek op opdracht of opdrachtgever..."
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters = {}
        beschikbaar_vanaf = self.request.GET.get("beschikbaar_vanaf")
        if beschikbaar_vanaf:
            try:
                active_filters["beschikbaar_vanaf"] = date.fromisoformat(beschikbaar_vanaf)
            except ValueError:
                active_filters["beschikbaar_vanaf"] = beschikbaar_vanaf

        # rol filter supports multi-select (values are skill public_ids)
        rol_filter = self.facets("rol", Skill).active_values
        if rol_filter:
            active_filters["rol"] = rol_filter

        # Skill/role counts: exclude role filter for cross-filtering.
        base_qs = self._get_base_queryset()
        skill_assignment_ids = (
            self._apply_filters(base_qs, exclude_filter="rol").values_list("id", flat=True).distinct()
        )
        skill_pairs = (
            Service.objects.filter(
                assignment_id__in=skill_assignment_ids,
                status="OPEN",
                placements__isnull=True,
            )
            .values_list("assignment_id", "skill_id")
            .distinct()
        )
        skill_counts = Counter(skill_id for _, skill_id in skill_pairs if skill_id is not None)

        skill_options = [{"value": "", "label": ""}]
        skill_selected_values = []
        for skill in Skill.objects.order_by("name"):
            option = {"value": str(skill.public_id), "label": skill.name, "count": skill_counts.get(skill.id, 0)}
            if str(skill.public_id) in active_filters.get("rol", set()):
                option["selected"] = True
                skill_selected_values.append(str(skill.public_id))
            skill_options.append(option)

        # Organization filter (multi-select via modal)
        self.add_org_filter_context(context, active_filters)
        self.add_unknown_filter_chips(context, {"rol": Skill})

        # Org counts exclude the org filter, so the numbers reflect the other
        # active filters — same cross-filter rule as the skill counts above.
        org_counts = _org_counts_from_filtered(
            self._apply_filters(base_qs, exclude_filter="org").distinct(),
            Assignment,
            "organizations__id",
        )

        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)
        context["client_modal_count_mode"] = "open_assignments"

        context["filter_groups"] = [
            {
                "type": "modal",
                "name": "organisatie",
                "label": "Opdrachtgever",
                "top_options": _get_top_org_options(
                    set(self.facets("org", OrganizationUnit).ids),
                    org_counts,
                    selected_self_ids=set(self.facets("org_self", OrganizationUnit).ids),
                    selected_type_labels=set(self.org_type_filter),
                ),
            },
            {
                "type": "select-multi",
                "name": "rol",
                "label": "Rol",
                "options": skill_options,
                "selected_values": skill_selected_values,
            },
            {
                "type": "date",
                "name": "beschikbaar_vanaf",
                "label": "Beschikbaar vanaf",
            },
        ]
        _finalize_filter_groups(context["filter_groups"])
        context["filter_modal_group_id"] = self.request.GET.get("filter_modal", "")

        # Build next page URL with all current filters
        if context.get("page_obj") and context["page_obj"].has_next():
            params = self.request.GET.copy()
            params["pagina"] = context["page_obj"].next_page_number()
            context["next_page_url"] = f"?{params.urlencode()}"
        else:
            context["next_page_url"] = None

        # Opens the create sheet as a panel on the list itself via
        # ?nieuwe-opdracht, like an assignment card does. hx-push-url puts the URL
        # in the address bar so a reload reopens the sheet (see side_panel.js).
        if self.request.user.has_perm("core.add_assignment"):
            context["primary_button"] = {
                "button_text": "Opdracht invoeren",
                "attrs": {
                    "hx-get": _build_panel_url(self.request, **{"nieuwe-opdracht": ""}),
                    "hx-target": "#side-panel-content",
                    "hx-swap": "innerHTML",
                    "hx-push-url": "true",
                },
            }

        # Side panel
        placement_id = self.request.GET.get("plaatsing")
        colleague_id = self.request.GET.get("collega")
        assignment_id = self.request.GET.get("opdracht")

        # ?nieuwe-opdracht opens the empty create form as a panel on the list.
        # Checked before the object lookups: this panel has no object. Without the
        # permission it falls away silently — this is the list view, not a 403.
        if self.request.GET.get("nieuwe-opdracht") is not None and self.request.user.has_perm("core.add_assignment"):
            from wies.core.services.assignments import (  # noqa: PLC0415 (import not at top level) — avoids import cycle
                assignment_create_specs,
            )

            specs = assignment_create_specs()
            form_cls, initial = build_combined_form_class(specs)
            # Prefill: the creator is usually the BM themselves.
            if getattr(self.request.user, "colleague", None):
                initial["owner"] = self.request.user.colleague
            context["panel_data"] = _build_assignment_create_panel_data(self.request, form_cls(initial=initial))
        elif placement_id:
            panel_data = _resolve_placement_panel(self.request, placement_id)
            if panel_data is not None:
                context["panel_data"] = panel_data
        elif colleague_id and not assignment_id:
            colleague = _resolve_panel_object(self.request, Colleague, colleague_id)
            if colleague is not None:
                context["panel_data"] = _build_colleague_panel_data(colleague, self.request)
        elif assignment_id:
            assignment = _resolve_panel_object(self.request, Assignment, assignment_id, select_related=("owner",))
            if assignment is not None:
                context["panel_data"] = _build_assignment_panel_data(assignment, self.request)

        # See PlacementListView.get_context_data: get_template_names reads this.
        self._panel_data = context.get("panel_data")
        return context


class UserListView(PublicIdFacetsMixin, PermissionRequiredMixin, ListView):
    """User list with filtering and infinite scroll pagination."""

    model = User
    template_name = "user_admin.html"
    paginate_by = 60
    page_kwarg = "pagina"
    permission_required = "rijksauth.view_user"

    def _get_base_queryset(self):
        """Base queryset with search applied."""
        qs = (
            User.objects.prefetch_related("groups", "colleague__labels__category")
            .filter(is_superuser=False)
            .order_by("last_name", "first_name")
        )

        search_filter = self.request.GET.get("zoek")
        if search_filter:
            qs = qs.annotate(
                full_name=Concat("first_name", Value(" "), "last_name"),
            ).filter(
                Q(full_name__icontains=search_filter)
                | Q(first_name__icontains=search_filter)
                | Q(last_name__icontains=search_filter)
                | Q(email__icontains=search_filter)
            )

        return qs

    @cached_property
    def role_filter(self) -> str:
        """``?rol=`` carries a Group pk: Group is Django's own model and has no public_id."""
        return self.request.GET.get("rol", "").strip()

    @cached_property
    def role_filter_ids(self) -> list[int]:
        """The group the filter names, empty when it names none; fails closed like every facet."""
        if not self.role_filter.isdigit():
            return []
        return list(Group.objects.filter(id=self.role_filter).values_list("id", flat=True))

    def _apply_filters(self, qs, *, exclude_filter=None):
        """Applies all selection filters, optionally excluding one filter type.

        ``exclude_filter`` is "rol", "merk", or a category_id (int) for labels.
        """
        # Label filter: OR within category, AND between categories
        for cat_id, cat_label_ids in self.labels_by_category.items():
            if exclude_filter != cat_id:
                qs = qs.filter(colleague__labels__id__in=cat_label_ids)

        # Merk filter: OR within the merk group (one merk per colleague)
        merk = self.facets("merk", Suborganization)
        if exclude_filter != "merk" and merk.requested:
            qs = qs.filter(colleague__suborganization_id__in=merk.ids)

        # Rol filter: an integer Group id, since Group has no public_id.
        if exclude_filter != "rol" and self.role_filter:
            qs = qs.filter(groups__id__in=self.role_filter_ids)

        return qs

    def get_queryset(self):
        """Applies the filters to the users queryset."""
        if self.labels_match_nothing:
            return User.objects.none()
        return self._apply_filters(self._get_base_queryset()).distinct()

    def get_template_names(self):
        """Returns the template for this request type."""
        if "HX-Request" in self.request.headers:
            if self.request.GET.get("filter_modal"):
                return ["parts/filter_options_modal.html"]
            if self.request.GET.get("pagina"):
                return ["parts/user_table_rows.html"]
            # Filter change: replace the result list (the sheet swaps OOB).
            return ["parts/user_results.html"]
        return ["user_admin.html"]

    def get_context_data(self, **kwargs):
        """Adds the dynamic filter options."""
        context = super().get_context_data(**kwargs)

        context["search_field"] = "zoek"
        context["search_placeholder"] = "Zoek op naam of email..."
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters = {}

        # label filter supports multi-select (values are label public_ids)
        label_filter = self.facets("labels", Label).active_values
        if label_filter:
            active_filters["labels"] = label_filter

        # merk filter supports multi-select (values are suborganization public_ids)
        suborganization_filter = self.facets("merk", Suborganization).active_values
        if suborganization_filter:
            active_filters["merk"] = suborganization_filter

        if self.role_filter:
            # A list, not the bare string: the chips iterate every active_filters
            # value, and a string would be walked character by character — which
            # silently matches nothing once a Group pk hits two digits.
            active_filters["rol"] = [self.role_filter]

        # Chips render in user_results.html: the filter panel is a sheet here, so
        # nothing outside it would otherwise say WHAT is filtered.

        # For each label category, count on a queryset excluding that category's filter.
        base_qs = self._get_base_queryset()

        label_filter_groups = []
        for category in LabelCategory.objects.all():
            cat_filtered_qs = self._apply_filters(base_qs, exclude_filter=category.id).distinct()
            cat_user_qs = User.objects.filter(id__in=cat_filtered_qs.values_list("id", flat=True))
            cat_label_ids = cat_user_qs.values_list("colleague__labels__id", flat=True)
            cat_label_counts = Counter(lid for lid in cat_label_ids if lid is not None)

            options = [{"value": "", "label": ""}]
            selected_values = []
            for label in Label.objects.filter(category=category):
                options.append(
                    {
                        "value": str(label.public_id),
                        "label": f"{label.name}",
                        "count": cat_label_counts.get(label.id, 0),
                    }
                )
                if str(label.public_id) in active_filters.get("labels", set()):
                    options[-1]["selected"] = True
                    selected_values.append(str(label.public_id))

            label_filter_groups.append(
                {
                    "type": "select-multi",
                    "name": "labels",
                    "label": category.name,
                    "options": options,
                    "selected_values": selected_values,
                }
            )

        # Merk filter group (one merk per colleague; counts exclude the merk filter)
        suborg_filtered_qs = self._apply_filters(base_qs, exclude_filter="merk").distinct()
        suborg_user_qs = User.objects.filter(id__in=suborg_filtered_qs.values_list("id", flat=True))
        suborg_id_values = suborg_user_qs.values_list("colleague__suborganization_id", flat=True)
        suborg_counts = Counter(mid for mid in suborg_id_values if mid is not None)

        suborganization_options = [{"value": "", "label": ""}]
        suborganization_selected_values = []
        for suborganization in Suborganization.objects.all():
            suborganization_options.append(
                {
                    "value": str(suborganization.public_id),
                    "label": suborganization.name,
                    "count": suborg_counts.get(suborganization.id, 0),
                }
            )
            if str(suborganization.public_id) in active_filters.get("merk", set()):
                suborganization_options[-1]["selected"] = True
                suborganization_selected_values.append(str(suborganization.public_id))

        suborganization_filter_group = {
            "type": "select-multi",
            "name": "merk",
            "label": "Merk",
            "options": suborganization_options,
            "selected_values": suborganization_selected_values,
        }

        # Rol group; counts exclude the rol filter itself, like merk.
        role_filtered_qs = self._apply_filters(base_qs, exclude_filter="rol").distinct()
        role_user_qs = User.objects.filter(id__in=role_filtered_qs.values_list("id", flat=True))
        role_id_values = role_user_qs.values_list("groups__id", flat=True)
        role_counts = Counter(gid for gid in role_id_values if gid is not None)

        role_options = [{"value": "", "label": ""}]
        role_selected_values = []
        for group in Group.objects.all().order_by("name"):
            role_options.append({"value": str(group.id), "label": group.name, "count": role_counts.get(group.id, 0)})
            # ?rol= holds a single Group id, so compare exactly.
            if str(group.id) == self.role_filter:
                role_options[-1]["selected"] = True
                role_selected_values.append(str(group.id))

        role_filter_group = {
            "type": "select-multi",
            "name": "rol",
            "label": "Rol",
            "options": role_options,
            "selected_values": role_selected_values,
        }

        context["active_filters"] = active_filters
        # Target URL for the filter form and the "Meer…" sheet (see filter_sidebar).
        context["filter_target_url"] = reverse("admin-users")
        context["filter_modal_group_id"] = self.request.GET.get("filter_modal", "")

        context["filter_groups"] = [
            role_filter_group,
            *label_filter_groups,
            suborganization_filter_group,
        ]
        # Adds top_options + has_more per select-multi group, so the filter sheet
        # shows a top-3 with a "Meer..." toggle like the other lists.
        _finalize_filter_groups(context["filter_groups"])

        context["primary_button"] = {
            "button_text": "Gebruiker toevoegen",
            "attrs": {
                "hx-get": reverse("user-create"),
                "hx-target": "#userFormModal",
                "hx-push-url": "false",  # necessary because nested in htmx powered form
            },
        }

        # Build next page URL with all current filters
        if context.get("page_obj") and context["page_obj"].has_next():
            params = self.request.GET.copy()
            params["pagina"] = context["page_obj"].next_page_number()
            context["next_page_url"] = f"?{params.urlencode()}"
        else:
            context["next_page_url"] = None

        return context


@permission_required("rijksauth.add_user", raise_exception=True)
def user_create(request):
    """Creates a user: GET returns the form modal, POST processes the creation."""

    form_post_url = reverse("user-create")
    modal_title = "Nieuwe gebruiker"
    element_id = "userFormModal"

    if request.method == "GET":
        form = UserForm()
        form.fields["first_name"].widget.attrs["autofocus"] = True
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Voeg gebruiker toe",
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            create_user(
                request.user,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
                labels=form.cleaned_data.get("labels"),
                groups=form.cleaned_data.get("groups"),
                suborganization=form.cleaned_data.get("suborganization"),
                request=request,
            )
            # HTMX needs HX-Redirect to force a full page redirect.
            if "HX-Request" in request.headers:
                response = HttpResponse(status=200)
                response["HX-Redirect"] = reverse("admin-users")
                return response
            return redirect(reverse("admin-users"))
        # Re-render with errors; HTMX keeps the modal open.
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Voeg gebruiker toe",
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    return HttpResponse(status=405)


@permission_required("rijksauth.change_user", raise_exception=True)
def user_edit(request, public_id):
    """Edits a user: GET returns the populated form modal, POST processes the update."""
    edited_user = get_object_or_404(User, public_id=public_id, is_superuser=False)
    form_post_url = reverse("user-edit", args=[edited_user.public_id])
    modal_title = "Gebruiker bewerken"
    element_id = "userFormModal"

    if request.method == "GET":
        form = UserForm(instance=edited_user)
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Opslaan",
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    if request.method == "POST":
        form = UserForm(request.POST, instance=edited_user)
        if form.is_valid():
            update_user(
                updater=request.user,
                user=edited_user,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
                labels=form.cleaned_data.get("labels"),
                groups=form.cleaned_data.get("groups"),
                suborganization=form.cleaned_data.get("suborganization"),
                request=request,
            )
            # HTMX needs HX-Redirect to force a full page redirect.
            if "HX-Request" in request.headers:
                response = HttpResponse(status=200)
                response["HX-Redirect"] = reverse("admin-users")
                return response
            return redirect(reverse("admin-users"))
        # Re-render with errors; HTMX keeps the modal open.
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Opslaan",
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    return HttpResponse(status=405)


@permission_required("rijksauth.delete_user", raise_exception=True)
def user_delete(request, public_id):
    """Deletes a user, after the confirmation modal."""
    user = get_object_or_404(User, public_id=public_id, is_superuser=False)

    if request.method == "GET":
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Gebruiker verwijderen?",
                "dialog_supporting": (
                    f"Weet je zeker dat je {user.first_name} {user.last_name} wilt verwijderen? "
                    "Verwijderen is permanent en niet terug te draaien."
                ),
                "confirm_label": "Verwijder gebruiker",
                "cancel_label": "Behoud gebruiker",
                "form_post_url": reverse("user-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        if hasattr(user, "colleague") and user.colleague:
            label_names = [label.name for label in user.colleague.labels.all()]
        else:
            label_names = []
        context = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "label_names": label_names,
            "group_names": [g.name for g in user.groups.all()],
        }
        # Capture the int PK before delete() nulls it; Event.object_id keeps
        # referencing the internal id, not the public_id.
        user_pk = user.id
        user.delete()
        create_event(
            object_type="User",
            action="delete",
            source="user",
            object_id=user_pk,
            user=request.user,
            request=request,
            context=context,
        )
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("admin-users")
        return response
    return HttpResponse(status=405)


# Safety ceiling so a single upload can't exhaust a worker's memory
MAX_CSV_UPLOAD_BYTES = 50 * 1024 * 1024
_CSV_MAX_MB = MAX_CSV_UPLOAD_BYTES // (1024 * 1024)
_CSV_TOO_LARGE_MSG = f"Bestand te groot. Upload een CSV-bestand van maximaal {_CSV_MAX_MB} MB."


def _csv_too_large(csv_file) -> bool:
    return bool(csv_file.size) and csv_file.size > MAX_CSV_UPLOAD_BYTES


@permission_required("rijksauth.add_user", raise_exception=True)
def user_import_csv(request):
    """Imports users from a CSV file; see ``create_users_from_csv`` for the format."""
    if request.method == "GET":
        return render(request, "user_import.html")
    if request.method == "POST":
        if "csv_file" not in request.FILES:
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": ["Geen bestand geüpload. Upload een CSV-bestand."]}},
            )

        csv_file = request.FILES["csv_file"]

        if not csv_file.name.endswith(".csv"):
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": ["Ongeldig bestandstype. Upload een CSV-bestand."]}},
            )

        if _csv_too_large(csv_file):
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": [_CSV_TOO_LARGE_MSG]}},
            )

        try:
            csv_content = csv_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": ["Ongeldige bestandscodering. Gebruik UTF-8."]}},
            )

        result = create_users_from_csv(request.user, csv_content, request=request)

        return render(request, "user_import.html", {"result": result})
    return HttpResponse(status=405)


@permission_required(
    [
        "core.add_assignment",
        "core.add_service",
        "core.add_placement",
        "core.add_colleague",
    ],
    raise_exception=True,
)
def assignment_import_csv(request):
    """Imports assignments from a CSV file, with their services, placements,
    colleagues and skills; see ``create_assignments_from_csv`` for the format."""
    if request.method == "GET":
        return render(request, "assignment_import.html")
    if request.method == "POST":
        if "csv_file" not in request.FILES:
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": ["Geen bestand geüpload. Upload een CSV-bestand."]}},
            )

        csv_file = request.FILES["csv_file"]

        if not csv_file.name.endswith(".csv"):
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": ["Ongeldig bestandstype. Upload een CSV-bestand."]}},
            )

        if _csv_too_large(csv_file):
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": [_CSV_TOO_LARGE_MSG]}},
            )

        try:
            csv_content = csv_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": ["Invalid CSV file encoding. Please use UTF-8."]}},
            )

        result = create_assignments_from_csv(request.user, csv_content, request=request)

        return render(request, "assignment_import.html", {"result": result})
    return HttpResponse(status=405)


@permission_required("core.view_organizationunit", raise_exception=True)
def organization_admin(request):
    """Show all organization units in a collapsible tree, grouped by type. Only available in DEBUG mode."""
    if not settings.DEBUG:
        raise Http404
    rows = OrganizationUnit.objects.values("id", "parent_id", "name", "label", "abbreviations", "end_date")

    today = timezone.now().date()
    units_by_id: dict[int, dict] = {}
    for row in rows:
        row["is_inactive"] = row["end_date"] is not None and row["end_date"] <= today
        row["tree_children"] = []
        units_by_id[row["id"]] = row

    roots: list[dict] = []
    for unit in units_by_id.values():
        parent_id = unit["parent_id"]
        if parent_id and parent_id in units_by_id:
            units_by_id[parent_id]["tree_children"].append(unit)
        else:
            roots.append(unit)

    def sort_key(u):
        return u["label"] or u["name"]

    for unit in units_by_id.values():
        unit["tree_children"].sort(key=sort_key)
    roots.sort(key=sort_key)

    # Organization types for the root nodes only, via the M2M through table.
    root_ids = {u["id"] for u in roots}
    type_links = (
        OrganizationUnit.organization_types.through.objects.filter(organizationunit_id__in=root_ids)
        .select_related("organizationtype")
        .values_list("organizationunit_id", "organizationtype__label")
    )
    root_types: dict[int, list[str]] = {}
    for unit_id, type_label in type_links:
        root_types.setdefault(unit_id, []).append(type_label)

    grouped: dict[str, list[dict]] = {}
    ungrouped: list[dict] = []
    for unit in roots:
        type_labels = root_types.get(unit["id"], [])
        if type_labels:
            for type_label in type_labels:
                grouped.setdefault(type_label, []).append(unit)
        else:
            ungrouped.append(unit)

    type_groups = [(ORG_TYPE_PLURAL.get(name, name), units) for name, units in sorted(grouped.items())]
    if ungrouped:
        type_groups.append(("Overig", ungrouped))

    return render(request, "organization_admin.html", {"type_groups": type_groups})


@permission_required("core.view_labelcategory", raise_exception=True)
def label_admin(request):
    """Main label admin page."""
    categories = annotate_usage_counts(LabelCategory.objects.all())
    return render(request, "label_admin.html", {"categories": categories})


@login_required
@require_POST
def user_theme(request):
    """Stores the display preference of the logged-in user.

    The choice lives on the Colleague, not in the browser, so it travels to every
    device and base.html can render it server-side as data-scheme — correct on
    first paint, without a flash.
    """
    theme = request.POST.get("theme", "")
    if theme not in Colleague.Theme.values:
        return HttpResponseBadRequest("Onbekende weergave")
    colleague = request.user.colleague
    colleague.theme = theme
    colleague.save(update_fields=["theme"])
    return HttpResponse(status=204)


@login_required
def profile_name_edit(request):
    """First and last name of the logged-in user, in one sheet.

    Saving goes through each field's Editable save, so the name on the linked
    Colleague follows along exactly as it does for inline edit.
    """
    from wies.core.editables.user import UserEditables  # noqa: PLC0415 — mirrors the other editable imports here

    user = request.user

    if request.method == "POST":
        form = ProfileNameForm(request.POST, instance=user)
        if form.is_valid():
            UserEditables.first_name.save(user, form.cleaned_data["first_name"])
            UserEditables.last_name.save(user, form.cleaned_data["last_name"])
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("user-profile")
            return response
    else:
        form = ProfileNameForm(instance=user)

    form.fields["first_name"].widget.attrs["autofocus"] = True

    return render(
        request,
        "parts/profile_name_sheet.html",
        {
            "content": form,
            "form_post_url": reverse("profile-name-edit"),
        },
    )


@login_required
def profile_labels_edit(request):
    """All label categories of your own profile in one sheet.

    Onboarding asks the same question with the same fields, but saves each one
    when its step is left; here they land together under one "Opslaan".
    """
    colleague = getattr(request.user, "colleague", None)
    if colleague is None:
        raise Http404("Geen collegaprofiel om te bewerken")

    categories = list(LabelCategory.objects.order_by("name"))

    if request.method == "POST":
        form = ProfileLabelsForm(request.POST, colleague=colleague, categories=categories)
        if form.is_valid():
            form.save()
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("user-profile")
            return response
    else:
        form = ProfileLabelsForm(colleague=colleague, categories=categories)

    if form.fields:
        next(iter(form.fields.values())).widget.attrs["autofocus"] = True

    return render(
        request,
        "parts/profile_labels_sheet.html",
        {
            "content": form,
            "form_post_url": reverse("profile-labels-edit"),
        },
    )


@permission_required("core.change_labelcategory", raise_exception=True)
def label_category_manage(request):
    """All categories in one sheet: rename, pick a colour, add rows.

    Adding a row (``extra_row``) and dropping an unsaved one
    (``delete_new_row_index``) post the current state back and re-render only the
    body without validating, so typed values survive and "naam is verplicht" does
    not flash on empty rows. Deleting an existing category goes through
    ``label-category-delete``.
    """
    queryset = LabelCategory.objects.all()
    prefix = LabelCategoryFormSet().prefix

    invalid_post = False
    if request.method == "POST":
        is_rerender = "extra_row" in request.POST or "delete_new_row_index" in request.POST
        if is_rerender:
            data = request.POST.copy()
            if "extra_row" in data:
                total = int(data.get(f"{prefix}-TOTAL_FORMS", 0) or 0)
                data[f"{prefix}-TOTAL_FORMS"] = str(total + 1)
            else:
                data = _drop_new_category_row(data, prefix, data.get("delete_new_row_index"))
            formset = LabelCategoryFormSet(data, queryset=queryset)
            # Don't validate on a row mutation: the user is still typing. Setting
            # an empty error dict suppresses the lazy full_clean.
            for form in formset.forms:
                form._errors = ErrorDict(renderer=form.renderer)
            if "extra_row" in request.POST and formset.forms:
                # Focus the row that was just added, as the old JS did.
                formset.forms[-1].fields["name"].widget.attrs["autofocus"] = True
            return _render_category_manage_body(request, formset)

        formset = LabelCategoryFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("label-admin")
            return response
        invalid_post = True
    else:
        formset = LabelCategoryFormSet(queryset=queryset)

    if formset.forms:
        formset.forms[0].fields["name"].widget.attrs["autofocus"] = True

    # On error only the body is refreshed: the sheet is already open, and
    # re-sending the whole sheet would stack a second one on top.
    template = "parts/label_category_manage_body.html" if invalid_post else "parts/label_category_manage_sheet.html"
    return _render_category_manage_body(request, formset, template=template)


def _drop_new_category_row(data, prefix, drop_index):
    """Drops one not-yet-saved row from the posted formset data.

    New rows are renumbered contiguously: a gap in the indexes would come back as
    an empty row on the next re-render. Saved rows keep their index — a
    modelformset binds the first INITIAL_FORMS forms to the queryset in order, so
    moving one to another slot would save it as a new object.
    """
    try:
        drop = int(drop_index)
    except TypeError, ValueError:
        return data

    initial = int(data.get(f"{prefix}-INITIAL_FORMS", 0) or 0)
    total = int(data.get(f"{prefix}-TOTAL_FORMS", 0) or 0)
    if drop < initial:
        # Only new rows can be dropped this way; ignore a bogus index.
        return data

    result = data.copy()
    # Collect the field values per index, drop the removed one, then renumber the
    # new rows contiguously from INITIAL_FORMS.
    new_rows = []
    for i in range(initial, total):
        if i == drop:
            continue
        new_rows.append({k[len(f"{prefix}-{i}-") :]: v for k, v in data.items() if k.startswith(f"{prefix}-{i}-")})
    for i in range(initial, total):
        for key in [k for k in result if k.startswith(f"{prefix}-{i}-")]:
            del result[key]
    for offset, fields in enumerate(new_rows):
        i = initial + offset
        for name, value in fields.items():
            result[f"{prefix}-{i}-{name}"] = value
    result[f"{prefix}-TOTAL_FORMS"] = str(initial + len(new_rows))
    return result


def _render_category_manage_body(request, formset, template="parts/label_category_manage_body.html"):
    return render(
        request,
        template,
        {
            "formset": formset,
            "form_post_url": reverse("label-category-manage"),
        },
    )


@permission_required("core.change_label", raise_exception=True)
def label_form(request, public_id=None):
    """One sheet for both adding and editing a label (category + name)."""
    label = get_object_or_404(Label, public_id=public_id) if public_id else None
    is_edit = label is not None

    invalid_post = False
    if request.method == "POST":
        form = LabelForm(request.POST, instance=label)
        if form.is_valid():
            form.save()
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("label-admin")
            return response
        invalid_post = True
    else:
        form = LabelForm(instance=label, category_id=request.GET.get("categorie"))

    form.fields["name"].widget.attrs["autofocus"] = True

    # On error only the body is refreshed: the sheet is already open, and
    # re-sending the whole sheet would stack a second one on top.
    template = "parts/label_form_body.html" if invalid_post else "parts/label_form_sheet.html"

    return render(
        request,
        template,
        {
            "content": form,
            "modal_title": "Label bewerken" if is_edit else "Label toevoegen",
            "form_button_label": "Opslaan" if is_edit else "Voeg label toe",
            "form_post_url": (
                reverse("label-form-edit", kwargs={"public_id": label.public_id})
                if is_edit
                else reverse("label-form-create")
            ),
            "modal_element_id": "labelFormModal",
        },
    )


def _category_delete_warning(category):
    """The confirmation text; the labels always go with the category."""
    count = category.labels.count()
    if count == 0:
        return f"Weet je zeker dat je categorie '{category.name}' wilt verwijderen?"
    return (
        f"Weet je zeker dat je categorie '{category.name}' wilt verwijderen? "
        f"De {count} labels erin worden ook verwijderd."
    )


@permission_required("core.delete_labelcategory", raise_exception=True)
def label_category_delete(request, public_id):
    """Deletes a label category, after the confirmation dialog. For use with htmx."""
    category = get_object_or_404(LabelCategory, public_id=public_id)
    if request.method == "GET":
        # A dialog, not a sheet: the question comes from the manage sheet, which
        # has to stay visible behind the confirmation.
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Categorie verwijderen?",
                "dialog_supporting": _category_delete_warning(category),
                "confirm_label": "Verwijder categorie en labels",
                "cancel_label": "Behoud categorie",
                "form_post_url": reverse("label-category-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        category_name = category.name  # Read before delete() clears the instance.
        # The labels cascade away with the category.
        category.delete()
        messages.success(request, f"Categorie '{category_name}' succesvol verwijderd")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("label-admin")
        return response
    return HttpResponse(status=405)


@permission_required("core.delete_label", raise_exception=True)
def label_delete(request, public_id):
    """Deletes a label, after the confirmation dialog. For use with htmx."""

    label = get_object_or_404(Label, public_id=public_id)

    label_use_count = label.colleagues.count()

    if request.method == "GET":
        # A centred confirmation dialog, not a side sheet, like the rest of Wies.
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": f"Label verwijderen: {label.name}?",
                "dialog_supporting": (
                    f"Weet je zeker dat je dit label wilt verwijderen? Het wordt gebruikt op {label_use_count} plekken."
                ),
                "confirm_label": "Verwijderen",
                "cancel_label": "Annuleren",
                "form_post_url": reverse("label-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        label.delete()
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("label-admin")
        return response

    return HttpResponse(status=405)


@permission_required("core.view_suborganization", raise_exception=True)
def suborganization_admin(request):
    """Main merken admin page."""
    suborganizations = annotate_suborganization_usage_counts(Suborganization.objects.all())
    return render(request, "suborganization_admin.html", {"suborganizations": suborganizations})


@permission_required("core.add_suborganization", raise_exception=True)
def suborganization_create(request):
    """Creates a suborganization via the sheet (htmx).

    GET opens the sheet, a valid POST saves and re-renders the merk list while
    closing it, an invalid POST re-renders only the body so the sheet keeps
    standing.
    """
    form_post_url = reverse("suborganization-create")
    modal_title = "Merk toevoegen"
    form_button_label = "Voeg merk toe"
    element_id = "suborganizationFormModal"

    if request.method == "POST":
        form = SuborganizationForm(request.POST)
        if form.is_valid():
            form.save()
            suborganizations = annotate_suborganization_usage_counts(Suborganization.objects.all())
            response = render(request, "parts/suborganization_list.html", {"suborganizations": suborganizations})
            response["HX-Retarget"] = "#suborganization_list_container"
            response["HX-Trigger"] = "closeModal"
            return response
    else:
        form = SuborganizationForm()
        # Focus the name field on GET only; after a validation error the focus
        # belongs with the failing field instead of jumping back to the top.
        form.fields["name"].widget.attrs["autofocus"] = True

    return render(
        request,
        "parts/generic_form_modal.html",
        {
            "content": form,
            "form_post_url": form_post_url,
            "modal_title": modal_title,
            "form_button_label": form_button_label,
            "modal_element_id": element_id,
            "target_element_id": element_id,
        },
    )


@permission_required("core.change_suborganization", raise_exception=True)
def suborganization_edit(request, public_id):
    """Edits a suborganization. Returns a partial for use with htmx."""
    suborganization = get_object_or_404(Suborganization, public_id=public_id)
    form_post_url = reverse("suborganization-edit", kwargs={"public_id": public_id})
    modal_title = f"Bewerk merk: {suborganization.name}"
    form_button_label = "Opslaan"
    element_id = "suborganizationFormModal"

    if request.method == "GET":
        form = SuborganizationForm(instance=suborganization)
        form.fields["name"].widget.attrs["autofocus"] = True
        return render(
            request,
            "parts/generic_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": form_button_label,
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    if request.method == "POST":
        form = SuborganizationForm(request.POST, instance=suborganization)
        if form.is_valid():
            form.save()
            suborganizations = annotate_suborganization_usage_counts(Suborganization.objects.all())
            response = render(request, "parts/suborganization_list.html", {"suborganizations": suborganizations})
            response["HX-Retarget"] = "#suborganization_list_container"
            response["HX-Trigger"] = "closeModal"
            return response
        return render(
            request,
            "parts/generic_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": form_button_label,
                "modal_element_id": element_id,
                "target_element_id": element_id,
            },
        )
    return None


@permission_required("core.delete_suborganization", raise_exception=True)
def suborganization_delete(request, public_id):
    """Deletes a suborganization. For use with htmx."""
    suborganization = get_object_or_404(Suborganization, public_id=public_id)
    suborganization_use_count = suborganization.colleagues.count()

    if request.method == "GET":
        # A centred confirmation dialog, not a side sheet, like the rest of Wies.
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": f"Merk verwijderen: {suborganization.name}?",
                "dialog_supporting": (
                    f"Weet je zeker dat je dit merk wilt verwijderen? "
                    f"Het wordt gebruikt door {suborganization_use_count} collega('s)."
                ),
                "confirm_label": "Verwijderen",
                "cancel_label": "Annuleren",
                "form_post_url": reverse("suborganization-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        suborganization.delete()
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("suborganization-admin")
        return response
    return HttpResponse(status=405)


def assignment_events_partial(request, public_id):
    assignment = get_object_or_404(Assignment, public_id=public_id)
    events = list(
        Event.objects.filter(
            object_type="Assignment",
            object_id=assignment.id,
        )
        .select_related("user__colleague")
        .order_by("-timestamp")[:20]
    )
    events = [event for event in events if _attach_audit_render_data(event, assignment, request)]
    for event in events:
        _attach_audit_sentence(event)
    return render(request, "parts/assignment_events_timeline.html", {"events": events})


HET_FIELD_LABELS = {"team", "merk"}


def _field_phrase(label: str) -> str:
    """Turns a field label into a sentence fragment: "Beschrijving" -> "de
    beschrijving", "Team" -> "het team". A label with an inner capital is a name,
    not a common noun ("Business Manager"), so its casing is left alone."""
    if not label or label == "een veld":
        return label or "een veld"
    noun = label[: -len("(s)")].strip() + "s" if label.endswith("(s)") else label
    # Judge the casing on the part outside any parenthetical, so "E-mail (ODI)"
    # is not read as a name because of the acronym.
    head = noun.split("(")[0]
    if not any(c.isupper() for c in head[1:]):
        noun = noun[0].lower() + noun[1:]
    article = "het" if noun.lower() in HET_FIELD_LABELS else "de"
    return f"{article} {noun}"


def _attach_audit_sentence(event) -> None:
    """Phrases the event as one running sentence, commit-message style.

    Long values (textareas) stay out of the sentence; the template renders them
    as Van/Naar blocks underneath. Requires ``_attach_audit_render_data`` to have
    run first, for render_kind, formatted_old/new and diff_entries.
    """
    colleague = getattr(event.user, "colleague", None) if event.user else None
    event.author_name = colleague.name if colleague else ""
    author = event.author_name or "Onbekende gebruiker"
    event.type_label = "Aangemaakt" if event.action == "create" else "Gewijzigd"
    if event.action == "create":
        event.sentence = f"{author} heeft deze opdracht aangemaakt."
        return
    if event.context.get("merge"):
        ids = event.context.get("merged_ids") or []
        noun = "dubbele opdracht" if len(ids) == 1 else "dubbele opdrachten"
        joined_ids = ", ".join(f"#{i}" for i in ids)
        event.sentence = f"{author} heeft {len(ids)} {noun} samengevoegd ({joined_ids})."
        return
    label = _field_phrase(event.context.get("field_label") or "een veld")
    if event.render_kind == "collection":
        clauses = [entry["text"] for entry in event.diff_entries or []]
        if not clauses:
            event.sentence = f"{author} heeft {label} gewijzigd."
        elif len(clauses) == 1:
            event.sentence = f"{author} heeft {clauses[0]}."
        else:
            event.sentence = f"{author} heeft {', '.join(clauses[:-1])} en {clauses[-1]}."
        return
    old, new = event.formatted_old, event.formatted_new
    if event.render_kind == "textarea":
        if not old and new:
            event.sentence = f"{author} heeft {label} toegevoegd."
        elif old and not new:
            event.sentence = f"{author} heeft {label} verwijderd."
        else:
            event.sentence = f"{author} heeft {label} gewijzigd."
        return
    if old and new:
        event.sentence = f'{author} heeft {label} van "{old}" naar "{new}" gewijzigd.'
    elif new:
        event.sentence = f'{author} heeft {label} naar "{new}" gewijzigd.'
    elif old:
        event.sentence = f"{author} heeft {label} leeggemaakt."
    else:
        event.sentence = f"{author} heeft {label} gewijzigd."


def _team_event_privacy_note(assignment, request, changes) -> str:
    """The note on one team row in the timeline, or "" when there is nothing to say.

    Only for a viewer who sees the row while others do not — in practice the BM.
    Rows that were filtered away no longer exist here, so they cannot carry a
    note; the note above the list covers those.
    """
    from wies.core.editables.assignment import (  # noqa: PLC0415 — avoids import cycle
        team_changes_are_restricted,
        visible_service_rows,
    )

    if not team_changes_are_restricted(assignment, request, changes):
        return ""
    return next(
        (note for row in visible_service_rows(assignment, request) if (note := row.get("privacy_warning_text"))),
        "",
    )


def _attach_audit_render_data(event, obj, request) -> bool:
    """Prepares ``event`` for the timeline. False means the viewer may see nothing
    of it and it must not be rendered at all."""
    event.render_kind = "text"
    event.diff_entries = None
    event.formatted_old = event.context.get("old_value")
    event.formatted_new = event.context.get("new_value")

    # Delete events are kept for the audit trail but never rendered here: a
    # deleted opdracht has no panel to open.
    if event.action != "update":
        return True
    model_label = event.object_type.lower()
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        return True
    spec = editable_set._editables.get(event.context.get("field_name", ""))
    if spec is None:
        return True

    if isinstance(spec, EditableCollection):
        event.render_kind = "collection"
        changes = event.context.get("changes", [])
        if spec.visible_changes is not None:
            try:
                visible = spec.visible_changes(obj, request, changes)
            except AttributeError, TypeError:
                # A legacy row shape the filter can't read is a row whose names
                # we can't clear, so show no rows rather than risk a leak.
                logger.warning(
                    "Audit visible_changes failed for collection Event id=%s field=%s; hiding its rows",
                    event.id,
                    event.context.get("field_name"),
                    exc_info=True,
                )
                return False
            if changes and not visible:
                return False
            # A viewer who sees more than an outsider (the BM gets the unfiltered
            # list) should know this row is hidden from others. Team rows only:
            # other fields look the same to everyone.
            event.privacy_note = _team_event_privacy_note(obj, request, visible)
            changes = visible
        if spec.render_change is not None:
            try:
                event.diff_entries = [spec.render_change(c) for c in changes]
            except TypeError:
                logger.warning(
                    "Audit render_change failed for collection Event id=%s field=%s; falling back to raw context",
                    event.id,
                    event.context.get("field_name"),
                    exc_info=True,
                )
                event.diff_entries = None
        return True

    from django import forms  # noqa: PLC0415

    # A textarea gets the Van/Naar block, unless it is one row high: that is a
    # plain text field allowed to wrap, and "van X naar Y" reads better there.
    widget = getattr(spec, "widget", None)
    is_textarea = isinstance(widget, forms.Textarea) or (
        isinstance(widget, type) and issubclass(widget, forms.Textarea)
    )
    rows = getattr(widget, "attrs", {}).get("rows", 3) if not isinstance(widget, type) else 3
    if is_textarea and int(rows or 3) > 1:
        event.render_kind = "textarea"

    formatter = getattr(spec, "render_change", None) or (lambda v: str(v or ""))
    try:
        event.formatted_old = formatter(event.context.get("old_value"))
        event.formatted_new = formatter(event.context.get("new_value"))
    except TypeError:
        # A legacy event can hold a shape the current render_change no longer
        # accepts; fall back to the raw context values so the row still renders.
        logger.warning(
            "Audit render_change failed for Event id=%s field=%s; falling back to raw context",
            event.id,
            event.context.get("field_name"),
            exc_info=True,
        )
    return True


def assignment_delete(request, public_id):
    assignment = get_object_or_404(Assignment, public_id=public_id)
    if not has_permission(Verb.DELETE, assignment, request.user):
        return HttpResponseForbidden()

    if request.method == "GET":
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Opdracht verwijderen?",
                "dialog_supporting": (
                    f"Weet je zeker dat je opdracht '{assignment.name}' wilt verwijderen? "
                    "Verwijderen is permanent en niet terug te draaien."
                ),
                "confirm_label": "Verwijder opdracht",
                "cancel_label": "Behoud opdracht",
                "form_post_url": reverse("assignment-delete", kwargs={"public_id": public_id}),
            },
        )
    if request.method == "POST":
        name = assignment.name
        # Capture the int PK before delete() nulls it; Event.object_id keeps
        # referencing the internal id, not the public_id.
        assignment_pk = assignment.id
        # Snapshot related rows before they cascade away.
        context = _assignment_audit_snapshot(assignment)
        # Atomic so a failed audit insert rolls back the delete: losing the
        # opdracht without a trace would be the worst outcome.
        with transaction.atomic():
            assignment.delete()
            create_event(
                object_type="Assignment",
                action="delete",
                source="user",
                object_id=assignment_pk,
                user=request.user,
                request=request,
                context=context,
            )
        messages.success(request, f"Opdracht '{name}' succesvol verwijderd")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = _page_url_behind_panel(request)
        return response
    return HttpResponse(status=405)


def _page_url_behind_panel(request) -> str:
    """The page the side panel was opened over, with the panel params dropped.

    The panel is an overlay on a real page, so after deleting we return there
    instead of jumping to the assignment list. Falls back to that list when the
    HX-Current-URL header is absent.
    """
    current = request.headers.get("HX-Current-URL")
    if not current:
        return reverse("assignment-list")
    parsed = urllib.parse.urlparse(current)
    # Keep collega/pagina/filters — only the opdracht panel is closing.
    return _url_drop_params(parsed.path, QueryDict(parsed.query), ("opdracht", "plaatsing"))


def _assignment_audit_snapshot(assignment) -> dict:
    """Snapshot for the create/delete audit event: every rol with who fills it
    (``"Java (Robbert)"``) or ``"open"``, plus the opdrachtgevers and the name.
    One entry per rol, so placements aren't duplicated."""
    services = []
    for s in assignment.services.select_related("skill").prefetch_related("placements__colleague"):
        rol = s.skill.name if s.skill_id else s.description
        names = [p.colleague.name for p in s.placements.all()]
        services.append(f"{rol} ({', '.join(names) if names else 'open'})")
    organizations = [rel.organization.label or rel.organization.name for rel in assignment.organization_relations.all()]
    snapshot = {"name": assignment.name}
    if services:
        snapshot["services"] = services
    if organizations:
        snapshot["organizations"] = organizations
    return snapshot


def user_profile(request):
    """User's own profile page with editable fields and full assignment history."""
    user = request.user
    colleague = getattr(user, "colleague", None)

    # Side panel handling
    colleague_id = request.GET.get("collega")
    assignment_id = request.GET.get("opdracht")
    placement_id = request.GET.get("plaatsing")
    panel_data = None

    if placement_id:
        panel_data = _resolve_placement_panel(request, placement_id)
    elif assignment_id:
        assignment = _resolve_panel_object(request, Assignment, assignment_id)
        if assignment is not None:
            panel_data = _build_assignment_panel_data(assignment, request)
    elif colleague_id:
        panel_colleague = _resolve_panel_object(request, Colleague, colleague_id)
        if panel_colleague is not None:
            panel_data = _build_colleague_panel_data(panel_colleague, request)

    # HTMX partial responses for panel swaps
    if "HX-Request" in request.headers:
        hx_target = request.headers.get("HX-Target")
        if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container") and panel_data:
            return render(request, panel_data["panel_content_template"], {"panel_data": panel_data})

    label_categories = []
    for category in LabelCategory.objects.order_by("name"):
        selected = list(colleague.labels.filter(category=category).order_by("name")) if colleague else []
        label_categories.append({"category": category, "labels": selected})

    assignment_list = _get_colleague_assignments(request, colleague, viewer=colleague) if colleague else []

    return render(
        request,
        "user_profile.html",
        {
            "colleague": colleague,
            "label_categories": label_categories,
            "assignment_list": assignment_list,
            "panel_data": panel_data,
        },
    )


@require_POST
def onboarding_complete(request):
    """Marks the first-login onboarding wizard as done (completed or skipped).

    An HTMX request gets a 204 with a ``closeOnboarding`` trigger so the dialog
    closes in place; otherwise it redirects home.
    """
    user = request.user
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = timezone.now()
        user.save(update_fields=["onboarding_completed_at"])

    if "HX-Request" in request.headers:
        response = HttpResponse(status=204)
        response["HX-Trigger"] = "closeOnboarding"
        return response
    return redirect("home")


# The onboarding edit screen builds one form over the assignment plus your own
# role(s) from the same specs as inline edit, so save and audit behaviour stay
# identical.


def _onboarding_entry(request, public_id):
    """The onboarding entry for this assignment, or None when you are not on it."""
    from wies.core.context_processors import _onboarding_assignments  # noqa: PLC0415 — avoids import cycle

    colleague = getattr(request.user, "colleague", None)
    for entry in _onboarding_assignments(colleague, request.user):
        if entry["assignment"].public_id == public_id:
            return entry
    return None


def _onboarding_edit_groups(request, entry, data=None):
    """Form groups for the edit screen: the assignment and each of your own roles.

    Every group gets a prefix so the role fields of multiple services don't
    collide on the same names. The Business Manager is deliberately left out:
    here they are the contact person, not something you set yourself.
    """
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle
    from wies.core.editables.service import ServiceEditables  # noqa: PLC0415

    assignment = entry["assignment"]
    groups = []

    assignment_specs = [
        (editable_set, spec, obj)
        for (editable_set, spec, obj) in assignment_edit_specs(assignment, request.user)
        if spec is not AssignmentEditables.owner
    ]
    if assignment_specs:
        form_cls, initial = build_combined_form_class(assignment_specs)
        groups.append(
            {
                # No heading: the screen title already names the assignment.
                "title": None,
                "specs": assignment_specs,
                "form": form_cls(data, initial=initial, prefix="opdracht"),
            }
        )

    services = entry["services"]
    for service in services:
        service_specs = [
            (ServiceEditables, spec, service)
            for spec in (ServiceEditables.skill, ServiceEditables.description)
            if has_permission(Verb.UPDATE, service, request.user, spec)
        ]
        if not service_specs:
            continue
        form_cls, initial = build_combined_form_class(service_specs)
        # Without edit rights on the role the form omits its field, so surface the
        # role read-only to keep the description in context.
        skill_editable = any(spec is ServiceEditables.skill for (_, spec, _) in service_specs)
        groups.append(
            {
                # A heading only when there is more than one role; otherwise the
                # field labels speak for themselves.
                "title": None if len(services) == 1 else f"Rol: {service.skill.name if service.skill else 'onbekend'}",
                "specs": service_specs,
                "form": form_cls(data, initial=initial, prefix=f"rol-{service.id}"),
                # None when editable (the form renders the field); otherwise the
                # role name, or "" so the template shows its dash fallback.
                "readonly_skill": None if skill_editable else (service.skill.name if service.skill else ""),
            }
        )

    return groups


def onboarding_assignment_edit(request, public_id):
    """Edit screen for one assignment inside the onboarding wizard."""
    entry = _onboarding_entry(request, public_id)
    if entry is None:
        raise Http404("Unknown assignment")

    groups = _onboarding_edit_groups(request, entry, data=request.POST if request.method == "POST" else None)
    if not groups:
        return HttpResponseForbidden()

    if request.method == "POST" and all(group["form"].is_valid() for group in groups):
        with transaction.atomic():
            for group in groups:
                save_edit_specs(request, group["specs"], group["form"].cleaned_data)
        # After-swap: closing re-reads the step from the DOM (see onboarding.js).
        entry = _onboarding_entry(request, public_id)
        response = render(request, "parts/onboarding/onboarding_assignment_box.html", {"entry": entry})
        response["HX-Retarget"] = f"#onboarding-assignment-{public_id}"
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger-After-Swap"] = "onboardingDetailClose"
        return response

    return render(
        request,
        "parts/onboarding/onboarding_assignment_form.html",
        {"entry": entry, "groups": groups},
    )


def contact(request):
    return render(request, "contact.html")


def faq(request):
    return render(request, "faq.html")


def privacy(request):
    return render(request, "privacy.html")


def toegankelijkheid(request):
    return render(request, "toegankelijkheid.html")


def error_400(request, exception=None):
    return render(request, "400.html", status=400)


@login_not_required
def error_403(request, exception=None):
    return render(request, "403.html", status=403)


@login_not_required
def error_404(request, exception=None):
    return render(request, "404.html", status=404)


@login_not_required
def error_500(request):
    return render(request, "500.html", status=500)


@login_not_required
def robots_txt(request):
    """Serves robots.txt, blocking crawlers and AI scrapers."""
    content = """# Disallow all crawlers
User-agent: *
Disallow: /

# AI scrapers
User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: cohere-ai
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Amazonbot
Disallow: /

User-agent: FacebookBot
Disallow: /

User-agent: Meta-ExternalAgent
Disallow: /

User-agent: Applebot-Extended
Disallow: /
"""
    return HttpResponse(content, content_type="text/plain")


def search_suggestions(request):
    """Returns org abbreviation suggestions for the search input (HTMX partial)."""
    term = request.GET.get("zoek", "")
    orgs = find_orgs_by_abbreviation(term)
    return render(
        request,
        "parts/search_suggestions.html",
        {"org_suggestions": orgs, "search_term": term.strip()},
    )


def _facet_counts(filtered_qs, facet_lookup: str, group_field: str) -> Counter[int]:
    """Counts distinct groups per facet value, not placements.

    The list shows one card per colleague or per assignment, so a sidebar that
    counted placements would report a higher number than the list has cards.

    Re-keys on distinct placement ids first: projecting straight off a
    .distinct() queryset emits SELECT DISTINCT on the projected columns only,
    which drops rows that differ elsewhere.
    """
    rows = Placement.objects.filter(id__in=filtered_qs.values_list("id", flat=True))
    pairs = rows.values_list(facet_lookup, group_field).distinct()
    return Counter(fid for fid, _ in pairs if fid is not None)


def _org_counts_from_filtered(filtered_qs, model, org_lookup: str, group_field: str | None = None) -> Counter[int]:
    """Per-org counts from an already org-excluded, filter-applied queryset.

    Re-key on distinct row ids first: projecting the org id straight off a
    .distinct() queryset emits SELECT DISTINCT org_id and undercounts orgs
    shared by multiple rows. The base queryset already drops excluded orgs, so
    the exclusion is not re-applied here.

    With ``group_field`` the count is per distinct group (a colleague or an
    assignment) instead of per row, so it matches a list that shows one card
    per group.
    """
    rows = model.objects.filter(id__in=filtered_qs.values_list("id", flat=True))
    # Without group_field each row is its own group, so counting is per row.
    pairs = rows.values_list(org_lookup, group_field or "id").distinct()
    return Counter(oid for oid, _ in pairs if oid is not None)


def _get_top_org_options(
    selected_org_ids: set[int],
    org_counts: Counter[int],
    *,
    selected_self_ids: set[int] | None = None,
    selected_type_labels: set[str] | None = None,
    limit: int = 3,
) -> list[dict]:
    """Turns per-org ``org_counts`` + the current selections into the opdrachtgever
    quick checkbox options, ordered by count then label.

    Each option carries its own ``param`` (``org``, ``org_self`` or ``org_type``)
    so the sidebar quick row stays in sync with whatever was picked in the modal.
    The ``org`` group pads up to ``limit`` with the highest-count unselected orgs;
    self/type only appear when selected, having no top-N baseline.

    A selected option is always shown, appended below the top-N when it does not
    make the cut. The order never depends on selection — ticking an option
    jumping to the top felt jarring.
    """
    selected_self_ids = selected_self_ids or set()
    selected_type_labels = selected_type_labels or set()

    selected_ids = set(selected_org_ids)
    self_ids = set(selected_self_ids)

    # The top-N is fixed on count regardless of selection, so ticking an option
    # never displaces a visible one.
    top_n = [oid for oid, _ in org_counts.most_common(limit)]
    org_wanted = selected_ids | set(top_n)

    options: list[dict] = []

    # Iterating the rows (not the wanted ids) keeps an id that no longer exists
    # out of the options instead of rendering it with a "None" value.
    if org_wanted:
        options.extend(
            {
                "param": "org",
                "value": str(public_id),
                "label": label or f"Organisatie {org_id}",
                "count": org_counts.get(org_id, 0),
                "selected": org_id in selected_ids,
            }
            for org_id, label, public_id in OrganizationUnit.objects.filter(id__in=org_wanted).values_list(
                "id", "label", "public_id"
            )
        )

    if self_ids:
        options.extend(
            {
                "param": "org_self",
                "value": str(public_id),
                "label": f"{label or f'Organisatie {org_id}'} (direct)",
                "count": org_counts.get(org_id, 0),
                "selected": True,
            }
            for org_id, label, public_id in OrganizationUnit.objects.filter(id__in=self_ids).values_list(
                "id", "label", "public_id"
            )
        )

    options.extend(
        {
            "param": "org_type",
            "value": type_label,
            "label": ORG_TYPE_PLURAL.get(type_label, type_label),
            "count": 0,
            "selected": True,
        }
        for type_label in selected_type_labels
    )

    # Sorted on count then label, deliberately not on ``selected``: a just-ticked
    # option jumping to the top read as confusing.
    options.sort(key=lambda o: (-o["count"], o["label"]))
    return options


def _finalize_filter_groups(filter_groups: list[dict], *, top_n: int = 3) -> None:
    """Post-processes the select-multi groups in place for the top-N + "Meer" modal.

    Each group gets a unique ``group_id`` (the key the modal opens by),
    ``top_options`` (the ``top_n`` options by count, selected ones kept visible)
    and ``has_more``. The full alphabetical ``options`` list is kept for the modal.
    """
    label_seq = 0
    for group in filter_groups:
        if group.get("type") != "select-multi":
            continue
        # Unique key — "labels" repeats per category, so disambiguate.
        if group["name"] == "labels":
            group["group_id"] = f"labels-{label_seq}"
            label_seq += 1
        else:
            group["group_id"] = group["name"]

        real_options = [o for o in group["options"] if o.get("value")]
        selected = set(group.get("selected_values", []))
        by_count = sorted(real_options, key=lambda o: (-o.get("count", 0), o.get("label", "")))
        # The top-N is fixed on count regardless of selection; a selected option
        # outside it is appended rather than displacing one. Same rule as
        # _get_top_org_options.
        top = list(by_count[:top_n])
        top_values = {o["value"] for o in top}
        top.extend(o for o in by_count if o["value"] in selected and o["value"] not in top_values)
        group["top_options"] = top
        group["has_more"] = len(real_options) > len(top)


def _build_org_hierarchy(
    org_self_counts: Counter[int], excluded_org_ids: list[int], *, prune_empty: bool
) -> list[dict]:
    """Builds the grouped org tree hierarchy for the client modal."""
    all_orgs = list(
        OrganizationUnit.objects.exclude(id__in=excluded_org_ids).values(
            "id", "public_id", "parent_id", "name", "label", "abbreviations"
        )
    )

    units_by_id: dict[int, dict] = {}
    for org in all_orgs:
        org["children_data"] = []
        org["self_count"] = org_self_counts.get(org["id"], 0)
        org["total_count"] = 0
        units_by_id[org["id"]] = org

    roots: list[dict] = []
    for unit in units_by_id.values():
        parent_id = unit["parent_id"]
        if parent_id and parent_id in units_by_id:
            units_by_id[parent_id]["children_data"].append(unit)
        else:
            roots.append(unit)

    def compute_total(node: dict) -> int:
        total = node["self_count"]
        for child in node["children_data"]:
            total += compute_total(child)
        node["total_count"] = total
        return total

    for root in roots:
        compute_total(root)

    if prune_empty:

        def prune(node: dict) -> None:
            node["children_data"] = [c for c in node["children_data"] if c["total_count"] > 0]
            for child in node["children_data"]:
                prune(child)

        for root in roots:
            prune(root)
        roots = [r for r in roots if r["total_count"] > 0]

    def sort_key(node: dict) -> str:
        return node.get("label") or node.get("name") or ""

    def to_json(node: dict) -> dict:
        children_data = sorted(node["children_data"], key=sort_key)
        children_json = []
        has_children_with_placements = any(c["total_count"] > 0 for c in children_data)
        if node["self_count"] > 0 and has_children_with_placements:
            children_json.append(
                {
                    "id": f"self-{node['public_id']}",  # UUID -> str via f-string
                    "label": node["label"] or node["name"],
                    "abbreviations": node["abbreviations"] or [],
                    "self": True,
                    "nr_of_placements": node["self_count"],
                }
            )
        children_json.extend(to_json(child) for child in children_data)
        result: dict = {
            "id": str(node["public_id"]),
            "label": node["label"] or node["name"],
            "abbreviations": node["abbreviations"] or [],
            "nr_of_placements": node["total_count"],
        }
        if children_json:
            result["children"] = children_json
        return result

    # Group roots by OrganizationUnit type
    root_ids = {u["id"] for u in roots}
    type_links = (
        OrganizationUnit.organization_types.through.objects.filter(organizationunit_id__in=root_ids)
        .select_related("organizationtype")
        .values_list("organizationunit_id", "organizationtype__label")
    )
    root_types: dict[int, list[str]] = {}
    for unit_id, type_label in type_links:
        root_types.setdefault(unit_id, []).append(type_label)

    grouped: dict[str, list[dict]] = {}
    ungrouped: list[dict] = []
    for unit in roots:
        type_labels = root_types.get(unit["id"], [])
        if type_labels:
            for type_label in type_labels:
                grouped.setdefault(type_label, []).append(unit)
        else:
            ungrouped.append(unit)

    hierarchy = []
    for group_label in sorted(grouped.keys()):
        group_units = sorted(grouped[group_label], key=sort_key)
        total = sum(u["total_count"] for u in group_units)
        hierarchy.append(
            {
                "id": f"group-{group_label}",
                "label": ORG_TYPE_PLURAL.get(group_label, group_label),
                "nr_of_placements": total,
                "group": True,
                "children": [to_json(u) for u in group_units],
            }
        )
    hierarchy.extend(to_json(unit) for unit in sorted(ungrouped, key=sort_key))
    return hierarchy


def _build_current_selections(request) -> dict[str, str]:
    """Builds the current selections from the request params, for state restoration."""
    current_selections: dict[str, str] = {}

    org_public_ids = request.GET.getlist("org")
    for org in OrganizationUnit.objects.filter(public_id__in=parse_public_ids(org_public_ids)).values(
        "public_id", "label"
    ):
        current_selections[str(org["public_id"])] = org["label"]

    self_org_public_ids = request.GET.getlist("org_self")
    for org in OrganizationUnit.objects.filter(public_id__in=parse_public_ids(self_org_public_ids)).values(
        "public_id", "label"
    ):
        current_selections[f"self-{org['public_id']}"] = f'Direct onder "{org["label"]}"'

    for type_label in request.GET.getlist("org_type"):
        if type_label:
            current_selections[f"group-{type_label}"] = ORG_TYPE_PLURAL.get(type_label, type_label)

    return current_selections


def client_modal(request):
    """Returns the client tree selection modal (HTMX partial)."""
    excluded_org_ids = get_excluded_org_ids()
    count_mode = request.GET.get("count_mode")

    # count_mode "none" is the assignment-form org picker, not a filter list, so
    # the tree carries no counts (the whole org tree is shown, unpruned). The
    # filter modes count over the list's other active filters (sent along via
    # hx-include) so the tree matches the sidebar: borrow the list view's own
    # _apply_filters (single source of the predicates) rather than re-implementing
    # them here, which would drift.
    if count_mode == "none":
        org_self_counts = Counter()
    else:
        group_field = None
        if count_mode == "open_assignments":
            view = AssignmentListView()
            model, org_lookup = Assignment, "organizations__id"
        elif count_mode == "placements":
            view = PlacementListView()
            model, org_lookup = Placement, "service__assignment__organizations__id"
        else:
            return HttpResponseBadRequest("Onbekende count_mode")
        view.request = request
        # The tree counts the same groups the sidebar does, and the sidebar
        # follows ?weergave=. Without this the modal counted placements whatever
        # the view, so its numbers sat next to sidebar numbers that disagreed.
        if count_mode == "placements":
            group_field = view.GROUP_FIELD[view.active_view]
        filtered_qs = view._apply_filters(view._get_base_queryset(), exclude_filter="org").distinct()
        org_self_counts = _org_counts_from_filtered(filtered_qs, model, org_lookup, group_field=group_field)
    hierarchy = _build_org_hierarchy(org_self_counts, excluded_org_ids, prune_empty=count_mode != "none")
    current_selections = _build_current_selections(request)

    template = "parts/assignment_org_modal.html" if count_mode == "none" else "parts/client_modal.html"
    return render(
        request,
        template,
        {"hierarchy": hierarchy, "current_selections": current_selections},
    )


# ---------------------------------------------------------------------------
# Inline-edit view (generic HTMX endpoint).
# See ``features/inline-editing.md`` for the full contract.
# ---------------------------------------------------------------------------


def _spec_label(editable_set: type[EditableSet], spec: Editable | EditableGroup | EditableCollection) -> str:
    # Editable: explicit label → model field's verbose_name → attr name. Groups/Collections always carry a label.
    if isinstance(spec, EditableGroup | EditableCollection):
        return spec.label
    if spec.label:
        return spec.label
    if spec.model is not None and spec.field is not None:
        try:
            return spec.model._meta.get_field(spec.field).verbose_name
        except Exception:  # noqa: BLE001
            return spec.name or spec.field or ""
    return spec.name or ""


PERMISSION_DENIED_ALERT = {
    "kind": "warning",
    "message": "Je hebt geen rechten om dit veld te bewerken.",
}

CONCURRENCY_CONFLICT_ALERT = {
    "kind": "warning",
    "message": "Deze gegevens zijn ondertussen gewijzigd. "
    "Kies 'Opslaan' om je wijziging toch door te voeren, of 'Annuleren' om de gewijzigde gegevens over te nemen.",
}

CONFLICT_VALUE_MAX_LENGTH = 120


def _readable_current_value(obj, spec) -> str | None:
    """A short, human-readable form of a single field's current value, naming the
    concurrent change in the conflict warning. A group or collection has no single
    value, so this returns None and the caller uses the generic warning."""
    if not isinstance(spec, Editable):
        return None
    value = _current_value(obj, spec)
    # The audit timeline already renders this field for a human (the colleague's
    # name, not "Colleague object (3)"), so reuse that chain.
    if spec.audit_state:
        value = spec.audit_state(value)
    if spec.render_change:
        text = spec.render_change(value)
    elif isinstance(value, list):
        # A list on a scalar Editable is an M2M (e.g. labels); name the members.
        text = ", ".join(str(v) for v in value)
    else:
        text = "" if value is None else str(value)
    text = str(text).strip()
    if not text:
        return "geen"
    if len(text) > CONFLICT_VALUE_MAX_LENGTH:
        text = text[:CONFLICT_VALUE_MAX_LENGTH].rstrip() + "…"
    return text


def _concurrency_conflict_alert(editable_set, spec, obj) -> dict:
    """The conflict warning, naming the field and the concurrent value where one
    can be shown, so the user need not press Annuleren — losing their own input —
    just to find out what changed."""
    concurrent = _readable_current_value(obj, spec)
    if concurrent is None:
        return CONCURRENCY_CONFLICT_ALERT
    # The alert renders its message as HTML; ``format_html`` escapes both
    # interpolations, the value being user content.
    return {
        "kind": "warning",
        "message": format_html(
            "<strong>{}</strong> is ondertussen gewijzigd naar <strong>“{}”</strong>. "
            "Klik op 'Opslaan' om jouw wijziging alsnog door te voeren, "
            "of op 'Annuleren' om de wijziging over te nemen.",
            _spec_label(editable_set, spec),
            concurrent,
        ),
    }


def _edit_state(editable_set, spec, obj):
    """The values this edit is based on, in a JSON-serialisable shape.

    Only Editable/EditableGroup specs reach this: collections are read-only in
    the inline-edit engine and have no save path to guard with a token.
    """
    state = {}
    for e in resolve_editables(editable_set, spec):
        value = _current_value(obj, e)
        if isinstance(value, list):
            # Rows carry their own shape (dicts for organizations, models for
            # M2M), so let audit_state flatten them where it exists rather than
            # leaning on repr. Order-independent either way.
            value = e.audit_state(value) if e.audit_state else sorted(str(getattr(i, "pk", i)) for i in value)
        elif isinstance(value, Model):
            value = value.pk
        state[e.field or e.name] = value
    return state


def _hash_state(state) -> str:
    payload = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _concurrency_token(editable_set, spec, obj) -> str:
    """A short hash of the values this edit is based on, embedded in the form and
    re-checked under a row lock at save time. Differing tokens mean the values
    changed since rendering, and the save is rejected instead of overwriting."""
    return _hash_state(_edit_state(editable_set, spec, obj))


def _submitted_token(request) -> str:
    return request.POST.get("_concurrency_token", "")


def _has_concurrency_conflict(request, editable_set, spec, obj, *, state=None) -> bool:
    """Whether this POST was built on a stale view of ``obj``.

    Call inside the transaction holding the row lock, so the state read here is
    the state the save writes over. A missing token counts as a conflict: every
    form this endpoint renders carries one, so its absence means staleness cannot
    be established. ``state`` reuses a snapshot the caller already read.
    """
    submitted = _submitted_token(request)
    if not submitted:
        logger.warning(
            "Inline edit POST without a concurrency token; treated as a conflict (model=%s, editable=%s, pk=%s)",
            editable_set.model._meta.model_name,
            spec.name,
            obj.pk,
        )
        return True
    if state is None:
        state = _edit_state(editable_set, spec, obj)
    return submitted != _hash_state(state)


def _permission_denied(
    editable_set: type[EditableSet],
    spec: Editable | EditableGroup | EditableCollection,
    user,
    obj,
) -> dict | None:
    """Returns the denial alert when the user can't UPDATE this field, None when allowed.

    Lookup goes through the registry in ``wies.core.permissions``, where
    field-level rules win over the whole-object rule for the same model.
    """
    if not has_permission(Verb.UPDATE, obj, user, spec):
        return PERMISSION_DENIED_ALERT
    return None


def _resolve_display(obj, spec, editables) -> dict:
    # Returns {"template": path} to include a partial or {"text": str} for plain rendering.
    if spec.display is None:
        if isinstance(spec, EditableCollection):
            # Rarely useful, so a collection is expected to declare a display.
            return {"text": str(spec.initial(obj))}
        if isinstance(spec, EditableGroup):
            parts = []
            for e in editables:
                v = _current_value(obj, e)
                parts.append("" if v is None else str(v))
            return {"text": " · ".join(p for p in parts if p)}
        value = _current_value(obj, spec)
        return {"text": "" if value is None else str(value)}

    if callable(spec.display):
        return {"text": str(spec.display(obj))}

    if isinstance(spec.display, str) and spec.display.endswith(".html"):
        return {"template": spec.display}
    return {"text": str(spec.display)}


def _inline_edit_base_ctx(editable_set, spec, obj) -> dict:
    # Shared context for display/form/collection-form renders — target id, URL, label, obj, spec.
    model_label = editable_set.model._meta.model_name
    return {
        "target": f"inline-edit-{model_label}-{obj.public_id}-{spec.name}",
        "edit_url": reverse("inline-edit", args=[model_label, obj.public_id, spec.name]),
        "label": _spec_label(editable_set, spec),
        "obj": obj,
        "editable": spec,
    }


def _render_inline_edit_display(
    request,
    editable_set,
    spec,
    editables,
    obj,
    *,
    alert: dict | None = None,
    user_can_edit: bool | None = None,
    saved: bool = False,
) -> HttpResponse:
    # `saved=True` triggers the toast via HX-Trigger-After-Swap.
    # On denial, skip resolving the value: it can be heavy (the services
    # collection queries per row) and the partial handles an empty value fine.
    if alert is not None:
        display: dict = {"text": ""}
        value: object = None
    else:
        display = _resolve_display(obj, spec, editables)
        if isinstance(spec, EditableCollection):
            value = spec.initial(obj)
        elif isinstance(spec, Editable):
            value = _current_value(obj, spec)
        else:
            value = {e.field or e.name: _current_value(obj, e) for e in editables}
    extra = {}
    display_context = getattr(spec, "display_context", None)
    if alert is None and display_context is not None:
        extra = display_context(obj, request)
    ctx = {
        **_inline_edit_base_ctx(editable_set, spec, obj),
        "value": value,
        "display": display,
        "user_can_edit": (
            user_can_edit if user_can_edit is not None else has_permission(Verb.UPDATE, obj, request.user, spec)
        ),
        "hide_edit_button": getattr(spec, "hide_edit_button", False),
        "alert": alert,
        **extra,
        # Lets display.html put `autofocus` on the pencil after a save: htmx
        # focuses the first [autofocus] element in swapped-in content, and
        # without it focus drops to <body> with the button that held it.
        # After **extra, so a spec's display_context cannot override the flag
        # and lose focus without anything reporting it.
        "saved": saved,
    }
    response = render(request, "parts/inline_edit/display.html", ctx)
    if saved:
        # The label travels along so the toast names what was saved; in the
        # onboarding wizard several fields are saved in a row. A missing label
        # falls back to the generic text.
        response["HX-Trigger-After-Swap"] = json.dumps(
            {"inline-edit-saved": {"label": getattr(spec, "label", None) or ""}}
        )
    return response


def _render_inline_edit_form(
    request, editable_set, spec, editables, obj, form, *, alert: dict | None = None, token: str | None = None
) -> HttpResponse:
    # form.html always owns the form element and the concurrency token; a group's
    # ``form_template`` only replaces the field body, so it cannot drop either.
    ctx = {
        **_inline_edit_base_ctx(editable_set, spec, obj),
        "form": form,
        "editable": spec,
        "concurrency_token": token if token is not None else _concurrency_token(editable_set, spec, obj),
        "alert": alert,
    }
    return render(request, "parts/inline_edit/form.html", ctx)


def _handle_inline_edit_collection(request, editable_set, spec: EditableCollection, obj) -> HttpResponse:
    # Collections are read-only in the inline-edit engine: they render their
    # display, and their rows are edited through a dedicated flow (the team is
    # edited one member at a time via assignment_member_edit_view), not the
    # generic save path. A POST here is therefore never valid.
    if request.method == "POST":
        raise Http404("Collection is not editable")
    return _render_inline_edit_display(request, editable_set, spec, editables=[], obj=obj)


def _public_id_stub(model, public_id):
    """An unsaved instance carrying only ``public_id``, enough for the denial
    partial's target and edit_url. Lets a missing object render byte-identically
    to a forbidden one without a second DB round-trip."""
    stub = model()
    stub.public_id = public_id
    return stub


def _render_inline_edit_denial(request, editable_set, spec, public_id, obj=None, alert=None) -> HttpResponse:
    """The denial partial for an object the user may not edit or that is not there.
    Both render identically, so this endpoint can't be walked as an existence
    oracle over public_ids."""
    display_obj = obj if obj is not None else _public_id_stub(editable_set.model, public_id)
    editables_for_display: list[Editable] = (
        [] if isinstance(spec, EditableCollection) else resolve_editables(editable_set, spec)
    )
    return _render_inline_edit_display(
        request,
        editable_set,
        spec,
        editables_for_display,
        display_obj,
        alert=alert or PERMISSION_DENIED_ALERT,
        user_can_edit=False,
    )


def inline_edit_view(request, model_label, public_id, name):
    """Generic HTMX endpoint. See ``features/inline-editing.md`` for the full contract."""
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        raise Http404("Unknown model")
    spec = editable_set._editables.get(name) or editable_set.resolve_dynamic(name)
    if spec is None:
        raise Http404("Unknown editable")

    obj = editable_set.model.objects.filter(public_id=public_id).first()

    # A missing object and a forbidden one return the same denial partial, so
    # this endpoint can't be walked as an existence oracle.
    denial = _permission_denied(editable_set, spec, request.user, obj) if obj is not None else PERMISSION_DENIED_ALERT
    if denial:
        return _render_inline_edit_denial(request, editable_set, spec, public_id, obj=obj, alert=denial)

    if isinstance(spec, EditableCollection):
        return _handle_inline_edit_collection(request, editable_set, spec, obj)

    editables = resolve_editables(editable_set, spec)

    if request.method == "POST":
        form_cls, _ = build_form_class(
            editables,
            obj=obj,
            group_clean=getattr(spec, "clean", None),
        )
        form = form_cls(request.POST)
        if form.is_valid():
            conflict = False
            saved = False
            try:
                with transaction.atomic():
                    obj = editable_set.model.objects.select_for_update().get(pk=obj.pk)
                    conflict = _has_concurrency_conflict(request, editable_set, spec, obj)
                    if not conflict:
                        # Same save + audit as every other edit path, wrapped in the
                        # set's audit_mirror like save_placement_edit does.
                        mirror = editable_set.audit_mirror
                        with mirror(obj, request.user, request) if mirror else nullcontext():
                            saved = save_edit_specs(request, [(editable_set, spec, obj)], form.cleaned_data)
            except editable_set.model.DoesNotExist:
                # Deleted between the permission check and the lock; the same
                # denial partial keeps this indistinguishable from a 404 or 403.
                return _render_inline_edit_denial(request, editable_set, spec, public_id)
            if conflict:
                # Re-render the bound form, keeping the user's input: Opslaan
                # saves anyway, Annuleren adopts the changed data.
                return _render_inline_edit_form(
                    request,
                    editable_set,
                    spec,
                    editables,
                    obj,
                    form,
                    alert=_concurrency_conflict_alert(editable_set, spec, obj),
                )
            return _render_inline_edit_display(
                request,
                editable_set,
                spec,
                editables,
                obj,
                # The onboarding wizard submits every field on "Volgende", so an
                # untouched one would announce a save that did not happen.
                saved=saved,
            )
        # Keep the token this POST was built on: recomputing it would adopt a
        # change made meanwhile, and the corrected resubmit would overwrite it
        # without ever showing the conflict warning.
        return _render_inline_edit_form(
            request, editable_set, spec, editables, obj, form, token=_submitted_token(request)
        )

    if request.GET.get("cancel"):
        return _render_inline_edit_display(request, editable_set, spec, editables, obj)
    if request.GET.get("edit"):
        form_cls, initial = build_form_class(
            editables,
            obj=obj,
            group_clean=getattr(spec, "clean", None),
        )
        return _render_inline_edit_form(
            request,
            editable_set,
            spec,
            editables,
            obj,
            form_cls(initial=initial),
        )
    return _render_inline_edit_display(request, editable_set, spec, editables, obj)


# The placement panel edits three things spread over TWO models: Service.skill,
# Service.description and the Placement.period group. An EditableGroup belongs to
# one model and cannot cover that, so one form is built from the separate specs,
# reusing inline_edit_view's save and audit machinery per spec.


def _safe_return_path(raw: str | None, fallback: str) -> str:
    """Returns ``raw`` only when it is a path on this site, else the fallback.

    The value comes from a hidden input, so the client controls it. It ends up in
    HX-Push-Url — the address bar only, no navigation — but a protocol-relative
    "//host" would still display a foreign origin there.
    """
    if raw and raw.startswith("/") and not raw.startswith("//"):
        return raw
    return fallback


@require_POST
def placement_edit_view(request, public_id):
    """Saves the combined edit form of the placement child sheet.

    On success the client is sent back to the parent URL via HX-Location, which
    re-renders the panel through the normal panel route. Rendering the parent
    panel here is not possible: panel URLs are built from ``request.path``, which
    is the POST path, so its buttons would point back at this endpoint. On errors
    the form returns with messages. POST-only, so a GET can never show an empty
    form.
    """
    placement = (
        Placement.objects.select_related("colleague", "service__assignment", "service__skill")
        .filter(public_id=public_id)
        .first()
    )
    # _resolve_placement_panel enforces the visibility rules.
    if placement is None or _resolve_placement_panel(request, placement.public_id) is None:
        raise Http404("Unknown placement")

    # ?veld= limits the save to that one field, so a single-field sheet does not
    # silently carry the other fields along.
    only = request.GET.get("veld") or None
    specs = placement_edit_specs(placement, request.user, only=only)
    if not specs:
        return HttpResponseForbidden()

    fallback = _build_panel_url(request, plaatsing=placement.public_id)
    return_path = _safe_return_path(request.POST.get("terug_url"), fallback)

    form_cls, _ = build_combined_form_class(specs)
    form = form_cls(request.POST)
    if not form.is_valid():
        panel_data = _build_placement_edit_panel_data(placement, request, form=form, parent_url=return_path)
        return render(request, "parts/placement_edit_panel_content.html", {"panel_data": panel_data})

    save_placement_edit(request, placement, specs, form.cleaned_data)

    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


# Headings for the single-field sheet. Not derived from the spec labels as the
# assignment does: "Rol" covers two specs here, so the first one would decide the
# heading and that reads as half a title.
PLACEMENT_FIELD_HEADINGS = {"skill": "Rol bewerken", "period": "Periode bewerken"}


def _build_placement_edit_panel_data(placement, request, *, form=None, parent_url=None):
    """Context for the placement edit child sheet, or None without edit rights.

    The single source for this sheet: the open-GET path merges the returned dict
    onto the read-only panel, and the invalid-POST path renders it directly. Pass
    the bound ``form`` (and the sanitised ``parent_url``) to re-render a submitted
    form with its errors instead of a fresh one.
    """
    only = request.GET.get("veld") or None
    specs = placement_edit_specs(placement, request.user, only=only)
    if not specs:
        return None
    if form is None:
        form_cls, initial = build_combined_form_class(specs)
        form = form_cls(initial=initial)
    return {
        "panel_content_template": "parts/placement_edit_panel_content.html",
        "colleague": placement.colleague,
        "service": placement.service,
        "form": form,
        # Single-field sheet: the title names that field ("Periode bewerken").
        "edit_heading": PLACEMENT_FIELD_HEADINGS.get(only) if only else None,
        "parent_url": parent_url
        if parent_url is not None
        else _url_drop_params(request.path, request.GET, ("bewerken", "veld")),
        "edit_url": reverse("placement-edit", args=[placement.public_id]) + (f"?veld={only}" if only else ""),
    }


# Same pattern as the placement above: all assignment data in one form, built
# from the existing specs so save and audit behaviour stay identical to inline
# edit. The team form is a formset and does not fit in this flat form, so it has
# its own child sheet.


def _build_assignment_edit_panel_data(assignment, request, *, form=None, parent_url=None):
    """Context for the assignment edit child sheet, or None without edit rights.

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
        "edit_heading": f"{_spec_label(AssignmentEditables, specs[0][1])} wijzigen" if only else "Opdracht bewerken",
        "parent_url": parent_url
        if parent_url is not None
        else _url_drop_params(request.path, request.GET, ("bewerken", "veld")),
        "edit_url": reverse("assignment-edit", args=[assignment.public_id]) + (f"?veld={only}" if only else ""),
    }


@require_POST
def assignment_edit_view(request, public_id):
    """Saves the combined assignment form of the child sheet.

    Same contract as placement_edit_view: HX-Location back to the parent URL on
    success, the form with messages on errors. POST-only.
    """
    assignment = Assignment.objects.filter(public_id=public_id).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    # ?veld= limits the save to that one field, so a single-field sheet does not
    # silently carry the other fields along.
    only = request.GET.get("veld") or None
    specs = assignment_edit_specs(assignment, request.user, only=only)
    if not specs:
        return HttpResponseForbidden()

    fallback = _build_panel_url(request, opdracht=assignment.public_id)
    return_path = _safe_return_path(request.POST.get("terug_url"), fallback)

    form_cls, _ = build_combined_form_class(specs)
    form = form_cls(request.POST)
    if not form.is_valid():
        panel_data = _build_assignment_edit_panel_data(assignment, request, form=form, parent_url=return_path)
        return render(request, "parts/assignment_edit_panel_content.html", {"panel_data": panel_data})

    with transaction.atomic():
        save_edit_specs(request, specs, form.cleaned_data)

    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


@require_POST
def assignment_create_sheet(request):
    """Creates the assignment from the create sheet and sends the client to its
    panel via HX-Location. Roles are added afterwards in that panel. The empty
    form itself is rendered by AssignmentListView (?nieuwe-opdracht), so it lives
    on the list URL like the object panels and survives a reload."""
    from wies.core.services.assignments import (  # noqa: PLC0415 — avoids import cycle
        assignment_create_specs,
        create_assignment_from_specs,
    )

    if not request.user.has_perm("core.add_assignment"):
        return HttpResponseForbidden()

    specs = assignment_create_specs()
    form_cls, _ = build_combined_form_class(specs)
    return_to = _safe_return_path(request.POST.get("terug_url"), reverse("assignment-list"))

    form = form_cls(request.POST)
    if form.is_valid():
        with transaction.atomic():
            assignment = create_assignment_from_specs(form.cleaned_data)
        create_event(
            object_type="Assignment",
            action="create",
            source="user",
            object_id=assignment.id,
            user=request.user,
            request=request,
            context=_assignment_audit_snapshot(assignment),
        )
        sep = "&" if "?" in return_to else "?"
        path = f"{return_to}{sep}opdracht={assignment.public_id}"
        # base.html does not reload on the panel swap that follows HX-Location,
        # so assignment_panel_content.html swaps the banner in separately (OOB).
        messages.success(
            request,
            f'Opdracht "{assignment.name}" is aangemaakt.',
            extra_tags=f"link:{path}|Bekijk opdracht",
        )
        response = HttpResponse(status=204)
        response["HX-Location"] = json.dumps({"path": path, "target": "#side-panel-content", "swap": "innerHTML"})
        return response

    # Invalid: re-render the fragment with messages. parent_url is the sanitised
    # return address, so terug_url survives a failed submit.
    panel_data = _build_assignment_create_panel_data(request, form, parent_url=return_to)
    return render(request, "parts/assignment_create_panel_content.html", {"panel_data": panel_data})


def _build_assignment_member_panel_data(assignment, request, *, member_form=None, member_heading=None, parent_url=None):
    """Context for the team member child sheet, or None without rights.

    The single source for this sheet. On open (GET), ``?teamlid=<service public_id>``
    edits an existing member and ``nieuw-aanvraag``/``nieuw-ingevuld`` add a row
    with the status preselected — the form and heading are derived here. On an
    invalid POST, pass the bound ``member_form`` + its ``member_heading`` +
    sanitised ``parent_url`` to re-render; the ``teamlid`` lookup is then skipped.
    """
    from wies.core.editables.assignment import AssignmentEditables, _services_initial, skill_choices  # noqa: PLC0415
    from wies.core.forms import ServiceForm  # noqa: PLC0415 — avoids circular import

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return None

    if member_form is None:
        teamlid = request.GET.get("teamlid", "")
        if teamlid in ("nieuw-aanvraag", "nieuw-ingevuld"):
            filled = teamlid == "nieuw-ingevuld"
            initial_row = {"is_filled": "ingevuld" if filled else "aanvraag", "has_custom_period": True}
            member_heading = "Geplaatste consultant toevoegen" if filled else "Aanvraag toevoegen"
        else:
            # teamlid is a Service public_id (UUID string); match it against the row
            # identity. A non-matching or malformed value just misses → 404 panel.
            initial_row = next((r for r in _services_initial(assignment) if r["service_public_id"] == teamlid), None)
            if initial_row is None:
                return None
            member_heading = "Teamlid bewerken"
        member_form = ServiceForm(initial=initial_row, skill_choices=skill_choices())

    return {
        "panel_content_template": "parts/assignment_member_edit_panel_content.html",
        "assignment": assignment,
        "member_form": member_form,
        "member_heading": member_heading,
        "parent_url": parent_url
        if parent_url is not None
        else _url_drop_params(request.path, request.GET, ("teamlid",)),
        "member_edit_url": reverse("assignment-member-edit", args=[assignment.public_id]),
    }


@require_POST
def assignment_member_edit_view(request, public_id):
    """Saves one team member from the child sheet, editing or adding.

    The form posts a single formset row, which mutates exactly that one service
    (and its placement). Same contract as assignment_edit_view.
    """
    from wies.core.editables.assignment import AssignmentEditables, skill_choices  # noqa: PLC0415
    from wies.core.forms import ServiceForm  # noqa: PLC0415 — avoids circular import

    assignment = Assignment.objects.filter(public_id=public_id).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return HttpResponseForbidden()

    fallback = _build_panel_url(request, opdracht=assignment.public_id)
    return_path = _safe_return_path(request.POST.get("terug_url"), fallback)

    def rerender(form):
        panel_data = _build_assignment_member_panel_data(
            assignment,
            request,
            member_form=form,
            member_heading=request.POST.get("member_heading") or "Teamlid bewerken",
            parent_url=return_path,
        )
        return render(request, "parts/assignment_member_edit_panel_content.html", {"panel_data": panel_data})

    form = ServiceForm(request.POST, skill_choices=skill_choices())
    if not form.is_valid():
        return rerender(form)

    try:
        with member_audit_event(request, assignment):
            save_service_from_form(assignment, form)
    except ValidationError as exc:
        for message in exc.messages:
            form.add_error(None, message)
        return rerender(form)

    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


@require_POST
def assignment_member_delete_view(request, public_id, service_public_id):
    """Deletes one team member, after the confirmation dialog in the panel."""
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415

    assignment = Assignment.objects.filter(public_id=public_id).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return HttpResponseForbidden()

    # Resolved by public_id within this assignment, so a foreign id 404s rather
    # than emitting a no-op audit event.
    service = assignment.services.filter(public_id=service_public_id).first()
    if service is None:
        raise Http404("Unknown service")

    with member_audit_event(request, assignment):
        service.delete()

    return_path = _safe_return_path(
        request.POST.get("terug_url"), _build_panel_url(request, opdracht=assignment.public_id)
    )
    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response
