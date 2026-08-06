import hashlib
import json
import logging
import urllib.parse
from collections import Counter
from contextlib import nullcontext
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required, login_required, permission_required, user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core import management
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, Exists, F, Model, OuterRef, Prefetch, Q, Value, When
from django.db.models.functions import Concat
from django.forms.utils import ErrorList
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views.decorators.http import require_POST
from django.views.generic.list import ListView

from wies.core.editables import REGISTRY
from wies.core.inline_edit.audit import emit_inline_edit_audit_event
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
from wies.core.placement_visibility import LABELS, evaluate
from wies.rijksauth.services.usage import get_usage_stats

from .forms import (
    CATEGORY_COLOR_CHOICES,
    AssignmentCreateForm,
    LabelCategoryForm,
    LabelCategoryFormSet,
    LabelForm,
    ProfileLabelsForm,
    ProfileNameForm,
    ServiceFormSet,
    UserForm,
)
from .models import (
    Assignment,
    AssignmentNote,
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
)
from .permissions import is_staff_member
from .querysets import annotate_placement_dates, annotate_usage_counts
from .services.assignments import (
    apply_team_change,
    assignment_edit_specs,
    create_assignment_from_form,
    extract_services_data,
    initial_row_to_services_data,
)
from .services.events import create_event
from .services.inline_edit_save import save_edit_specs
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


def get_delete_context(delete_url_name, object_pk, object_name):
    """Helper function to generate delete context for modals"""
    return {
        "delete_url": reverse(delete_url_name, args=[object_pk]),
        "delete_confirm_message": f"Weet je zeker dat je {object_name} wilt verwijderen?",
    }


# Query params that drive the side panel; stripped when (re)building a page URL.
# ``bewerken`` zet het plaatsingspaneel in de bewerkstand (de child sheet).
PANEL_PARAMS = ("pagina", "collega", "opdracht", "plaatsing", "bewerken", "teamlid", "veld", "match", "notitie")


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


def _build_assignment_panel_data(assignment, request):
    """Shared helper to build assignment panel context data for both views."""
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
        # Same human label as the "Externe bron" row (get_source_display), so
        # the intro says "OTYS IIR", not the raw uppercased key "OTYS_IIR".
        "team_external_source": assignment.get_source_display() if assignment.source not in ("wies", "") else "",
        # Eén privacyzin boven de lijst in plaats van een noot per rij. De
        # formulering komt uit placement_visibility en is al op de kijker
        # toegesneden ("... jou en de Business Manager" / "... jou en de
        # consultant"), dus alleen de eerste letter hoeft mee te buigen.
        "team_privacy_note": next(
            (note[0].lower() + note[1:] for row in team_rows if (note := row.get("privacy_warning_text"))),
            "",
        ),
        "user_can_edit": bool(assignment_edit_specs(assignment, request.user)),
        "user_can_edit_team": has_permission(Verb.UPDATE, assignment, request.user, AssignmentEditables.services),
        "show_updates_tab": assignment.source != "otys_iir",
        "organization_count": assignment.organization_relations.count(),
        # Read-only weergavecontext: het paneel toont waarden direct (de per-veld
        # inline edit is vervangen door de bewerk-child-sheet).
        "organization_rows": _organizations_initial(assignment),
        "owner_display": _owner_display_context(assignment, request),
        "edit_panel_url": _build_panel_url(request, opdracht=assignment.id, bewerken=1),
        "member_add_aanvraag_url": _build_panel_url(request, opdracht=assignment.id, teamlid="nieuw-aanvraag"),
        "member_add_ingevuld_url": _build_panel_url(request, opdracht=assignment.id, teamlid="nieuw-ingevuld"),
        # PoC opmerkingen: rijen met een "…"-menu (net als het team). Toevoegen en
        # bewerken openen dezelfde child-sheet — nieuw via ?notitie=nieuw, één
        # bestaande via ?notitie=<id>. Alleen de BM van de opdracht mag beheren.
        "note_add_url": _build_panel_url(request, opdracht=assignment.id, notitie="nieuw"),
        "note_can_manage": _user_is_board_owner(request, assignment),
        "notes": list(assignment.notes.select_related("author")),
    }
    # Child sheets: ?bewerken= opent het gecombineerde opdrachtformulier,
    # ?teamlid= het formulier van één teamlid (of een nieuw lid via
    # nieuw-aanvraag / nieuw-ingevuld). Zonder rechten valt de parameter terug
    # op het leespaneel.
    if request.GET.get("bewerken"):
        edit_panel = _build_assignment_edit_panel_data(assignment, request)
        if edit_panel is not None:
            data.update(edit_panel)
    elif request.GET.get("teamlid"):
        member_panel = _build_assignment_member_panel_data(assignment, request)
        if member_panel is not None:
            data.update(member_panel)
    elif request.GET.get("match"):
        match_panel = _build_assignment_match_panel_data(assignment, request)
        if match_panel is not None:
            data.update(match_panel)
    elif request.GET.get("notitie"):
        note_panel = _build_assignment_note_panel_data(assignment, request)
        if note_panel is not None:
            data.update(note_panel)
    return data


def _merge_date_range(existing: dict, start, end):
    """Widen the date range of an assignment entry to include the given start/end."""
    if start and (existing["start_date"] is None or start < existing["start_date"]):
        existing["start_date"] = start
    if end and (existing["end_date"] is None or end > existing["end_date"]):
        existing["end_date"] = end


def _make_assignment_entry(name, aid, request, start_date=None, end_date=None, placement_id=None, **extra):
    """Build a standard assignment dict for panel display."""
    url = _build_panel_url(request, plaatsing=placement_id) if placement_id else _build_panel_url(request, opdracht=aid)
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
        viewer_is_assignment_bd = viewer is not None and owner_id is not None and owner_id == viewer.id
        start = placement.get("actual_start_date")
        end = placement.get("actual_end_date")
        # Active placements are public; ended or not-yet-started ones are only
        # visible to the placed colleague and the assignment's BM-owner.
        result = evaluate(start, end, colleague.id, viewer, viewer_is_assignment_bd, today)
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
                placement_id=placement["id"],
            )
        else:
            _merge_date_range(bucket[assignment_id], start, end)
        skill_name = placement["service__skill__name"]
        if skill_name:
            bucket[assignment_id]["tags"][skill_name] = placement["service__description"]

    # BM roles (active and ended)
    bm_assignments = Assignment.objects.filter(owner=colleague).values_list("id", "name", "start_date", "end_date")
    for assignment_id, name, start_date, end_date in bm_assignments:
        assignment_is_active = end_date is None or today <= end_date

        if assignment_is_active:
            if assignment_id not in active_by_id:
                active_by_id[assignment_id] = _make_assignment_entry(
                    name,
                    assignment_id,
                    request,
                    start_date=start_date,
                    end_date=end_date,
                )
            active_by_id[assignment_id]["tags"]["Business Manager"] = None
        elif viewer_is_colleague:
            # user can their own ended assignments as business manager
            # no clause for other business manager that can see this (only one)
            if assignment_id not in historical_by_id:
                historical_by_id[assignment_id] = _make_assignment_entry(
                    name,
                    assignment_id,
                    request,
                    start_date=start_date,
                    end_date=end_date,
                    tags={"Business Manager": None},
                    historical=True,
                    privacy_warning_text="Alleen zichtbaar voor jou en het team",
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
    """Shared helper to build colleague panel context data for both views."""
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
    """Build panel context for a single placement (colleague-on-assignment view).

    ``visibility`` (a PlacementVisibility) flags a non-active placement so the
    card shows the timing chip + privacy note. Access control is the caller's
    job — see ``_resolve_placement_panel``."""
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
        "assignment_url": _build_panel_url(request, opdracht=assignment.id),
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

    # De overige opdrachten van deze collega staan in hetzelfde paneel, zodat je
    # er niet voor hoeft door te klikken naar een tweede sheet. Dezelfde
    # zichtbaarheidsregels als het collegapaneel, want het is dezelfde bron.
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
        # Eén "Bewerken"-knop opent de child sheet; hij verschijnt alleen als er
        # ook echt iets te bewerken valt.
        "user_can_edit_details": bool(placement_edit_specs(placement, request.user)),
        "edit_panel_url": _build_panel_url(request, plaatsing=placement.id, bewerken=1),
    }


def _resolve_placement_panel(request, placement_id):
    """Fetch a placement for the side panel, enforcing the same rule as the team
    list: ended or not-yet-started placements are only shown to the placed
    colleague and the assignment's BM-owner. Returns panel data, or None when
    the placement does not exist or the viewer may not see it."""
    try:
        placement = Placement.objects.select_related("colleague", "service__assignment", "service__skill").get(
            id=placement_id
        )
    except Placement.DoesNotExist, ValueError:
        # ValueError: a non-numeric ?plaatsing= param fails PK coercion; treat
        # it the same as "not found" rather than letting it escape as a 500.
        return None
    assignment = placement.service.assignment
    viewer = getattr(request.user, "colleague", None)
    viewer_is_bm = viewer is not None and assignment.owner_id == viewer.id
    result = evaluate(
        placement.start_date, placement.end_date, placement.colleague_id, viewer, viewer_is_bm, timezone.now().date()
    )
    if not result.visible:
        return None
    panel_data = _build_placement_panel_data(placement, request, visibility=result)
    if request.GET.get("bewerken"):
        edit_panel = _build_placement_edit_panel_data(placement, request)
        # Zonder bewerkrechten valt ?bewerken= terug op het leespaneel in plaats
        # van een lege of verboden sheet.
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


ERRORS_PER_PAGE = 10


@staff_required
def staff_dashboard(request):
    # The error table is loaded separately via HTMX (see the error-table endpoint).
    return render(request, "staff_dashboard.html", {"usage": get_usage_stats()})


def _render_error_table(request, page_number):
    """Render the paginated error table fragment for the given page."""
    paginator = Paginator(ErrorEvent.objects.select_related("user"), ERRORS_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    def page_url(number):
        return f"{reverse('error-table')}?pagina={number}"

    context = {
        "object_list": page_obj.object_list,
        "page_obj": page_obj,
        "previous_page_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        "next_page_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
    }
    return render(request, "parts/error_table.html", context)


@staff_required
def error_table(request):
    """Paginated error table fragment, loaded via HTMX by the dashboard."""
    return _render_error_table(request, request.GET.get("pagina"))


@staff_required
def error_detail(request, pk):
    """One error (traceback etc.), staff-only.

    From the list on the dashboard this arrives over htmx and renders as a
    sheet; a direct link renders the full page. Both include the same body
    partial, so the two cannot drift.
    """
    error = get_object_or_404(ErrorEvent, pk=pk)
    if request.headers.get("HX-Request"):
        context = {"error": error, "pagina": request.GET.get("pagina", "1")}
        return render(request, "parts/error_detail_sheet.html", context)
    return render(request, "error_detail.html", {"error": error})


@staff_required
@require_POST
def delete_error(request, pk):
    """Delete a single handled error and return the refreshed current page of the table."""
    ErrorEvent.objects.filter(pk=pk).delete()
    response = _render_error_table(request, request.GET.get("pagina"))
    # Deleting happens from the detail sheet, which describes a row that is now
    # gone: close it along with the swap.
    response["HX-Trigger"] = "closeModal"
    return response


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
            messages.success(
                request,
                "Onboarding is gereset. De wizard verschijnt weer bij de volgende paginalading.",
            )
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
            if not groups:
                messages.info(request, "Geen dubbele opdrachten gevonden.")
            else:
                context["merge_groups"] = [
                    {
                        "name": group[0].name,
                        "owner": str(group[0].owner),
                        "count": len(group),
                        "target": group[0],
                        "duplicates": group[1:],
                    }
                    for group in groups
                ]
            return render(request, "staff_database.html", context)

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
                    total = sum(len(g) - 1 for g in groups)
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
                        f"{total} dubbele opdracht(en) samengevoegd in {len(groups)} groep(en).",
                    )

        return redirect("staff-database")

    return render(request, "staff_database.html", context)


def _get_top_org_options(
    count_mode: str,
    excluded_org_ids: list[int],
    selected_org_ids: set[str],
    *,
    viewer=None,
    selected_self_ids: set[str] | None = None,
    selected_type_labels: set[str] | None = None,
    org_counts: Counter[int] | None = None,
    limit: int = 3,
) -> list[dict]:
    """Return opdrachtgever quick checkbox options: the top-N by count, then any selection below it.

    Each option carries its own ``param`` (``org``, ``org_self`` or
    ``org_type``) so the sidebar quick row stays in sync with whatever was
    picked in the modal — including a "direct onder…" self-node (``org_self``)
    or an org-type group (``org_type``). Self/type only appear when actually
    selected (they have no top-N baseline).

    ``org_counts`` lets the caller pass filter-aware per-org counts (computed
    like rol/labels, excluding the org filter) so the numbers reflect the other
    active filters. When omitted, falls back to the global ``_get_org_counts``
    baseline (used by the modal, which has no other filter context).
    """
    selected_self_ids = selected_self_ids or set()
    selected_type_labels = selected_type_labels or set()

    if org_counts is None:
        org_counts = _get_org_counts(count_mode, excluded_org_ids, viewer)
    selected_ids = {int(x) for x in selected_org_ids if str(x).isdigit()}
    self_ids = {int(x) for x in selected_self_ids if str(x).isdigit()}

    # The head is the top-N by count and it stays put: aanvinken mag de rijen
    # eronder niet laten verspringen en mag er ook geen uit duwen. Een keuze die
    # buiten de kop valt komt eronder te staan, dus de lijst wordt langer.
    # Zelfde regel als _finalize_filter_groups voor de andere filtergroepen.
    labels = dict(OrganizationUnit.objects.filter(id__in=set(org_counts) | selected_ids).values_list("id", "label"))

    def _rank(org_id: int) -> tuple[int, str]:
        return (-org_counts.get(org_id, 0), labels.get(org_id) or f"Organisatie {org_id}")

    head_ids = sorted(org_counts, key=_rank)[:limit]
    org_wanted = head_ids + sorted(selected_ids - set(head_ids), key=_rank)

    options: list[dict] = []

    options.extend(
        {
            "param": "org",
            "value": str(org_id),
            "label": labels.get(org_id) or f"Organisatie {org_id}",
            "count": org_counts.get(org_id, 0),
            "selected": org_id in selected_ids,
        }
        for org_id in org_wanted
    )

    if self_ids:
        self_labels = dict(OrganizationUnit.objects.filter(id__in=self_ids).values_list("id", "label"))
        options.extend(
            {
                "param": "org_self",
                "value": str(org_id),
                "label": f"{self_labels.get(org_id) or f'Organisatie {org_id}'} (direct)",
                "count": org_counts.get(org_id, 0),
                "selected": True,
            }
            for org_id in self_ids
        )

    if selected_type_labels:
        # A type row covers whole roots, so its number is the subtree total the
        # modal shows for that group, not a per-org self-count. Building the tree
        # is only worth it when such a row is actually there, which is why this
        # sits behind the check.
        group_totals = {
            node["id"]: node["nr_of_placements"]
            for node in _build_org_hierarchy(org_counts, excluded_org_ids, prune_empty=True)
            if node.get("group")
        }
        options.extend(
            {
                "param": "org_type",
                "value": type_label,
                "label": ORG_TYPE_PLURAL.get(type_label, type_label),
                "count": group_totals.get(f"group-{type_label}", 0),
                "selected": True,
            }
            for type_label in selected_type_labels
        )

    return options


def _finalize_filter_groups(filter_groups: list[dict], *, top_n: int = 3) -> None:
    """Post-process select-multi groups in place for the top-N + "Meer" modal.

    For each ``select-multi`` group:
      - assigns a unique ``group_id`` (the modal opens by this key),
      - computes ``top_options``: the ``top_n`` options by count, in that order,
        plus any option selected outside that head appended below it,
      - sets ``has_more`` when there are more options than fit inline.
    The full ``options`` list is kept for the modal. Mutates in place.
    """
    label_seq = 0
    for group in filter_groups:
        if group.get("type") != "select-multi":
            continue
        # "labels" repeats per category, so disambiguate the key.
        if group["name"] == "labels":
            group["group_id"] = f"labels-{label_seq}"
            label_seq += 1
        else:
            group["group_id"] = group["name"]

        real_options = [o for o in group["options"] if o.get("value")]
        selected = set(group.get("selected_values", []))
        by_count = sorted(real_options, key=lambda o: o.get("count", 0), reverse=True)
        # The head is the top_n by count and it stays put: kiezen in de "Meer"-
        # sheet mag de rij eronder niet laten verspringen. Een keuze die buiten
        # de kop valt komt eronder te staan, dus de lijst wordt langer in plaats
        # van dat er een optie uit valt. De volledige lijst blijft in de sheet.
        head = by_count[:top_n]
        head_values = {o["value"] for o in head}
        extra_selected = [o for o in by_count[top_n:] if o["value"] in selected and o["value"] not in head_values]
        top = head + extra_selected
        group["top_options"] = top
        group["has_more"] = len(real_options) > len(top)


class PlacementListView(ListView):
    """View for placements table view with infinite scroll pagination"""

    model = Placement
    template_name = "placements.html"
    paginate_by = 60
    page_kwarg = "pagina"

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
            "skill": "service__skill__name",
            "end_date": "service__assignment__end_date",
        }

        order_param = self.request.GET.get("order")
        if order_param:
            descending = order_param.startswith("-")
            field_name = order_param.lstrip("-")
            order_by = order_mapping.get(field_name)
            if order_by:
                qs = qs.order_by(f"-{order_by}" if descending else order_by)

        # Active placements are public; ended ones are hidden from everyone;
        # not-yet-started ones only for the placed colleague and the BM-owner.
        qs = annotate_placement_dates(qs)
        viewer = getattr(self.request.user, "colleague", None)
        return filter_visible_placements(qs, timezone.now().date(), viewer)

    def _get_labels_by_category(self):
        """Parse selected label IDs grouped by category."""
        label_ids = [int(lid) for lid in self.request.GET.getlist("labels") if lid.isdigit()]
        if not label_ids:
            return {}
        labels_by_category = {}
        for label in Label.objects.filter(id__in=label_ids).values("id", "category_id"):
            labels_by_category.setdefault(label["category_id"], []).append(label["id"])
        return labels_by_category

    def _get_loopt_af_options(self, base_qs):
        """Build 'loopt af' filter options with cumulative counts."""
        today = timezone.now().date()
        filtered_qs = self._apply_filters(base_qs, exclude_filter="loopt_af").distinct()
        presets = [
            ("3m", "Binnen 3 maanden", 91),
            ("6m", "Binnen 6 maanden", 182),
        ]
        options = [{"value": "", "label": ""}]
        for value, label, days in presets:
            end_date = today + timedelta(days=days)
            count = filtered_qs.filter(service__assignment__end_date__lte=end_date).count()
            options.append({"value": value, "label": label, "count": count})
        # "Longer than 6 months"
        half_year = today + timedelta(days=182)
        count_beyond = filtered_qs.filter(service__assignment__end_date__gt=half_year).count()
        options.append({"value": "6m+", "label": "Langer dan 6 maanden", "count": count_beyond})
        return options

    def _apply_filters(self, qs, *, exclude_filter=None):
        """Apply all selection filters, optionally excluding one filter type.

        exclude_filter can be: "rol", "org", "loopt_af", or a category_id (int) for labels.
        """
        if exclude_filter != "rol":
            rol_filter = [x for x in self.request.GET.getlist("rol") if x.isdigit()]
            if rol_filter:
                qs = qs.filter(service__skill__id__in=rol_filter)

        if exclude_filter != "org":
            org_ids = [int(x) for x in self.request.GET.getlist("org") if x.isdigit()]
            org_self_ids = [int(x) for x in self.request.GET.getlist("org_self") if x.isdigit()]
            org_type_labels = [x for x in self.request.GET.getlist("org_type") if x]

            if org_ids or org_self_ids or org_type_labels:
                matching_ids: set[int] = set()
                if org_ids:
                    matching_ids |= get_org_descendant_ids(org_ids)
                if org_type_labels:
                    type_root_ids = list(
                        OrganizationUnit.objects.filter(organization_types__label__in=org_type_labels).values_list(
                            "id", flat=True
                        )
                    )
                    matching_ids |= get_org_descendant_ids(type_root_ids)
                if org_self_ids:
                    matching_ids |= set(org_self_ids)
                qs = qs.filter(service__assignment__organizations__id__in=matching_ids)

        # Label filter: OR within category, AND between categories
        labels_by_category = self._get_labels_by_category()
        for cat_id, cat_label_ids in labels_by_category.items():
            if exclude_filter != cat_id:
                qs = qs.filter(colleague__labels__id__in=cat_label_ids)

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
        """Apply filters to placements queryset - only show INGEVULD assignments, not LEAD"""
        qs = self._get_base_queryset()
        label_ids = [int(lid) for lid in self.request.GET.getlist("labels") if lid.isdigit()]
        if label_ids and not self._get_labels_by_category():
            return Placement.objects.none()
        qs = self._apply_filters(qs)
        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if "HX-Request" in self.request.headers:
            if self.request.GET.get("filter_modal"):
                return ["parts/filter_options_modal.html"]
            hx_target = self.request.headers.get("HX-Target", "")
            if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container"):
                # panel_data kiest zijn eigen sjabloon (o.a. de bewerk-child-sheet);
                # get_context_data heeft het hier al klaargezet.
                panel_data = getattr(self, "_panel_data", None)
                if panel_data:
                    return [panel_data["panel_content_template"]]
                return ["parts/placement_panel_content.html"]
            if self.request.GET.get("pagina"):
                return ["parts/placement_table_rows.html"]
            return ["parts/filter_and_table_container.html"]
        return ["placements.html"]

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)
        context["render_filter_fields_oob"] = "HX-Request" in self.request.headers

        # Add panel URLs to placement objects
        for placement in context["object_list"]:
            placement.panel_url = _build_panel_url(self.request, plaatsing=placement.id)

        context["filter_target_url"] = reverse("home")
        context["search_field"] = "zoek"
        context["search_placeholder"] = "Zoek op collega, opdracht of opdrachtgever..."
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters: dict = {}

        loopt_af_values = set(self.request.GET.getlist("loopt_af"))
        if loopt_af_values:
            active_filters["loopt_af"] = loopt_af_values

        # rol filter supports multi-select
        rol_filter = set()
        for rol_id in self.request.GET.getlist("rol"):
            if rol_id.isdigit():
                rol_filter.add(rol_id)
        if len(rol_filter) > 0:
            active_filters["rol"] = rol_filter

        # label filter supports multi-select
        label_filter = set()
        for label_id in self.request.GET.getlist("labels"):
            if label_id.isdigit():
                label_filter.add(label_id)
        if len(label_filter) > 0:
            active_filters["labels"] = label_filter

        # Organization filter (multi-select via modal)
        active_org_filter_count = 0
        org_filter = [x for x in self.request.GET.getlist("org") if x.isdigit()]
        org_self_filter = [x for x in self.request.GET.getlist("org_self") if x.isdigit()]
        org_type_filter = [x for x in self.request.GET.getlist("org_type") if x]
        if org_filter:
            active_filters["org"] = org_filter
            active_org_filter_count += len(org_filter)
        if org_self_filter:
            active_filters["org_self"] = org_self_filter
            active_org_filter_count += len(org_self_filter)
        if org_type_filter:
            active_filters["org_type"] = org_type_filter
            active_org_filter_count += len(org_type_filter)

        # Build chip display data for org filters
        org_chip_data: list[dict] = []
        if org_filter:
            org_labels = dict(
                OrganizationUnit.objects.filter(id__in=[int(x) for x in org_filter]).values_list("id", "label")
            )
            org_chip_data.extend(
                {
                    "param_name": "org",
                    "param_value": org_id,
                    "label": org_labels.get(int(org_id), f"Organisatie {org_id}"),
                }
                for org_id in org_filter
            )
        if org_self_filter:
            org_self_labels = dict(
                OrganizationUnit.objects.filter(id__in=[int(x) for x in org_self_filter]).values_list("id", "label")
            )
            for org_id in org_self_filter:
                base_label = org_self_labels.get(int(org_id), f"Organisatie {org_id}")
                org_chip_data.append(
                    {
                        "param_name": "org_self",
                        "param_value": org_id,
                        "label": f"{base_label} (direct)",
                    }
                )
        org_chip_data.extend(
            {
                "param_name": "org_type",
                "param_value": type_label,
                "label": ORG_TYPE_PLURAL.get(type_label, type_label),
            }
            for type_label in org_type_filter
        )

        # For each filter category, count on a queryset excluding that category's filter
        base_qs = self._get_base_queryset()

        label_filter_groups = []
        for category in LabelCategory.objects.all():
            # Count with all filters EXCEPT this label category
            cat_filtered_qs = self._apply_filters(base_qs, exclude_filter=category.id).distinct()
            cat_placement_qs = Placement.objects.filter(id__in=cat_filtered_qs.values_list("id", flat=True))
            cat_label_ids = cat_placement_qs.values_list("colleague__labels__id", flat=True)
            cat_label_counts = Counter(lid for lid in cat_label_ids if lid is not None)

            options = [{"value": "", "label": ""}]
            selected_values = []
            for label in Label.objects.filter(category=category):
                options.append(
                    {
                        "value": str(label.id),
                        "label": f"{label.name}",
                        "category_color": category.color,
                        "count": cat_label_counts.get(label.id, 0),
                    }
                )
                if str(label.id) in active_filters.get("labels", set()):
                    options[-1]["selected"] = True
                    selected_values.append(str(label.id))

            label_filter_groups.append(
                {
                    "type": "select-multi",
                    "name": "labels",
                    "label": category.name,
                    "options": options,
                    "selected_values": selected_values,
                }
            )

        # Skill/role counts: exclude role filter
        skill_filtered_qs = self._apply_filters(base_qs, exclude_filter="rol").distinct()
        skill_placement_qs = Placement.objects.filter(id__in=skill_filtered_qs.values_list("id", flat=True))
        skill_ids = skill_placement_qs.values_list("service__skill__id", flat=True)
        skill_counts = Counter(sid for sid in skill_ids if sid is not None)

        skill_options = [{"value": "", "label": ""}]
        skill_selected_values = []
        for skill in Skill.objects.order_by("name"):
            option = {"value": str(skill.id), "label": skill.name, "count": skill_counts.get(skill.id, 0)}
            if str(skill.id) in active_filters.get("rol", set()):
                option["selected"] = True
                skill_selected_values.append(str(skill.id))
            skill_options.append(option)

        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)
        context["active_org_filter_count"] = active_org_filter_count
        context["active_org_filter_label"] = org_chip_data[0]["label"] if len(org_chip_data) == 1 else ""
        context["org_chip_data"] = org_chip_data
        context["client_modal_count_mode"] = "placements"

        # TODO: this can be become an object to help defining correctly and performing extra preprocessing on context
        # introduce value_key, label_key:
        context["filter_groups"] = [
            {
                "type": "modal",
                "name": "organisatie",
                "label": "Opdrachtgever",
                "top_options": _get_top_org_options(
                    "placements",
                    get_excluded_org_ids(),
                    set(org_filter),
                    selected_self_ids=set(org_self_filter),
                    selected_type_labels=set(org_type_filter),
                ),
            },
            {
                "type": "select-multi",
                "name": "rol",
                "label": "Rol",
                "options": skill_options,
                "selected_values": skill_selected_values,
            },
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
            try:
                colleague = Colleague.objects.get(id=colleague_id)
                context["panel_data"] = _build_colleague_panel_data(colleague, self.request)
            except Colleague.DoesNotExist, ValueError:
                pass
        elif assignment_id:
            try:
                assignment = Assignment.objects.get(id=assignment_id)
                context["panel_data"] = _build_assignment_panel_data(assignment, self.request)
            except Assignment.DoesNotExist, ValueError:
                pass
        # get_context_data draait vóór get_template_names, dus die kan hier het
        # paneelsjabloon uit aflezen in plaats van het opnieuw af te leiden.
        self._panel_data = context.get("panel_data")
        return context


class AssignmentListView(ListView):
    """View for vacancy assignments displayed as cards with infinite scroll pagination"""

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
        qs = Assignment.objects.filter(has_unfilled_open_service).order_by(F("created_at").desc(nulls_last=True))
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
        if exclude_filter != "rol":
            rol_filter = [x for x in self.request.GET.getlist("rol") if x.isdigit()]
            if rol_filter:
                qs = qs.filter(
                    services__skill__id__in=rol_filter,
                    services__status="OPEN",
                    services__placements__isnull=True,
                )

        if exclude_filter != "org":
            org_ids = [int(x) for x in self.request.GET.getlist("org") if x.isdigit()]
            org_self_ids = [int(x) for x in self.request.GET.getlist("org_self") if x.isdigit()]
            org_type_labels = [x for x in self.request.GET.getlist("org_type") if x]
            if org_ids or org_self_ids or org_type_labels:
                matching_ids: set[int] = set()
                if org_ids:
                    matching_ids |= get_org_descendant_ids(org_ids)
                if org_type_labels:
                    type_root_ids = list(
                        OrganizationUnit.objects.filter(organization_types__label__in=org_type_labels).values_list(
                            "id", flat=True
                        )
                    )
                    matching_ids |= get_org_descendant_ids(type_root_ids)
                if org_self_ids:
                    matching_ids |= set(org_self_ids)
                qs = qs.filter(organizations__id__in=matching_ids)

        return qs

    def get_queryset(self):
        qs = self._get_base_queryset()
        qs = self._apply_filters(qs)
        return qs.distinct().prefetch_related(
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

    def get_template_names(self):
        if "HX-Request" in self.request.headers:
            if self.request.GET.get("filter_modal"):
                return ["parts/filter_options_modal.html"]
            hx_target = self.request.headers.get("HX-Target", "")
            if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container"):
                # Zie PlacementListView.get_template_names.
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
            assignment.panel_url = _build_panel_url(self.request, opdracht=assignment.id)
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

        # rol filter supports multi-select
        rol_filter = set()
        for rol_id in self.request.GET.getlist("rol"):
            if rol_id.isdigit():
                rol_filter.add(rol_id)
        if len(rol_filter) > 0:
            active_filters["rol"] = rol_filter

        # Skill/role counts: exclude role filter for cross-filtering
        base_qs = self._get_base_queryset()
        skill_filtered_qs = self._apply_filters(base_qs, exclude_filter="rol").distinct()
        skill_ids = skill_filtered_qs.values_list("services__skill__id", flat=True)
        skill_counts = Counter(sid for sid in skill_ids if sid is not None)

        skill_options = [{"value": "", "label": ""}]
        skill_selected_values = []
        for skill in Skill.objects.order_by("name"):
            option = {"value": str(skill.id), "label": skill.name, "count": skill_counts.get(skill.id, 0)}
            if str(skill.id) in active_filters.get("rol", set()):
                option["selected"] = True
                skill_selected_values.append(str(skill.id))
            skill_options.append(option)

        # Organization filter (multi-select via modal)
        active_org_filter_count = 0
        org_filter = [x for x in self.request.GET.getlist("org") if x.isdigit()]
        org_self_filter = [x for x in self.request.GET.getlist("org_self") if x.isdigit()]
        org_type_filter = [x for x in self.request.GET.getlist("org_type") if x]
        if org_filter:
            active_filters["org"] = org_filter
            active_org_filter_count += len(org_filter)
        if org_self_filter:
            active_filters["org_self"] = org_self_filter
            active_org_filter_count += len(org_self_filter)
        if org_type_filter:
            active_filters["org_type"] = org_type_filter
            active_org_filter_count += len(org_type_filter)

        # Build chip display data for org filters
        org_chip_data: list[dict] = []
        if org_filter:
            org_labels = dict(
                OrganizationUnit.objects.filter(id__in=[int(x) for x in org_filter]).values_list("id", "label")
            )
            org_chip_data.extend(
                {
                    "param_name": "org",
                    "param_value": org_id,
                    "label": org_labels.get(int(org_id), f"Organisatie {org_id}"),
                }
                for org_id in org_filter
            )
        if org_self_filter:
            org_self_labels = dict(
                OrganizationUnit.objects.filter(id__in=[int(x) for x in org_self_filter]).values_list("id", "label")
            )
            for org_id in org_self_filter:
                base_label = org_self_labels.get(int(org_id), f"Organisatie {org_id}")
                org_chip_data.append(
                    {
                        "param_name": "org_self",
                        "param_value": org_id,
                        "label": f"{base_label} (direct)",
                    }
                )
        org_chip_data.extend(
            {
                "param_name": "org_type",
                "param_value": type_label,
                "label": ORG_TYPE_PLURAL.get(type_label, type_label),
            }
            for type_label in org_type_filter
        )

        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)
        context["active_org_filter_count"] = active_org_filter_count
        context["active_org_filter_label"] = org_chip_data[0]["label"] if len(org_chip_data) == 1 else ""
        context["org_chip_data"] = org_chip_data
        context["client_modal_count_mode"] = "open_assignments"

        context["filter_groups"] = [
            {
                "type": "modal",
                "name": "organisatie",
                "label": "Opdrachtgever",
                "top_options": _get_top_org_options(
                    "open_assignments",
                    get_excluded_org_ids(),
                    set(org_filter),
                    selected_self_ids=set(org_self_filter),
                    selected_type_labels=set(org_type_filter),
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

        # Primary button for assignment creation (BDM permission). Opent de
        # aanmaak-sheet in het zijpaneel; ?terug= laat de sheet na aanmaken het
        # nieuwe opdrachtpaneel op deze pagina openen.
        if self.request.user.has_perm("core.add_assignment"):
            context["primary_button"] = {
                "button_text": "Opdracht invoeren",
                "attrs": {
                    "hx-get": reverse("assignment-create-sheet") + "?terug=" + reverse("assignment-list"),
                    "hx-target": "#side-panel-content",
                    "hx-swap": "innerHTML",
                    "hx-push-url": "false",
                },
            }

        # Side panel
        placement_id = self.request.GET.get("plaatsing")
        colleague_id = self.request.GET.get("collega")
        assignment_id = self.request.GET.get("opdracht")

        if placement_id:
            panel_data = _resolve_placement_panel(self.request, placement_id)
            if panel_data is not None:
                context["panel_data"] = panel_data
        elif colleague_id and not assignment_id:
            try:
                colleague = Colleague.objects.get(id=colleague_id)
                context["panel_data"] = _build_colleague_panel_data(colleague, self.request)
            except Colleague.DoesNotExist, ValueError:
                pass
        elif assignment_id:
            try:
                assignment = Assignment.objects.select_related("owner").get(id=assignment_id)
                context["panel_data"] = _build_assignment_panel_data(assignment, self.request)
            except Assignment.DoesNotExist, ValueError:
                pass

        # Zie PlacementListView.get_context_data: get_template_names leest dit.
        self._panel_data = context.get("panel_data")
        return context


class UserListView(PermissionRequiredMixin, ListView):
    """View for user list with filtering and infinite scroll pagination"""

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

    def _get_labels_by_category(self):
        """Parse selected label IDs grouped by category."""
        label_ids = [int(lid) for lid in self.request.GET.getlist("labels") if lid.isdigit()]
        if not label_ids:
            return {}
        labels_by_category = {}
        for label in Label.objects.filter(id__in=label_ids).values("id", "category_id"):
            labels_by_category.setdefault(label["category_id"], []).append(label["id"])
        return labels_by_category

    def _apply_filters(self, qs, *, exclude_filter=None):
        """Apply all selection filters, optionally excluding one filter type.

        exclude_filter can be: "rol", or a category_id (int) for labels.
        """
        # Label filter: OR within category, AND between categories
        labels_by_category = self._get_labels_by_category()
        for cat_id, cat_label_ids in labels_by_category.items():
            if exclude_filter != cat_id:
                qs = qs.filter(colleague__labels__id__in=cat_label_ids)

        # Role filter
        if exclude_filter != "rol":
            role_filter = self.request.GET.get("rol")
            if role_filter and role_filter.isdigit():
                qs = qs.filter(groups__id=role_filter)

        return qs

    def get_queryset(self):
        """Apply filters to users queryset - exclude superusers"""
        qs = self._get_base_queryset()
        label_ids = [int(lid) for lid in self.request.GET.getlist("labels") if lid.isdigit()]
        if label_ids and not self._get_labels_by_category():
            return User.objects.none()
        qs = self._apply_filters(qs)
        return qs.distinct()

    def _panel_colleague(self):
        """The colleague whose panel is requested via ?collega=, if any."""
        colleague_id = self.request.GET.get("collega")
        if not colleague_id or not colleague_id.isdigit():
            return None
        return Colleague.objects.filter(id=colleague_id).first()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if "HX-Request" in self.request.headers:
            if self.request.headers.get("HX-Target") == "side-panel-content":
                return ["parts/colleague_panel_content.html"]
            # If paginating, return only rows
            if self.request.GET.get("pagina"):
                return ["parts/user_table_rows.html"]
            # Otherwise, return full table (for filter changes)
            return ["parts/user_table.html"]
        return ["user_admin.html"]

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)

        # Het profielpaneel hangt aan deze pagina, zodat "Profiel bekijken" in
        # het rijmenu de sheet hier opent in plaats van naar de lijstpagina te
        # springen. Bij een directe load rendert het paneel server-side mee.
        panel_colleague = self._panel_colleague()
        context["panel_data"] = _build_colleague_panel_data(panel_colleague, self.request) if panel_colleague else None

        context["search_field"] = "zoek"
        context["search_placeholder"] = "Zoek op naam of email..."
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters = {}

        # label filter supports multi-select
        label_filter = set()
        for label_id in self.request.GET.getlist("labels"):
            if label_id.isdigit():
                label_filter.add(label_id)
        if len(label_filter) > 0:
            active_filters["labels"] = label_filter

        role_filter = self.request.GET.get("rol")
        if role_filter and role_filter.isdigit():
            active_filters["rol"] = role_filter

        # For each label category, count on queryset excluding that category's filter
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
                        "value": str(label.id),
                        "label": f"{label.name}",
                        "count": cat_label_counts.get(label.id, 0),
                    }
                )
                if str(label.id) in active_filters.get("labels", set()):
                    options[-1]["selected"] = True
                    selected_values.append(str(label.id))

            label_filter_groups.append(
                {
                    "type": "select-multi",
                    "name": "labels",
                    "label": category.name,
                    "options": options,
                    "selected_values": selected_values,
                }
            )

        role_options = [
            {"value": "", "label": "Alle rollen"},
        ]
        role_value = ""
        for group in Group.objects.all().order_by("name"):
            role_options.append({"value": str(group.id), "label": group.name})
            if active_filters.get("rol") == str(group.id):
                role_options[-1]["selected"] = True
                role_value = str(group.id)

        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)

        context["filter_groups"] = [
            {
                "type": "select",
                "name": "rol",
                "label": "Rol",
                "options": role_options,
                "value": role_value,
            },
            *label_filter_groups,
        ]

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
    """Handle user creation - GET returns form modal, POST processes creation"""

    form_post_url = reverse("user-create")
    modal_title = "Nieuwe gebruiker"
    element_id = "userFormModal"

    if request.method == "GET":
        # Return modal HTML with empty UserForm
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
                request=request,
            )
            # For HTMX requests, use HX-Redirect header to force full page redirect
            # For standard form posts, use normal redirect
            if "HX-Request" in request.headers:
                response = HttpResponse(status=200)
                response["HX-Redirect"] = reverse("admin-users")
                return response
            return redirect(reverse("admin-users"))
        # Re-render form with errors (stays in modal with HTMX)
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
def user_edit(request, pk):
    """Handle user editing - GET returns form modal with user data, POST processes update"""
    edited_user = get_object_or_404(User, pk=pk, is_superuser=False)
    form_post_url = reverse("user-edit", args=[edited_user.id])
    modal_title = "Gebruiker bewerken"
    element_id = "userFormModal"

    if request.method == "GET":
        # Return modal HTML with UserForm populated with user data
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
                request=request,
            )
            # For HTMX requests, use HX-Redirect header to force full page redirect
            # For standard form posts, use normal redirect
            if "HX-Request" in request.headers:
                response = HttpResponse(status=200)
                response["HX-Redirect"] = reverse("admin-users")
                return response
            return redirect(reverse("admin-users"))
        # Re-render form with errors (stays in modal with HTMX)
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
def user_delete(request, pk):
    """Handle user deletion"""
    user = get_object_or_404(User, pk=pk, is_superuser=False)

    if request.method == "GET":
        # Show delete confirmation modal
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
                "form_post_url": reverse("user-delete", kwargs={"pk": pk}),
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
        user.delete()
        create_event(
            object_type="User",
            action="delete",
            source="user",
            object_id=pk,
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
    """
    Import users from a CSV file.

    GET: Display the import main form
    POST: Process the uploaded CSV file and create users

    For expected CSV format, see create_users_from_csv function
    """
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

        # Return results in the form
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
    """
    Import assignments from a CSV file.

    GET: Display the import form
    POST: Process the uploaded CSV file and create assignments
          (with related services, placements, colleagues, and skills)

    For expected CSV format, see create_assignment_from_csv function
    """
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

        # Return results in the form
        return render(request, "assignment_import.html", {"result": result})
    return HttpResponse(status=405)


@permission_required("core.view_organizationunit", raise_exception=True)
def organization_admin(request):
    """Show all organization units in a collapsible tree, grouped by type. Only available in DEBUG mode."""
    if not settings.DEBUG:
        raise Http404
    rows = OrganizationUnit.objects.values("id", "parent_id", "name", "label", "abbreviations", "end_date")

    # Index all units as lightweight dicts
    today = timezone.now().date()
    units_by_id: dict[int, dict] = {}
    for row in rows:
        row["is_inactive"] = row["end_date"] is not None and row["end_date"] <= today
        row["tree_children"] = []
        units_by_id[row["id"]] = row

    # Build tree
    roots: list[dict] = []
    for unit in units_by_id.values():
        parent_id = unit["parent_id"]
        if parent_id and parent_id in units_by_id:
            units_by_id[parent_id]["tree_children"].append(unit)
        else:
            roots.append(unit)

    # Sort children at every level
    def sort_key(u):
        return u["label"] or u["name"]

    for unit in units_by_id.values():
        unit["tree_children"].sort(key=sort_key)
    roots.sort(key=sort_key)

    # Get organization types for root nodes only (via M2M through table)
    root_ids = {u["id"] for u in roots}
    type_links = (
        OrganizationUnit.organization_types.through.objects.filter(organizationunit_id__in=root_ids)
        .select_related("organizationtype")
        .values_list("organizationunit_id", "organizationtype__label")
    )
    root_types: dict[int, list[str]] = {}
    for unit_id, type_label in type_links:
        root_types.setdefault(unit_id, []).append(type_label)

    # Group roots by organization type
    grouped: dict[str, list[dict]] = {}
    ungrouped: list[dict] = []
    for unit in roots:
        type_labels = root_types.get(unit["id"], [])
        if type_labels:
            for type_label in type_labels:
                grouped.setdefault(type_label, []).append(unit)
        else:
            ungrouped.append(unit)

    # Sort groups alphabetically, put ungrouped last
    type_groups = [(ORG_TYPE_PLURAL.get(name, name), units) for name, units in sorted(grouped.items())]
    if ungrouped:
        type_groups.append(("Overig", ungrouped))

    return render(request, "organization_admin.html", {"type_groups": type_groups})


@permission_required("core.view_labelcategory", raise_exception=True)
def label_admin(request):
    """Main label admin pag"""
    categories = annotate_usage_counts(LabelCategory.objects.all())
    return render(request, "label_admin.html", {"categories": categories})


@permission_required("core.change_labelcategory", raise_exception=True)
def label_category_create(request):
    """
    Returns a partial html page, to be used with htmx
    """

    """Create a new label category"""
    form_post_url = reverse("label-category-create")
    modal_title = "Nieuwe categorie"
    element_id = "labelFormModal"
    form_button_label = "Toevoegen"

    if request.method == "GET":
        form = LabelCategoryForm()
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
        form = LabelCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Categorie '{form.cleaned_data['name']}' succesvol aangemaakt")
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("label-admin")
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


@permission_required("core.change_labelcategory", raise_exception=True)
def label_category_edit(request, pk):
    """
    Edit a label category
    Returns a partial html page, to be used with htmx
    """

    category = get_object_or_404(LabelCategory, pk=pk)
    form_post_url = reverse("label-category-edit", kwargs={"pk": pk})
    modal_title = f"Bewerk categorie: {category.name}"
    form_button_label = "Opslaan"
    element_id = "labelFormModal"

    if request.method == "GET":
        form = LabelCategoryForm(instance=category)
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
                **get_delete_context("label-category-delete", category.pk, f"categorie '{category.name}'"),
            },
        )
    if request.method == "POST":
        form = LabelCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("label-admin")
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
                **get_delete_context("label-category-delete", category.pk, f"categorie '{category.name}'"),
            },
        )
    return None


@login_required
@require_POST
def user_theme(request):
    """Store the display preference of the logged-in user.

    The choice lives on the user rather than in the browser, so it travels to
    every device and base.html can render it server-side as data-scheme: the
    screen is correct on first paint, without a flash while loading.
    """
    theme = request.POST.get("theme", "")
    if theme not in User.Theme.values:
        return HttpResponseBadRequest("Onbekende weergave")
    request.user.theme = theme
    request.user.save(update_fields=["theme"])
    return HttpResponse(status=204)


@login_required
def profile_name_edit(request):
    """Voor- en achternaam van de ingelogde gebruiker, in één sheet.

    Alleen het eigen profiel: de pagina toont ``request.user``, dus er is niets
    te kiezen. Opslaan loopt via de Editable-save van elk veld, zodat de naam op
    de gekoppelde Colleague meebeweegt zoals bij de inline-edit.
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

    Onboarding asks the same question with the same token fields, but there
    each field saves itself when the step is left. Here the three land
    together under one "Opslaan", which is what a sheet promises.
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
    """Alle categorieën in één sheet: hernoemen, kleur kiezen, rijen toevoegen.

    Hernoemen en nieuwe rijen zijn gestapeld tot "Opslaan"; verwijderen loopt
    via de bevestigingsdialoog en gaat meteen, omdat het gevolgen heeft voor de
    labels eronder (die verhuizen naar de vangnetcategorie).
    """
    queryset = LabelCategory.objects.all()

    if request.method == "POST":
        formset = LabelCategoryFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            response = HttpResponse(status=200)
            response["HX-Redirect"] = reverse("label-admin")
            return response
    else:
        formset = LabelCategoryFormSet(queryset=queryset)

    if formset.forms:
        formset.forms[0].fields["name"].widget.attrs["autofocus"] = True

    return render(
        request,
        "parts/label_category_manage_sheet.html",
        {
            "formset": formset,
            "color_choices": CATEGORY_COLOR_CHOICES,
            "form_post_url": reverse("label-category-manage"),
        },
    )


@permission_required("core.change_label", raise_exception=True)
def label_form(request, pk=None):
    """Eén sheet voor toevoegen én bewerken van een label (categorie + naam)."""
    label = get_object_or_404(Label, pk=pk) if pk else None
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

    # Een fout ververst alleen de inhoud: de sheet staat al open, en de hele
    # sheet opnieuw sturen zou er een tweede overheen zetten.
    template = "parts/label_form_body.html" if invalid_post else "parts/label_form_sheet.html"

    return render(
        request,
        template,
        {
            "content": form,
            "modal_title": "Label bewerken" if is_edit else "Label toevoegen",
            "form_button_label": "Opslaan" if is_edit else "Voeg label toe",
            "form_post_url": (
                reverse("label-form-edit", kwargs={"pk": label.pk}) if is_edit else reverse("label-form-create")
            ),
            "modal_element_id": "labelFormModal",
        },
    )


def _move_labels_to_fallback(category):
    """Re-home a category's labels before it is deleted.

    Returns the catch-all category, or None when there was nothing to move (or
    the catch-all itself is being deleted). Labels are unique per category, so a
    name that already exists in the catch-all is merged: the colleagues of the
    duplicate move to the surviving label and the duplicate goes.
    """
    labels = list(category.labels.all())
    if not labels:
        return None

    fallback = LabelCategory.fallback()
    if fallback.pk == category.pk:
        return None

    for label in labels:
        existing = Label.objects.filter(category=fallback, name=label.name).exclude(pk=label.pk).first()
        if existing is None:
            label.category = fallback
            label.save(update_fields=["category"])
        else:
            existing.colleagues.add(*label.colleagues.all())
            label.delete()
    return fallback


def _category_delete_warning(category):
    """The confirmation text, which differs for the catch-all itself."""
    count = category.labels.count()
    if count == 0:
        return f"Weet je zeker dat je categorie '{category.name}' wilt verwijderen?"
    if category.name == LabelCategory.FALLBACK_NAME:
        return (
            f"Weet je zeker dat je categorie '{category.name}' wilt verwijderen? "
            f"De {count} labels erin worden verwijderd, ook bij de collega's die ze hebben."
        )
    return (
        f"Weet je zeker dat je categorie '{category.name}' wilt verwijderen? "
        f"De {count} labels erin verhuizen naar '{LabelCategory.FALLBACK_NAME}'."
    )


@permission_required("core.delete_labelcategory", raise_exception=True)
def label_category_delete(request, pk):
    """
    To be used with htmx
    """
    category = get_object_or_404(LabelCategory, pk=pk)
    if request.method == "GET":
        # Een dialoog, geen sheet: de vraag komt uit de beheersheet en die moet
        # zichtbaar blijven staan achter de bevestiging.
        has_labels = category.labels.exists()
        is_fallback = category.name == LabelCategory.FALLBACK_NAME
        return render(
            request,
            "parts/confirm_delete_modal.html",
            {
                "dialog_text": "Categorie verwijderen?",
                "dialog_supporting": _category_delete_warning(category),
                "confirm_label": "Verwijder categorie",
                "cancel_label": "Behoud categorie",
                "form_post_url": reverse("label-category-delete", kwargs={"pk": pk}),
                # De labels weggooien is een aparte keuze, en alleen zinnig als
                # er labels zijn die anders zouden verhuizen.
                "extra_confirm_label": ("Verwijder categorie en de labels" if has_labels and not is_fallback else ""),
                "extra_confirm_vals": '{"labels_verwijderen": "1"}',
            },
        )
    if request.method == "POST":
        category_name = category.name  # Store name before deleting
        # Zonder deze vlag verhuizen de labels naar het vangnet; met de vlag
        # gaan ze mee met de categorie (cascade).
        drop_labels = request.POST.get("labels_verwijderen") == "1"
        moved_to = None if drop_labels else _move_labels_to_fallback(category)
        category.delete()
        if moved_to is not None:
            messages.success(
                request,
                f"Categorie '{category_name}' verwijderd; de labels staan nu onder '{moved_to.name}'",
            )
        else:
            messages.success(request, f"Categorie '{category_name}' succesvol verwijderd")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("label-admin")
        return response
    return HttpResponse(status=405)


@permission_required("core.change_label", raise_exception=True)
def label_edit(request, pk):
    """
    Returns a partial html page, to be used with htmx
    """
    label = get_object_or_404(Label, pk=pk)
    category = label.category
    form_post_url = reverse("label-edit", kwargs={"pk": pk})
    modal_title = f"Bewerk label: {label.name}"
    form_button_label = "Opslaan"
    element_id = "labelFormModal"

    if request.method == "GET":
        form = LabelForm(instance=label, category_id=category.id)
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
                **get_delete_context("label-delete", label.pk, f"label '{label.name}'"),
            },
        )
    if request.method == "POST":
        form = LabelForm(request.POST, instance=label)
        if form.is_valid():
            form.save()

            category_qs = LabelCategory.objects.filter(id=category.id)
            category = annotate_usage_counts(category_qs).get()

            response = render(request, "parts/label_category.html", {"category": category})
            response["HX-Retarget"] = f"#label_category_{category.id}"
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
                **get_delete_context("label-delete", label.pk, f"label '{label.name}'"),
            },
        )
    return None


@permission_required("core.delete_label", raise_exception=True)
def label_delete(request, pk):
    """
    To be used with htmx
    """

    label = get_object_or_404(Label, pk=pk)
    category = label.category

    label_use_count = label.colleagues.count()

    if request.method == "GET":
        return render(
            request,
            "parts/generic_form_modal.html",
            {
                "modal_title": f"Verwijder label: {label.name}",
                "warning_modal": True,
                "modal_element_id": "labelFormModal",
                "target_element_id": f"label_category_{category.id}",
                "delete_warning": (
                    f"Weet je zeker dat je dit label wilt verwijderen? Het wordt gebruikt op {label_use_count} plekken."
                ),
                "form_post_url": reverse("label-delete", kwargs={"pk": pk}),
                "form_button_label": "Verwijderen",
            },
        )
    if request.method == "POST":
        label.delete()

        category_qs = LabelCategory.objects.filter(id=category.id)
        category = annotate_usage_counts(category_qs).get()

        response = render(
            request,
            "parts/label_category.html",
            {
                "category": category,
            },
        )
        response["HX-Trigger"] = "closeModal"
        return response

    return HttpResponse(status=405)


def assignment_events_partial(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
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


HET_FIELD_LABELS = {"team", "merk", "thema", "budget", "onderwerp", "contract", "tarief"}


def _field_phrase(label: str) -> str:
    """Turn a field label into something that reads as part of a sentence:
    "Beschrijving" -> "de beschrijving", "Team" -> "het team". A label with an
    inner capital is a name, not a common noun ("Business Manager", "E-mail
    (ODI)"), so its casing is left alone."""
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
    """Phrase the event as one running sentence, commit-message style:
    "Bart van de Biezen heeft AI Consultant (open) toegevoegd en Process
    Analyst (Anke Jacobs) naar Process Analyst (open) gewijzigd." Long values
    (textarea's, toelichtingen) stay out of the sentence; the template renders
    them as Van/Naar blocks underneath. Requires _attach_audit_render_data to
    have run first (render_kind, formatted_old/new, diff_entries)."""
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


def _attach_audit_render_data(event, obj, request) -> bool:
    """Prepare `event` for the timeline. False means the viewer may see nothing
    of it and it must not be rendered at all."""
    event.render_kind = "text"
    event.diff_entries = None
    event.formatted_old = event.context.get("old_value")
    event.formatted_new = event.context.get("new_value")

    # Delete events are kept for the audit trail but never rendered here — a
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

    # Een textarea krijgt het Van/Naar-blok, behalve als hij maar één regel hoog
    # is: dat is een gewoon tekstveld dat alleen mag doorlopen (de opdrachtnaam),
    # en dan leest de zin "van X naar Y" prettiger dan twee blokken.
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
        # Legacy events can have a stored shape the current render_change no
        # longer accepts. Fall through to the raw context values set at the
        # top of this function so the timeline row still renders.
        logger.warning(
            "Audit render_change failed for Event id=%s field=%s; falling back to raw context",
            event.id,
            event.context.get("field_name"),
            exc_info=True,
        )
    return True


def assignment_delete(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
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
                "form_post_url": reverse("assignment-delete", kwargs={"pk": pk}),
            },
        )
    if request.method == "POST":
        name = assignment.name
        # Snapshot related rows before they cascade away.
        context = _assignment_audit_snapshot(assignment)
        # Atomic so a failed audit insert rolls back the delete — losing
        # the opdracht without a trace would be the worst outcome.
        with transaction.atomic():
            assignment.delete()
            create_event(
                object_type="Assignment",
                action="delete",
                source="user",
                object_id=pk,
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

    The opdracht side panel is an overlay (``?opdracht=`` / ``?plaatsing=``)
    on a real page, so after deleting we return there instead of jumping to
    the opdrachten-lijst. Falls back to the list when the header is absent.
    """
    current = request.headers.get("HX-Current-URL")
    if not current:
        return reverse("assignment-list")
    parsed = urllib.parse.urlparse(current)
    # Keep collega/pagina/filters — only the opdracht panel is closing.
    return _url_drop_params(parsed.path, QueryDict(parsed.query), ("opdracht", "plaatsing"))


def _assignment_audit_snapshot(assignment) -> dict:
    """Snapshot for the create/delete audit event: every rol with who fills it
    (``"Java (Robbert)"``) or ``"open"`` when unfilled, plus the opdrachtgevers
    and the name. One entry per rol, so placements aren't duplicated. Empty
    lists are left out of the audit."""
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
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            panel_data = _build_assignment_panel_data(assignment, request)
        except Assignment.DoesNotExist, ValueError:
            pass
    elif colleague_id:
        try:
            panel_colleague = Colleague.objects.get(id=colleague_id)
            panel_data = _build_colleague_panel_data(panel_colleague, request)
        except Colleague.DoesNotExist, ValueError:
            pass

    # HTMX partial responses for panel swaps
    if "HX-Request" in request.headers:
        hx_target = request.headers.get("HX-Target")
        if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container") and panel_data:
            return render(request, panel_data["panel_content_template"], {"panel_data": panel_data})

    # Build label data per category for the data list rows
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
    """Mark the first-login onboarding wizard as done (completed or skipped).

    Sets ``onboarding_completed_at`` so the wizard no longer appears. For an
    HTMX request, returns a 204 with a ``closeOnboarding`` trigger so the
    dialog closes in place; otherwise redirects home.
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


# Het onboarding-bewerkscherm bouwt één formulier over de opdracht plus je eigen
# rol(len) uit dezelfde specs als inline edit, zodat save- en auditgedrag identiek
# blijft.


def _onboarding_entry(request, pk):
    """De onboarding-entry voor deze opdracht, of None als je er niet op staat."""
    from wies.core.context_processors import _onboarding_assignments  # noqa: PLC0415 — avoids import cycle

    colleague = getattr(request.user, "colleague", None)
    for entry in _onboarding_assignments(colleague, request.user):
        if entry["assignment"].id == pk:
            return entry
    return None


def _onboarding_edit_groups(request, entry, data=None):
    """Formuliergroepen voor het bewerkscherm: de opdracht en elke eigen rol.

    Elke groep krijgt een prefix, zodat de rolvelden van meerdere diensten niet
    op dezelfde namen botsen. De Business Manager zit er bewust niet bij: die is
    hier het aanspreekpunt, niet iets wat je zelf zet.
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
                # Geen kopje: de titel van het scherm noemt de opdracht al.
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
        groups.append(
            {
                # Alleen een kopje als er meer dan één rol is; anders spreken de
                # veldlabels (Rol, Omschrijving rol) voor zich.
                "title": None if len(services) == 1 else f"Rol: {service.skill.name if service.skill else 'onbekend'}",
                "specs": service_specs,
                "form": form_cls(data, initial=initial, prefix=f"rol-{service.id}"),
            }
        )

    return groups


def onboarding_assignment_edit(request, pk):
    """Bewerkscherm voor één opdracht binnen de onboardingwizard."""
    entry = _onboarding_entry(request, pk)
    if entry is None:
        raise Http404("Unknown assignment")

    groups = _onboarding_edit_groups(request, entry, data=request.POST if request.method == "POST" else None)
    if not groups:
        return HttpResponseForbidden()

    if request.method == "POST" and all(group["form"].is_valid() for group in groups):
        with transaction.atomic():
            for group in groups:
                save_edit_specs(request, group["specs"], group["form"].cleaned_data)
        # De bijgewerkte box vervangt de oude in de stap; het bewerkscherm sluit
        # zichzelf op de trigger (zie onboarding.js).
        entry = _onboarding_entry(request, pk)
        response = render(request, "parts/onboarding/onboarding_assignment_box.html", {"entry": entry})
        response["HX-Retarget"] = f"#onboarding-assignment-{pk}"
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger"] = "onboardingDetailClose"
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
    """
    Serve robots.txt to block crawlers and AI scrapers.
    """
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


@permission_required("core.add_assignment", raise_exception=True)
def assignment_create(request):
    """Handle assignment creation - standalone form page."""
    template = "assignment_create.html"

    skill_choices = [("", " "), ("__new__", "+ Nieuwe rol aanmaken")]
    skill_choices.extend((str(s.id), s.name) for s in Skill.objects.order_by("name"))

    if request.method == "GET":
        initial = {}
        if hasattr(request.user, "colleague"):
            initial["owner"] = request.user.colleague
        form = AssignmentCreateForm(initial=initial)
        service_formset = ServiceFormSet(prefix="service", form_kwargs={"skill_choices": skill_choices})
        return render(request, template, {"form": form, "service_formset": service_formset})

    if request.method == "POST":
        form = AssignmentCreateForm(request.POST)
        service_formset = ServiceFormSet(request.POST, prefix="service", form_kwargs={"skill_choices": skill_choices})

        # Check if at least one service has a skill selected (works even when formset is invalid)
        raw_total_forms = request.POST.get("service-TOTAL_FORMS", "0")
        # A crafted/non-numeric management-form value must not crash the view; treat
        # it as zero rows, which surfaces the normal "add at least one role" error.
        total_forms = min(int(raw_total_forms), 100) if raw_total_forms.isdigit() else 0
        has_any_service = any(request.POST.get(f"service-{i}-skill") for i in range(total_forms))
        services_error = "" if has_any_service else "Voeg minimaal één rol toe."

        form_valid = form.is_valid()
        formset_valid = service_formset.is_valid()

        if not form_valid or not formset_valid or services_error:
            if services_error:
                form.add_error(None, services_error)
            return render(request, template, {"form": form, "service_formset": service_formset})

        services_data = extract_services_data(service_formset)
        orgs = form.cleaned_data["organizations"]
        primary_org = next(o["organization"] for o in orgs if o["role"] == "PRIMARY")
        involved_orgs = [o["organization"] for o in orgs if o["role"] == "INVOLVED"]

        assignment = create_assignment_from_form(
            name=form.cleaned_data["name"],
            extra_info=form.cleaned_data.get("extra_info", ""),
            start_date=form.cleaned_data.get("start_date"),
            end_date=form.cleaned_data.get("end_date"),
            owner=form.cleaned_data.get("owner"),
            primary_organization_id=primary_org.id,
            involved_organization_ids=[o.id for o in involved_orgs],
            services_data=services_data,
        )

        create_event(
            object_type="Assignment",
            action="create",
            source="user",
            object_id=assignment.id,
            user=request.user,
            request=request,
            context=_assignment_audit_snapshot(assignment),
        )

        link_url = f"{reverse('assignment-list')}?opdracht={assignment.id}"
        messages.success(
            request,
            f'Opdracht "{assignment.name}" is aangemaakt.',
            extra_tags=f"link:{link_url}|Bekijk opdracht",
        )
        return redirect("assignment-list")
    return HttpResponse(status=405)


def search_suggestions(request):
    """Return org abbreviation suggestions for the search input (HTMX partial)."""
    term = request.GET.get("zoek", "")
    orgs = find_orgs_by_abbreviation(term)
    return render(
        request,
        "parts/search_suggestions.html",
        {"org_suggestions": orgs, "search_term": term.strip()},
    )


def _get_org_counts(count_mode: str, excluded_org_ids: list[int], viewer) -> Counter[int]:
    """Return per-org self-counts based on count_mode.

    ``viewer`` (the viewing Colleague or None) gates the placements count through
    ``filter_visible_placements`` so a planned/ended placement never inflates the
    count shown to someone who may not see it, the same rule the list already applies.
    """
    if count_mode == "none":
        return Counter()
    if count_mode == "open_assignments":
        has_unfilled_open_service = Exists(
            Service.objects.filter(
                assignment=OuterRef("pk"),
                status="OPEN",
                placements__isnull=True,
            )
        )
        assignment_qs = Assignment.objects.filter(has_unfilled_open_service)
        if excluded_org_ids:
            assignment_qs = assignment_qs.exclude(organizations__id__in=excluded_org_ids)
        org_id_list = assignment_qs.values_list("organizations__id", flat=True)
    else:
        visible_placements = filter_visible_placements(
            annotate_placement_dates(Placement.objects.all()), timezone.now().date(), viewer
        )
        if excluded_org_ids:
            visible_placements = visible_placements.exclude(service__assignment__organizations__id__in=excluded_org_ids)
        org_id_list = visible_placements.values_list("service__assignment__organizations__id", flat=True)
    return Counter(org_id for org_id in org_id_list if org_id is not None)


def _build_org_hierarchy(
    org_self_counts: Counter[int], excluded_org_ids: list[int], *, prune_empty: bool
) -> list[dict]:
    """Build the grouped org tree hierarchy for the client modal."""
    all_orgs = list(
        OrganizationUnit.objects.exclude(id__in=excluded_org_ids).values(
            "id", "parent_id", "name", "label", "abbreviations"
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
                    "id": f"self-{node['id']}",
                    "label": node["label"] or node["name"],
                    "abbreviations": node["abbreviations"] or [],
                    "self": True,
                    "nr_of_placements": node["self_count"],
                }
            )
        children_json.extend(to_json(child) for child in children_data)
        result: dict = {
            "id": node["id"],
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
    """Build current selections dict from request params for state restoration."""
    current_selections: dict[str, str] = {}

    org_ids = [org_id for org_id in request.GET.getlist("org") if org_id.isdigit()]
    for org in OrganizationUnit.objects.filter(id__in=org_ids).values("id", "label"):
        current_selections[org["id"]] = org["label"]

    self_org_ids = [org_id for org_id in request.GET.getlist("org_self") if org_id.isdigit()]
    for org in OrganizationUnit.objects.filter(id__in=self_org_ids).values("id", "label"):
        current_selections[f"self-{org['id']}"] = f'Direct onder "{org["label"]}"'

    for type_label in request.GET.getlist("org_type"):
        if type_label:
            current_selections[f"group-{type_label}"] = ORG_TYPE_PLURAL.get(type_label, type_label)

    return current_selections


def client_modal(request):
    """Return the client tree selection modal (HTMX partial)."""
    excluded_org_ids = get_excluded_org_ids()
    count_mode = request.GET.get("count_mode", "placements")

    viewer = getattr(request.user, "colleague", None)
    org_self_counts = _get_org_counts(count_mode, excluded_org_ids, viewer)
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
    """A short, human-readable form of a single field's current value, to name
    the concurrent change in the conflict warning. A group or a collection has
    no single value to show, so this returns None and the caller falls back to
    the generic warning."""
    if not isinstance(spec, Editable):
        return None
    value = _current_value(obj, spec)
    # The audit timeline already renders this field for a human (owner → the
    # colleague's name, not "Colleague object (3)"), so reuse that chain.
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
    """The conflict warning, naming the field and the concurrent value where we
    can show one, so the user does not have to press Annuleren, losing their
    own input, just to find out what changed."""
    concurrent = _readable_current_value(obj, spec)
    if concurrent is None:
        return CONCURRENCY_CONFLICT_ALERT
    # Bold the field label and the concurrent value so the change stands out.
    # ``format_html`` escapes both (the value is user content) before marking
    # the surrounding markup safe; the alert renders its message as HTML.
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
    """The values this edit is based on, in a JSON-serialisable shape."""
    if isinstance(spec, EditableCollection):
        if spec.audit_state is None:
            # Every token would otherwise hash the same empty payload, so no
            # conflict could ever be detected for this collection.
            message = f"EditableCollection {spec.name!r} needs an audit_state to build a concurrency token"
            raise ImproperlyConfigured(message)
        return spec.audit_state(obj)
    state = {}
    for e in resolve_editables(editable_set, spec):
        value = _current_value(obj, e)
        if isinstance(value, list):
            # Rows carry their own shape (dicts for organizations, models for
            # M2M), so let audit_state flatten them where it exists rather than
            # leaning on repr; order-independent either way.
            value = e.audit_state(value) if e.audit_state else sorted(str(getattr(i, "pk", i)) for i in value)
        elif isinstance(value, Model):
            value = value.pk
        state[e.field or e.name] = value
    return state


def _hash_state(state) -> str:
    payload = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _concurrency_token(editable_set, spec, obj) -> str:
    """A short hash of the values this edit is based on, embedded in the edit
    form and re-checked (under a row lock) at save time. If the underlying
    values changed since the form was rendered, the tokens differ and the save
    is rejected instead of silently overwriting the other change."""
    return _hash_state(_edit_state(editable_set, spec, obj))


def _submitted_token(request) -> str:
    return request.POST.get("_concurrency_token", "")


def _has_concurrency_conflict(request, editable_set, spec, obj, *, state=None) -> bool:
    """Whether this POST was built on a stale view of ``obj``.

    Call inside the transaction that holds the row lock, so the state read here
    is the state the save writes over.

    A missing token counts as a conflict. Every form this endpoint renders
    carries one (form.html and collection_form.html own the field), so its
    absence means the POST was not built on a form we handed out and its
    staleness cannot be established. Letting it through would silently disable
    the check for whichever caller omitted the field.

    ``state`` reuses a snapshot the caller already read, so the collection path
    doesn't query the whole team twice while holding the lock.
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
    """Return the denial alert when the user can't UPDATE this field; None when allowed.

    Permission lookup goes through the registry in
    ``wies.core.permissions``. Field-level rules win over the
    whole-object rule for the same model.
    """
    if not has_permission(Verb.UPDATE, obj, user, spec):
        return PERMISSION_DENIED_ALERT
    return None


def _resolve_display(obj, spec, editables) -> dict:
    # Returns {"template": path} to include a partial or {"text": str} for plain rendering.
    if spec.display is None:
        if isinstance(spec, EditableCollection):
            # Collections without an explicit display fall back to a
            # newline-joined string of the initial row dicts — rarely
            # useful, so collections are expected to declare display.
            return {"text": str(spec.initial(obj))}
        if isinstance(spec, EditableGroup):
            # No explicit group display — render each member's value.
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
        "target": f"inline-edit-{model_label}-{obj.pk}-{spec.name}",
        "edit_url": reverse("inline-edit", args=[model_label, obj.pk, spec.name]),
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
    # `saved=True` triggers the toast via HX-Trigger-After-Swap; `alert` carries a denial warning.
    # On denial, skip the value/display resolution — it can be heavy (e.g. the
    # services collection does a per-row Placement query) and the partial
    # gracefully handles an empty value with the alert banner.
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
    }
    response = render(request, "wies/parts/inline_edit/display.html", ctx)
    if saved:
        response["HX-Trigger-After-Swap"] = "inline-edit-saved"
    return response


def _render_inline_edit_form(
    request, editable_set, spec, editables, obj, form, *, alert: dict | None = None, token: str | None = None
) -> HttpResponse:
    # Edit-mode partial: form + save/cancel. On validation failure, `form` carries inline errors.
    # form.html always owns the form element and the concurrency token; a group's
    # ``form_template`` only replaces the field body, so it cannot drop either.
    ctx = {
        **_inline_edit_base_ctx(editable_set, spec, obj),
        "form": form,
        "editable": spec,
        "concurrency_token": token if token is not None else _concurrency_token(editable_set, spec, obj),
        "alert": alert,
    }
    return render(request, "wies/parts/inline_edit/form.html", ctx)


def _render_inline_edit_collection_form(
    request, editable_set, spec, obj, formset, *, alert: dict | None = None, token: str | None = None
) -> HttpResponse:
    # Inner body from spec.form_template; receives the formset as `formset`.
    ctx = {
        **_inline_edit_base_ctx(editable_set, spec, obj),
        "formset": formset,
        "concurrency_token": token if token is not None else _concurrency_token(editable_set, spec, obj),
        "alert": alert,
    }
    return render(request, "wies/parts/inline_edit/collection_form.html", ctx)


def _attach_formset_error(formset, message: str) -> None:
    # FormSets lack a public API for this; _non_form_errors is the documented workaround
    # (is_valid() uses the same internal path when clean() raises).
    existing = list(formset.non_form_errors()) if hasattr(formset, "_non_form_errors") else []
    formset._non_form_errors = ErrorList([*existing, message])


def _handle_inline_edit_collection(request, editable_set, spec: EditableCollection, obj) -> HttpResponse:
    # FormSet equivalent of the Editable/Group path in inline_edit_view.
    if request.method == "POST":
        formset = spec.formset_factory(data=request.POST)
        if formset.is_valid():
            conflict = False
            try:
                with transaction.atomic():
                    obj = editable_set.model.objects.select_for_update().get(pk=obj.pk)
                    # One snapshot, used both to check the token and as the
                    # audit event's "before"; the team query is not cheap.
                    before = _edit_state(editable_set, spec, obj)
                    conflict = _has_concurrency_conflict(request, editable_set, spec, obj, state=before)
                    if not conflict:
                        spec.save(obj, formset)
                        after = _edit_state(editable_set, spec, obj)
                        emit_inline_edit_audit_event(
                            editable_set, spec, obj, before, after, request.user, request=request
                        )
            except editable_set.model.DoesNotExist:
                # Deleted between the permission check and the lock. Same denial
                # partial as a missing or forbidden object, so this stays
                # indistinguishable from those.
                return _render_inline_edit_denial(request, editable_set, spec, obj.pk)
            except ValidationError as exc:
                for message in exc.messages:
                    _attach_formset_error(formset, message)
                return _render_inline_edit_collection_form(
                    request, editable_set, spec, obj, formset, token=_submitted_token(request)
                )
            if conflict:
                # Re-render the bound form (user's input kept) with a token for
                # the new state: Opslaan saves anyway, Annuleren shows the
                # changed data. Rendered after the lock is released.
                return _render_inline_edit_collection_form(
                    request, editable_set, spec, obj, formset, alert=CONCURRENCY_CONFLICT_ALERT
                )
            return _render_inline_edit_display(request, editable_set, spec, editables=[], obj=obj, saved=True)
        return _render_inline_edit_collection_form(
            request, editable_set, spec, obj, formset, token=_submitted_token(request)
        )

    if request.GET.get("cancel"):
        return _render_inline_edit_display(request, editable_set, spec, editables=[], obj=obj)
    if request.GET.get("edit"):
        formset = spec.formset_factory(initial=spec.initial(obj))
        return _render_inline_edit_collection_form(request, editable_set, spec, obj, formset)
    return _render_inline_edit_display(request, editable_set, spec, editables=[], obj=obj)


def _pk_stub(model, pk):
    """An unsaved model instance carrying only ``pk``. Enough for the denial
    partial's target/edit_url so a missing object renders byte-identically to a
    forbidden one, without a second DB round-trip or a real record."""
    stub = model()
    stub.pk = pk
    return stub


def _render_inline_edit_denial(request, editable_set, spec, pk, obj=None, alert=None) -> HttpResponse:
    """The denial partial for an object the user may not edit or that isn't
    there (any more). Both render identically, so this endpoint can't be walked
    as a 404-vs-200 existence oracle over sequential PKs."""
    display_obj = obj if obj is not None else _pk_stub(editable_set.model, pk)
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


def inline_edit_view(request, model_label, pk, name):
    """Generic HTMX endpoint. See ``features/inline-editing.md`` for the full contract."""
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        raise Http404("Unknown model")
    spec = editable_set._editables.get(name) or editable_set.resolve_dynamic(name)
    if spec is None:
        raise Http404("Unknown editable")

    obj = editable_set.model.objects.filter(pk=pk).first()

    # Permission ladder: a missing object and a forbidden one both return the
    # SAME denial partial, so this endpoint can't be walked as a 404-vs-200
    # existence oracle over sequential PKs (mirrors how the side panel returns an
    # identical empty response for not-found and not-visible).
    denial = _permission_denied(editable_set, spec, request.user, obj) if obj is not None else PERMISSION_DENIED_ALERT
    if denial:
        return _render_inline_edit_denial(request, editable_set, spec, pk, obj=obj, alert=denial)

    if isinstance(spec, EditableCollection):
        return _handle_inline_edit_collection(request, editable_set, spec, obj)

    editables = resolve_editables(editable_set, spec)

    # Import here to avoid circulars at module load time.
    from wies.core.inline_edit.forms import save_spec  # noqa: PLC0415

    if request.method == "POST":
        form_cls, _ = build_form_class(
            editables,
            obj=obj,
            group_clean=getattr(spec, "clean", None),
        )
        form = form_cls(request.POST)
        if form.is_valid():
            conflict = False
            try:
                with transaction.atomic():
                    obj = editable_set.model.objects.select_for_update().get(pk=obj.pk)
                    conflict = _has_concurrency_conflict(request, editable_set, spec, obj)
                    if not conflict:
                        if isinstance(spec, EditableGroup):
                            before = {e.name: _current_value(obj, e) for e in editables}
                        else:
                            before = _current_value(obj, spec)
                        mirror = editable_set.audit_mirror
                        with mirror(obj, request.user, request) if mirror else nullcontext():
                            save_spec(spec, editables, form.cleaned_data, obj)
                            if isinstance(spec, EditableGroup):
                                after = {e.name: _current_value(obj, e) for e in editables}
                            else:
                                after = _current_value(obj, spec)
                            emit_inline_edit_audit_event(
                                editable_set,
                                spec,
                                obj,
                                before,
                                after,
                                request.user,
                                child_editables=editables if isinstance(spec, EditableGroup) else None,
                                request=request,
                            )
            except editable_set.model.DoesNotExist:
                # Deleted between the permission check and the lock. Same denial
                # partial as a missing or forbidden object, so this stays
                # indistinguishable from those.
                return _render_inline_edit_denial(request, editable_set, spec, pk)
            if conflict:
                # Re-render the bound form (user's input kept) with a token for
                # the new state: Opslaan saves anyway, Annuleren shows the
                # changed data. Rendered after the lock is released.
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
                saved=True,
            )
        # Keep the token this POST was built on: recomputing it here would adopt
        # a change made in the meantime, and the corrected resubmit would then
        # overwrite that change without ever showing the conflict warning.
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


# Het plaatsingspaneel bewerkt drie dingen die over TWEE modellen verdeeld zijn:
# Service.skill, Service.description en de Placement.period-groep. Een
# EditableGroup kan dat niet dekken (die hoort bij één model), dus bouwen we hier
# één formulier uit de losse specs en hergebruiken we per spec de bestaande
# save- en audit-machinerie van inline_edit_view.


def _safe_return_path(raw: str | None, fallback: str) -> str:
    """Alleen een pad op deze site; anders de fallback.

    De waarde komt uit een hidden input, dus hij is door de client te sturen.
    Hij belandt in HX-Push-Url (alleen de adresbalk, geen navigatie), maar een
    protocol-relative "//host" zou daar alsnog een vreemde origin tonen.
    """
    if raw and raw.startswith("/") and not raw.startswith("//"):
        return raw
    return fallback


@require_POST
def placement_edit_view(request, pk):
    """Sla het gecombineerde bewerkformulier van de plaatsing-child-sheet op.

    Bij succes stuurt deze view de client via HX-Location terug naar de
    ouder-URL; die rendert het paneel opnieuw via de gewone panel-route. Zelf het
    ouderpaneel renderen kan niet: alle paneel-URL's worden uit ``request.path``
    opgebouwd, en dat is hier het POST-pad. De knoppen in dat paneel wezen dan
    naar deze endpoint, die met GET een leeg gebonden formulier opleverde — en
    opslaan wiste vervolgens de velden.

    Bij fouten komt het formulier opnieuw, met meldingen. POST-only, zodat een
    GET nooit een leeg formulier kan tonen.
    """
    placement = (
        Placement.objects.select_related("colleague", "service__assignment", "service__skill").filter(pk=pk).first()
    )
    if placement is None or _resolve_placement_panel(request, pk) is None:
        raise Http404("Unknown placement")

    specs = placement_edit_specs(placement, request.user)
    if not specs:
        return HttpResponseForbidden()

    fallback = _build_panel_url(request, plaatsing=placement.id)
    return_path = _safe_return_path(request.POST.get("terug_url"), fallback)

    form_cls, _ = build_combined_form_class(specs)
    form = form_cls(request.POST)
    if not form.is_valid():
        panel_data = _build_placement_panel_data(placement, request)
        panel_data["form"] = form
        panel_data["parent_url"] = return_path
        panel_data["edit_url"] = reverse("placement-edit", args=[placement.id])
        return render(request, "parts/placement_edit_panel_content.html", {"panel_data": panel_data})

    save_placement_edit(request, placement, specs, form.cleaned_data)

    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


def _build_placement_edit_panel_data(placement, request):
    """Context voor de bewerk-child-sheet, of None zonder bewerkrechten."""
    specs = placement_edit_specs(placement, request.user)
    if not specs:
        return None
    form_cls, initial = build_combined_form_class(specs)
    return {
        "panel_content_template": "parts/placement_edit_panel_content.html",
        "form": form_cls(initial=initial),
        "parent_url": _url_drop_params(request.path, request.GET, ("bewerken",)),
        "edit_url": reverse("placement-edit", args=[placement.id]),
    }


# Zelfde patroon als de plaatsing hierboven: alle opdrachtgegevens in één
# formulier, opgebouwd uit de bestaande specs zodat save- en audit-gedrag
# identiek blijven aan inline edit. Het teamformulier (een formset) heeft een
# eigen child sheet; een formset past niet in dit platte formulier.


def _build_assignment_edit_panel_data(assignment, request):
    """Context voor de opdracht-bewerk-child-sheet, of None zonder bewerkrechten."""
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle

    only = request.GET.get("veld") or None
    specs = assignment_edit_specs(assignment, request.user, only=only)
    if not specs:
        return None
    form_cls, initial = build_combined_form_class(specs)
    return {
        "panel_content_template": "parts/assignment_edit_panel_content.html",
        "form": form_cls(initial=initial),
        # Eén-veld-sheet: de titel noemt dat veld ("Business Manager wijzigen").
        "edit_heading": f"{_spec_label(AssignmentEditables, specs[0][1])} wijzigen" if only else "Opdracht bewerken",
        "parent_url": _url_drop_params(request.path, request.GET, ("bewerken", "veld")),
        "edit_url": reverse("assignment-edit", args=[assignment.id]) + (f"?veld={only}" if only else ""),
    }


@require_POST
def assignment_edit_view(request, pk):
    """Sla het gecombineerde opdrachtformulier van de child sheet op.

    Zelfde contract als placement_edit_view: bij succes HX-Location terug naar
    de ouder-URL (die het paneel opnieuw rendert), bij fouten het formulier
    opnieuw met meldingen. POST-only.
    """
    from wies.core.editables.assignment import AssignmentEditables  # noqa: PLC0415 — avoids import cycle

    assignment = Assignment.objects.filter(pk=pk).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    # ?veld= beperkt de save tot dat ene veld (het ⋯-menu van een rij), zodat
    # een één-veld-sheet niet ongemerkt de andere velden meeneemt.
    only = request.GET.get("veld") or None
    specs = assignment_edit_specs(assignment, request.user, only=only)
    if not specs:
        return HttpResponseForbidden()

    fallback = _build_panel_url(request, opdracht=assignment.id)
    return_path = _safe_return_path(request.POST.get("terug_url"), fallback)
    edit_url = reverse("assignment-edit", args=[assignment.id]) + (f"?veld={only}" if only else "")

    form_cls, _ = build_combined_form_class(specs)
    form = form_cls(request.POST)
    if not form.is_valid():
        panel_data = _build_assignment_panel_data(assignment, request)
        panel_data["form"] = form
        panel_data["parent_url"] = return_path
        panel_data["edit_url"] = edit_url
        panel_data["edit_heading"] = (
            f"{_spec_label(AssignmentEditables, specs[0][1])} wijzigen" if only else "Opdracht bewerken"
        )
        return render(request, "parts/assignment_edit_panel_content.html", {"panel_data": panel_data})

    with transaction.atomic():
        save_edit_specs(request, specs, form.cleaned_data)

    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


# De teamlijst bewerkt per LID, niet als één formset: elke rij heeft zijn eigen
# child sheet (bewerken/toevoegen) en verwijderen gaat via een bevestigings-
# dialoog. Server-side blijft de bestaande sync- en auditmachinerie van de
# formset gelden: elk endpoint reconstrueert het volledige team en wijzigt
# alleen de betrokken rij, zodat apply_services_to_assignment (dat op
# afwezigheid verwijdert) nooit ongewild rijen ziet verdwijnen.


def _build_assignment_member_panel_data(assignment, request):
    """Context voor de teamlid-child-sheet, of None zonder rechten/onbekend lid.

    ``?teamlid=<service-id>`` bewerkt een bestaand lid; ``?teamlid=nieuw-aanvraag``
    en ``?teamlid=nieuw-ingevuld`` voegen een rij toe met de status voorgekozen.
    """
    from wies.core.editables.assignment import AssignmentEditables, _services_initial  # noqa: PLC0415

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return None

    teamlid = request.GET.get("teamlid", "")
    if teamlid in ("nieuw-aanvraag", "nieuw-ingevuld"):
        filled = teamlid == "nieuw-ingevuld"
        initial_row = {"is_filled": "ingevuld" if filled else "aanvraag", "has_custom_period": True}
        heading = "Geplaatste consultant toevoegen" if filled else "Aanvraag toevoegen"
    else:
        try:
            service_id = int(teamlid)
        except ValueError:
            return None
        initial_row = next((r for r in _services_initial(assignment) if r["id"] == service_id), None)
        if initial_row is None:
            return None
        heading = "Teamlid bewerken"

    return {
        "panel_content_template": "parts/assignment_member_edit_panel_content.html",
        "member_formset": spec.formset_factory(initial=[initial_row]),
        "member_heading": heading,
        "parent_url": _url_drop_params(request.path, request.GET, ("teamlid",)),
        "member_edit_url": reverse("assignment-member-edit", args=[assignment.id]),
    }


# --- Match beschikbare collega op één aanvraag (child sheet) ------------------
#
# Het ⋯-menu van een open aanvraag opent "Match beschikbare collega" via
# ?match=<service-id>: een sheet met collega's zonder lopende plaatsing die op de
# skill van díe aanvraag matchen. Een klik plaatst de collega op díe dienst.


def _build_assignment_match_panel_data(assignment, request):
    """Context voor de match-child-sheet, of None zonder rechten/onbekende dienst."""
    from wies.core.editables.assignment import AssignmentEditables, _services_initial  # noqa: PLC0415
    from wies.core.services.placements import available_colleagues  # noqa: PLC0415

    if not has_permission(Verb.UPDATE, assignment, request.user, AssignmentEditables.services):
        return None

    try:
        service_id = int(request.GET.get("match", ""))
    except ValueError:
        return None
    row = next((r for r in _services_initial(assignment) if r["id"] == service_id), None)
    # Alleen een open aanvraag (geen plaatsing) is te matchen.
    if row is None or row["is_filled"] != "aanvraag":
        return None

    skill_ids = [int(row["skill"])] if row["skill"] else None
    colleagues = list(available_colleagues(skill_ids=skill_ids)[:50])

    return {
        "panel_content_template": "parts/assignment_match_panel_content.html",
        "match_colleagues": colleagues,
        "match_role": row["skill_name"] or "onbekende rol",
        "match_place_url": reverse("assignment-match-place", args=[assignment.id, service_id]),
        "parent_url": _url_drop_params(request.path, request.GET, ("match",)),
    }


@require_POST
def assignment_match_place(request, pk, service_id):
    """Plaats de gekozen collega op één specifieke open dienst van de opdracht."""
    from wies.core.editables.assignment import AssignmentEditables, _services_initial  # noqa: PLC0415
    from wies.core.services.assignments import apply_team_change, initial_row_to_services_data  # noqa: PLC0415

    assignment = Assignment.objects.filter(pk=pk).first()
    if assignment is None:
        raise Http404("Unknown assignment")
    if not has_permission(Verb.UPDATE, assignment, request.user, AssignmentEditables.services):
        return HttpResponseForbidden()

    colleague = Colleague.objects.filter(pk=request.POST.get("collega")).first()
    rows = _services_initial(assignment)
    target = next((r for r in rows if r["id"] == service_id and r["is_filled"] == "aanvraag"), None)
    if colleague is None or target is None:
        return HttpResponse(status=422)

    services_data = [initial_row_to_services_data(r) for r in rows]
    for svc in services_data:
        if svc["id"] == service_id:
            svc["colleague_id"] = colleague.id
            svc["status"] = "OPEN"
    apply_team_change(request, assignment, services_data)

    return_path = _safe_return_path(request.POST.get("terug_url"), _build_panel_url(request, opdracht=assignment.id))
    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


@require_POST
def assignment_member_edit_view(request, pk):
    """Sla één teamlid op uit de child sheet (bewerken of toevoegen).

    Het formulier post één formset-rij; de overige rijen komen uit de database,
    zodat de sync altijd het volledige team ziet. Zelfde contract als
    assignment_edit_view: HX-Location terug bij succes, formulier met
    meldingen bij fouten."""
    from wies.core.editables.assignment import AssignmentEditables, _services_initial  # noqa: PLC0415
    from wies.core.services.assignments import extract_services_data  # noqa: PLC0415

    assignment = Assignment.objects.filter(pk=pk).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return HttpResponseForbidden()

    fallback = _build_panel_url(request, opdracht=assignment.id)
    return_path = _safe_return_path(request.POST.get("terug_url"), fallback)

    def rerender(formset):
        panel_data = _build_assignment_panel_data(assignment, request)
        panel_data["member_formset"] = formset
        panel_data["member_heading"] = request.POST.get("member_heading") or "Teamlid bewerken"
        panel_data["parent_url"] = return_path
        panel_data["member_edit_url"] = reverse("assignment-member-edit", args=[assignment.id])
        return render(request, "parts/assignment_member_edit_panel_content.html", {"panel_data": panel_data})

    formset = spec.formset_factory(data=request.POST)
    if not formset.is_valid():
        return rerender(formset)

    edited = extract_services_data(formset)
    if not edited:
        # Zonder rol slaat extract_services_data de rij over; hier zou dat het
        # lid stilletjes VERWIJDEREN (sync op afwezigheid), dus blokkeer het.
        _attach_formset_error(formset, "Kies een rol.")
        return rerender(formset)

    edited_ids = {int(row["id"]) for row in edited if row.get("id")}
    others = [initial_row_to_services_data(row) for row in _services_initial(assignment) if row["id"] not in edited_ids]
    try:
        apply_team_change(request, assignment, others + edited)
    except ValidationError as exc:
        for message in exc.messages:
            _attach_formset_error(formset, message)
        return rerender(formset)

    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


@require_POST
def assignment_member_delete_view(request, pk, service_id):
    """Verwijder één teamlid, na de bevestigingsdialoog in het paneel."""
    from wies.core.editables.assignment import AssignmentEditables, _services_initial  # noqa: PLC0415

    assignment = Assignment.objects.filter(pk=pk).first()
    if assignment is None:
        raise Http404("Unknown assignment")

    spec = AssignmentEditables.services
    if not has_permission(Verb.UPDATE, assignment, request.user, spec):
        return HttpResponseForbidden()

    rows = _services_initial(assignment)
    if not any(row["id"] == service_id for row in rows):
        raise Http404("Unknown service")

    services_data = [initial_row_to_services_data(row) for row in rows if row["id"] != service_id]
    apply_team_change(request, assignment, services_data)

    return_path = _safe_return_path(request.POST.get("terug_url"), _build_panel_url(request, opdracht=assignment.id))
    response = HttpResponse(status=204)
    response["HX-Location"] = json.dumps({"path": return_path, "target": "#side-panel-content", "swap": "innerHTML"})
    return response


@login_required
def bm_board(request):
    """PoC: kanban-bord van de diensten waarvan de ingelogde gebruiker BM is."""
    from wies.core.services.board import COLUMNS, build_bm_board  # noqa: PLC0415 — PoC, lokaal

    # Een kaart opent het opdrachtpaneel via ?opdracht= op /bord zelf (niet via
    # /opdrachten), zodat de adresbalk op /bord blijft en een refresh het paneel
    # terugbrengt. Alle paneel-URL's komen uit request.path, dus ze wijzen ook
    # terug naar /bord. Zie AssignmentListView voor hetzelfde patroon.
    panel_data = None
    assignment_id = request.GET.get("opdracht")
    if assignment_id:
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            panel_data = _build_assignment_panel_data(assignment, request)
        except Assignment.DoesNotExist, ValueError:
            pass

    if "HX-Request" in request.headers:
        hx_target = request.headers.get("HX-Target", "")
        if hx_target in ("side-panel-content", "side_panel-content", "side_panel-container") and panel_data:
            return render(request, panel_data["panel_content_template"], {"panel_data": panel_data})

    from wies.core.services.board import GILDES  # noqa: PLC0415 — PoC, lokaal

    colleague = getattr(request.user, "colleague", None)

    # Filters (PoC): gilde (it/digi, dummy uit opdracht-id) en "aflopend binnen"
    # N maanden. Onbekende waarden negeren we, zodat een rare querystring niet
    # crasht maar gewoon niet filtert.
    gilde = request.GET.get("gilde") if request.GET.get("gilde") in GILDES else None
    try:
        ending_within = int(request.GET.get("aflopend", ""))
    except ValueError:
        ending_within = None
    if ending_within not in (1, 2, 3):
        ending_within = None

    board = build_bm_board(colleague, gilde=gilde, ending_within_months=ending_within)
    columns = [{"key": key, "label": label, "cards": board[key]} for key, label in COLUMNS]
    active_filters = {"gilde": gilde, "aflopend": ending_within}

    # Filterwissel: de filterrijen targeten #bm-board-grid, dus lever de kolommen
    # terug plus de sidebar als OOB-swap (anders houden de rijen hun oude
    # checked-staat en toggle-URL's).
    if "HX-Request" in request.headers and request.headers.get("HX-Target") == "bm-board-grid":
        grid = render_to_string("parts/bm_board_columns.html", {"columns": columns}, request=request)
        sidebar = render_to_string(
            "parts/bm_board_filters.html",
            {"active_filters": active_filters, "filters_oob": True},
            request=request,
        )
        return HttpResponse(grid + sidebar)

    # Zelfde "Opdracht invoeren"-knop als de Aanvragen-lijst: opent de
    # aanmaak-sheet in het zijpaneel van het bord.
    primary_button = None
    if request.user.has_perm("core.add_assignment"):
        primary_button = {
            "button_text": "Opdracht invoeren",
            "attrs": {
                "hx-get": reverse("assignment-create-sheet") + "?terug=" + reverse("bm-board"),
                "hx-target": "#side-panel-content",
                "hx-swap": "innerHTML",
                "hx-push-url": "false",
            },
        }
    return render(
        request,
        "bm_board.html",
        {
            "columns": columns,
            "primary_button": primary_button,
            "panel_data": panel_data,
            "active_filters": active_filters,
        },
    )


@require_POST
@login_required
def bm_board_move(request, assignment_id):
    """PoC: sla een sleep-actie op het bord op — zet de status van de opdracht.

    Alleen de BM (owner) van de opdracht mag slepen. 204 bij succes; 422 bij een
    onbekende statuskolom zodat het JS de kaart terugzet.
    """
    from wies.core.services.board import move_assignment_to_status  # noqa: PLC0415 — PoC, lokaal

    colleague = getattr(request.user, "colleague", None)
    assignment = Assignment.objects.filter(pk=assignment_id).first()
    if assignment is None or colleague is None or assignment.owner_id != colleague.id:
        return HttpResponseForbidden()

    status = request.POST.get("kolom", "")
    if not move_assignment_to_status(assignment, status):
        return HttpResponse(status=422)
    return HttpResponse(status=204)


def _board_owner_or_403(request, assignment_id):
    """De opdracht als de ingelogde gebruiker de BM ervan is, anders None."""
    colleague = getattr(request.user, "colleague", None)
    assignment = Assignment.objects.filter(pk=assignment_id).first()
    if assignment is None or colleague is None or assignment.owner_id != colleague.id:
        return None, colleague
    return assignment, colleague


def _user_is_board_owner(request, assignment):
    """Alleen de BM van de opdracht beheert de opmerkingen (toevoegen/togglen/verwijderen)."""
    colleague = getattr(request.user, "colleague", None)
    return colleague is not None and assignment.owner_id == colleague.id


def _build_assignment_note_panel_data(assignment, request):
    """Context voor de opmerking-child-sheet, of None zonder BM-rechten.

    Net als het teamlid: ``?notitie=nieuw`` opent een leeg formulier, ``?notitie=
    <id>`` bewerkt één bestaande opmerking. Toevoegen en bewerken delen hetzelfde
    formulier (tekst + 'tonen op het bord'). Zonder BM-rechten valt de parameter
    terug op het leespaneel.
    """
    if not _user_is_board_owner(request, assignment):
        return None

    notitie = request.GET.get("notitie", "")
    if notitie == "nieuw":
        note = None
        heading = "Opmerking toevoegen"
    else:
        try:
            note = assignment.notes.get(pk=int(notitie))
        except ValueError, AssignmentNote.DoesNotExist:
            return None
        heading = "Opmerking bewerken"

    return {
        "panel_content_template": "parts/assignment_note_edit_panel_content.html",
        "note": note,
        "note_heading": heading,
        "note_save_url": reverse("assignment-note-save", args=[assignment.id, note.id if note else 0]),
        "parent_url": _url_drop_params(request.path, request.GET, ("notitie",)),
    }


def _note_save_response(request, assignment):
    """Her-render het opdrachtpaneel (child-sheet sluit, verse opmerkingen-lijst)
    plus de bord-kaart als out-of-band swap.

    Bewust GEEN HX-Location zoals de teamlid-sheet: die herlaadt alleen
    #side-panel-content en short-circuit't de OOB-swap in deze response, dus de
    bord-kaart eronder ververst dan niet. We renderen daarom het paneel direct in
    de body én de OOB-kaart, zodat htmx beide toepast.
    """
    from urllib.parse import urlparse  # noqa: PLC0415

    from django.http import QueryDict  # noqa: PLC0415

    from wies.core.services.board import build_bm_board  # noqa: PLC0415 — PoC, lokaal

    # Het paneel bouwt al z'n actie-URL's uit request.path/GET. Op deze POST is dat
    # het save-endpoint, dus richt het even op de ouder-URL (terug_url) zodat de
    # knoppen weer naar /bord (of /opdrachten) wijzen. Daarna terugzetten.
    parent = _safe_return_path(request.POST.get("terug_url"), _build_panel_url(request, opdracht=assignment.id))
    parsed = urlparse(parent)
    orig_path, orig_get = request.path, request.GET
    request.path, request.GET = parsed.path, QueryDict(parsed.query)
    try:
        panel_data = _build_assignment_panel_data(assignment, request)
        panel_html = render_to_string(panel_data["panel_content_template"], {"panel_data": panel_data}, request=request)
    finally:
        request.path, request.GET = orig_path, orig_get
    board = build_bm_board(assignment.owner)
    card = next((c for cards in board.values() for c in cards if c["id"] == assignment.id), None)
    card_html = ""
    if card is not None:
        card_html = render_to_string("parts/bm_board_card.html", {"card": card, "oob": True}, request=request)
    return HttpResponse(panel_html + card_html)


@login_required
@require_POST
def assignment_note_save(request, assignment_id, note_id):
    """PoC: sla één opmerking op (toevoegen als note_id 0 is, anders bewerken).

    Tekst + 'tonen op het bord' komen uit hetzelfde formulier als toevoegen.
    Alleen de BM van de opdracht.
    """
    assignment, colleague = _board_owner_or_403(request, assignment_id)
    if assignment is None:
        return HttpResponseForbidden()

    text = (request.POST.get("text") or "").strip()
    show_on_board = bool(request.POST.get("show_on_board"))
    if not text:
        # Leeg tekstveld: her-render het formulier met een melding.
        panel_data = _build_assignment_panel_data(assignment, request)
        note = assignment.notes.filter(pk=note_id).first() if note_id else None
        panel_data.update(
            {
                "note": note,
                "note_heading": "Opmerking bewerken" if note else "Opmerking toevoegen",
                "note_save_url": reverse("assignment-note-save", args=[assignment.id, note_id]),
                "parent_url": _safe_return_path(
                    request.POST.get("terug_url"), _build_panel_url(request, opdracht=assignment.id)
                ),
                "note_error": "Vul een opmerking in.",
            }
        )
        return render(request, "parts/assignment_note_edit_panel_content.html", {"panel_data": panel_data})

    if note_id:
        note = assignment.notes.filter(pk=note_id).first()
        if note is None:
            return HttpResponseForbidden()
        note.text = text[:500]
        note.show_on_board = show_on_board
        note.save(update_fields=["text", "show_on_board"])
    else:
        AssignmentNote.objects.create(
            assignment=assignment, author=colleague, text=text[:500], show_on_board=show_on_board
        )
    return _note_save_response(request, assignment)


@login_required
@require_POST
def assignment_note_delete(request, assignment_id, note_id):
    """PoC: verwijder een opmerking. Alleen de BM."""
    assignment, _ = _board_owner_or_403(request, assignment_id)
    if assignment is None:
        return HttpResponseForbidden()
    assignment.notes.filter(pk=note_id).delete()
    return _note_save_response(request, assignment)


@login_required
def assignment_create_sheet(request):
    """Maak een opdracht aan via het zijpaneel — hergebruikt het opdracht-
    formulier van de bewerk-sheet (naam, omschrijving, opdrachtgever, periode,
    BM). Diensten/rollen voeg je daarna toe in het opdrachtpaneel.

    GET: de sheet met een leeg formulier. POST: aanmaken en via HX-Location naar
    het nieuwe opdrachtpaneel. Alleen voor wie opdrachten mag aanmaken.
    """
    from wies.core.services.assignments import assignment_create_specs, create_assignment_from_specs  # noqa: PLC0415

    if not request.user.has_perm("core.add_assignment"):
        return HttpResponseForbidden()

    specs = assignment_create_specs()
    form_cls, initial = build_combined_form_class(specs)
    return_to = _safe_return_path(request.GET.get("terug") or request.POST.get("terug_url"), reverse("assignment-list"))

    if request.method == "POST":
        form = form_cls(request.POST)
        if form.is_valid():
            with transaction.atomic():
                assignment = create_assignment_from_specs(form.cleaned_data)
            # Het bord rendert geen opdrachtpaneel, dus daar herladen we de pagina
            # (de nieuwe kaart verschijnt in de juiste kolom). Op de lijst openen
            # we het nieuwe opdrachtpaneel via HX-Location.
            if return_to == reverse("bm-board"):
                response = HttpResponse(status=204)
                response["HX-Redirect"] = return_to
                return response
            sep = "&" if "?" in return_to else "?"
            path = f"{return_to}{sep}opdracht={assignment.id}"
            response = HttpResponse(status=204)
            response["HX-Location"] = json.dumps({"path": path, "target": "#side-panel-content", "swap": "innerHTML"})
            return response
    else:
        # Voorvullen: de aanmaker is doorgaans zelf de BM.
        if getattr(request.user, "colleague", None):
            initial["owner"] = request.user.colleague
        form = form_cls(initial=initial)

    panel_data = {
        "form": form,
        "edit_url": reverse("assignment-create-sheet"),
        "parent_url": return_to,
        "edit_heading": "Opdracht invoeren",
        "submit_label": "Aanmaken",
    }
    return render(request, "parts/assignment_create_panel_content.html", {"panel_data": panel_data})
