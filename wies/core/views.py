import logging
import tempfile
import urllib.parse
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required, permission_required, user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core import management
from django.core.exceptions import ValidationError
from django.db.models import Case, Exists, OuterRef, Prefetch, Q, Value, When
from django.db.models.functions import Concat
from django.forms.utils import ErrorList
from django.http import Http404, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
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
    build_form_class,
    resolve_editables,
)
from wies.core.permissions import Verb, has_permission

from .forms import (
    AssignmentCreateForm,
    LabelCategoryForm,
    LabelForm,
    ServiceFormSet,
    UserForm,
)
from .models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Event,
    Label,
    LabelCategory,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)
from .querysets import annotate_placement_dates, annotate_usage_counts
from .services.assignments import create_assignment_from_form, extract_services_data
from .services.events import create_event
from .services.organizations import (
    find_orgs_by_abbreviation,
    get_excluded_org_ids,
    get_org_breadcrumb,
    get_org_descendant_ids,
)
from .services.placements import (
    create_assignments_from_csv,
    filter_placements_by_min_end_date,
)
from .services.sync import sync_all_otys_iir_records
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


def _build_panel_url(request, **overrides):
    """Build a URL on the current path, preserving filters but replacing panel params."""
    params = QueryDict(mutable=True)
    params.update(request.GET)
    params.pop("pagina", None)
    params.pop("collega", None)
    params.pop("opdracht", None)
    for key, value in overrides.items():
        params[key] = value
    return f"{request.path}?{params.urlencode()}"


def _build_close_url(request):
    """Build close URL preserving current filters."""
    params = QueryDict(mutable=True)
    params.update(request.GET)
    params.pop("pagina", None)
    params.pop("collega", None)
    params.pop("opdracht", None)
    return f"{request.path}?{params.urlencode()}" if params else request.path


def _make_team_member_entry(
    colleague, colleague_url=None, *, historical=False, privacy_warning_text=None, is_vacancy=False, skills=None
):
    """Build a standard team member dict for assignment panel display."""
    return {
        "colleague": colleague,
        "colleague_url": colleague_url,
        "skills": skills or [],
        "historical": historical,
        "privacy_warning_text": privacy_warning_text,
        "is_vacancy": is_vacancy,
    }


def _build_assignment_panel_data(assignment, request, breadcrumb_base):
    """Shared helper to build assignment panel context data for both views."""
    today = timezone.now().date()
    viewer = getattr(request.user, "colleague", None)
    viewer_is_bm = viewer is not None and assignment.owner_id == viewer.id

    # Single query: all services with all annotated placements
    services = list(
        assignment.services.select_related("skill").prefetch_related(
            Prefetch(
                "placements",
                queryset=annotate_placement_dates(Placement.objects.select_related("colleague")),
                to_attr="all_placements",
            )
        )
    )

    vacancy_list: list[dict] = []
    # Group by (colleague_id, historical) to merge skills per colleague
    current_grouped: dict[int, dict] = {}
    historical_grouped: dict[int, dict] = {}

    for service in services:
        skill = {"name": service.skill.name, "description": service.description} if service.skill else None

        # Vacancy: OPEN service that never had any placement
        if not service.all_placements and service.status == "OPEN":
            vacancy_list.append(_make_team_member_entry(None, is_vacancy=True, skills=[skill] if skill else []))
            continue

        for placement in service.all_placements:
            cid = placement.colleague.id
            placement_is_active = placement.actual_end_date is None or today <= placement.actual_end_date

            if placement_is_active:
                # Active placements are visible to everyone
                if cid not in current_grouped:
                    current_grouped[cid] = _make_team_member_entry(
                        placement.colleague,
                        colleague_url=_build_panel_url(request, collega=cid),
                    )
                if skill:
                    current_grouped[cid]["skills"].append(skill)

            elif viewer is not None and cid == viewer.id:
                # Consultants can see their own ended placements
                if cid not in historical_grouped:
                    historical_grouped[cid] = _make_team_member_entry(
                        placement.colleague,
                        colleague_url=_build_panel_url(request, collega=cid),
                        historical=True,
                        privacy_warning_text="Alleen zichtbaar voor jou en de Business Manager",
                    )
                if skill:
                    historical_grouped[cid]["skills"].append(skill)

            elif viewer_is_bm:
                # BM can see all ended placements on their assignment
                if cid not in historical_grouped:
                    historical_grouped[cid] = _make_team_member_entry(
                        placement.colleague,
                        colleague_url=_build_panel_url(request, collega=cid),
                        historical=True,
                        privacy_warning_text="Alleen zichtbaar voor jou en de consultant",
                    )
                if skill:
                    historical_grouped[cid]["skills"].append(skill)

            else:
                # Others must not see ended placements
                continue

    team_members = vacancy_list + list(current_grouped.values()) + list(historical_grouped.values())

    primary = assignment.organization_relations.filter(role="PRIMARY").select_related(
        "organization__parent__parent__parent__parent"
    )
    involved = assignment.organization_relations.filter(role="INVOLVED").select_related(
        "organization__parent__parent__parent__parent"
    )
    org_breadcrumbs = [
        {**get_org_breadcrumb(rel.organization, breadcrumb_base), "role": rel.role} for rel in [*primary, *involved]
    ]

    owner_mailto_href = ""
    if assignment.owner and assignment.owner.email:
        opdracht_url = request.build_absolute_uri(reverse("assignment-list") + f"?opdracht={assignment.id}")
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
        owner_mailto_href = f"mailto:{assignment.owner.email}?subject={subject}&body={body}"

    return {
        "panel_content_template": "parts/assignment_panel_content.html",
        "panel_title": assignment.name,
        "close_url": _build_close_url(request),
        "assignment": assignment,
        "team_members": team_members,
        "user_can_edit": has_permission(Verb.UPDATE, assignment, request.user),
        "show_updates_tab": assignment.source != "otys_iir",
        "owner_url": _build_panel_url(request, collega=assignment.owner.id) if assignment.owner else "",
        "owner_mailto_href": owner_mailto_href,
        "org_breadcrumbs": org_breadcrumbs,
    }


def _merge_date_range(existing: dict, start, end):
    """Widen the date range of an assignment entry to include the given start/end."""
    if start and (existing["start_date"] is None or start < existing["start_date"]):
        existing["start_date"] = start
    if end and (existing["end_date"] is None or end > existing["end_date"]):
        existing["end_date"] = end


def _make_assignment_entry(name, aid, request, start_date=None, end_date=None, **extra):
    """Build a standard assignment dict for panel display."""
    return {
        "name": name,
        "id": aid,
        "tags": {},
        "assignment_url": _build_panel_url(request, opdracht=aid),
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
        placement_is_active = placement.get("actual_end_date") is None or today <= placement["actual_end_date"]
        owner_id = placement["service__assignment__owner_id"]
        viewer_is_assignment_bd = viewer is not None and owner_id is not None and owner_id == viewer.id

        if placement_is_active:
            if assignment_id not in active_by_id:
                active_by_id[assignment_id] = _make_assignment_entry(
                    placement["service__assignment__name"],
                    assignment_id,
                    request,
                    start_date=placement.get("actual_start_date"),
                    end_date=placement.get("actual_end_date"),
                )
            else:
                _merge_date_range(
                    active_by_id[assignment_id], placement.get("actual_start_date"), placement.get("actual_end_date")
                )
            skill_name = placement["service__skill__name"]
            if skill_name:
                active_by_id[assignment_id]["tags"][skill_name] = placement["service__description"]
        elif viewer_is_colleague:
            # users can see their own ended placements
            if assignment_id not in historical_by_id:
                historical_by_id[assignment_id] = _make_assignment_entry(
                    placement["service__assignment__name"],
                    assignment_id,
                    request,
                    start_date=placement.get("actual_start_date"),
                    end_date=placement.get("actual_end_date"),
                    historical=True,
                    privacy_warning_text="Alleen zichtbaar voor jou en de Business Manager",
                )
            else:
                _merge_date_range(
                    historical_by_id[assignment_id],
                    placement.get("actual_start_date"),
                    placement.get("actual_end_date"),
                )
            skill_name = placement["service__skill__name"]
            if skill_name:
                historical_by_id[assignment_id]["tags"][skill_name] = placement["service__description"]
        elif viewer_is_assignment_bd:
            # business developers can see their the assignments they own
            # users can see their own ended placements
            if assignment_id not in historical_by_id:
                historical_by_id[assignment_id] = _make_assignment_entry(
                    placement["service__assignment__name"],
                    assignment_id,
                    request,
                    start_date=placement.get("actual_start_date"),
                    end_date=placement.get("actual_end_date"),
                    historical=True,
                    privacy_warning_text="Alleen zichtbaar voor jou en de consultant",
                )
            else:
                _merge_date_range(
                    historical_by_id[assignment_id],
                    placement.get("actual_start_date"),
                    placement.get("actual_end_date"),
                )
            skill_name = placement["service__skill__name"]
            if skill_name:
                historical_by_id[assignment_id]["tags"][skill_name] = placement["service__description"]
        else:
            # others should not see these placements
            continue

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


@login_not_required  # page cannot require login because you land on this after unsuccesful login
def no_access(request):
    email = request.session.pop("failed_login_email", None)
    is_allowed_domain = email and is_allowed_email_domain(email)
    return render(request, "no_access.html", {"email": email, "is_allowed_domain": is_allowed_domain})


@user_passes_test(lambda u: u.is_authenticated and u.email.lower() in settings.STAFF_EMAILS, login_url="/geen-toegang/")
def staff(request):
    context = {
        "assignment_count": Assignment.objects.count(),
        "colleague_count": Colleague.objects.count(),
        "organization_count": OrganizationUnit.objects.count(),
        "latest_tasks": get_latest_tasks(limit=3),
    }
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "clear_data":
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
            management.call_command("loaddata", "base_dummy_data.json")
            messages.success(request, "Data geladen uit base_dummy_data.json")
        elif action == "export_data":
            # Use dumpdata's native --output argument with temp file
            with tempfile.NamedTemporaryFile(mode="r", suffix=".json", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # dumpdata writes directly to file using --output argument
                management.call_command("dumpdata", "--natural-foreign", "--natural-primary", output=tmp_path)

                # Read the JSON file
                json_data = Path(tmp_path).read_text()

                response = HttpResponse(json_data, content_type="application/json")
                response["Content-Disposition"] = 'attachment; filename="wies_datadump.json"'
                return response
            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)
        elif action == "import_data":
            # Handle database import from uploaded JSON file
            if "json_file" not in request.FILES:
                messages.error(request, "Geen bestand geüpload. Upload een JSON-bestand.")
                return redirect("staff")

            json_file = request.FILES["json_file"]

            # Validate file extension
            if not json_file.name.endswith(".json"):
                messages.error(request, "Ongeldig bestandstype. Upload een JSON-bestand.")
                return redirect("staff")

            # Save uploaded file to temp location
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False) as tmp:
                tmp_path = tmp.name
                for chunk in json_file.chunks():
                    tmp.write(chunk)

            try:
                # Clear existing data before import to avoid PK conflicts
                # Same clearing logic as "clear_data" action
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

                # Load data using Django's loaddata command
                management.call_command("loaddata", tmp_path)
                messages.success(request, "Database succesvol geïmporteerd")
            except Exception as e:  # noqa: BLE001
                # Catch all exceptions to show user-friendly error message
                messages.error(request, f"Import mislukt: {e!s}")
            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)

            return redirect("staff")
        elif action == "sync_all_otys_records":
            sync_all_otys_iir_records()
            messages.success(request, "All records synced successfully from OTYS IIR")
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

            return redirect("staff")
        return redirect("staff")

    return render(request, "admin_db.html", context)


class PlacementListView(ListView):
    """View for placements table view with infinite scroll pagination"""

    model = Placement
    template_name = "placement_table.html"
    paginate_by = 50
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
        }

        order_param = self.request.GET.get("order")
        if order_param:
            order_by = order_mapping.get(order_param)
            if order_by:
                qs = qs.order_by(order_by)

        # filter out historical placements
        qs = annotate_placement_dates(qs)
        return filter_placements_by_min_end_date(qs, timezone.now().date())

    def _get_labels_by_category(self):
        """Parse selected label IDs grouped by category."""
        label_ids = [int(lid) for lid in self.request.GET.getlist("labels") if lid]
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
        label_ids = [int(lid) for lid in self.request.GET.getlist("labels") if lid]
        if label_ids and not self._get_labels_by_category():
            return Placement.objects.none()
        qs = self._apply_filters(qs)
        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if "HX-Request" in self.request.headers:
            if self.request.headers.get("HX-Target") == "side_panel-container":
                return ["parts/side_panel.html"]
            if self.request.headers.get("HX-Target") == "side_panel-content":
                colleague_id = self.request.GET.get("collega")
                assignment_id = self.request.GET.get("opdracht")

                if colleague_id and not assignment_id:
                    return ["parts/colleague_panel_content.html"]
                if assignment_id:
                    return ["parts/assignment_panel_content.html"]
            if self.request.GET.get("pagina"):
                return ["parts/placement_table_rows.html"]
            return ["parts/filter_and_table_container.html"]
        return ["placement_table.html"]

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)
        context["render_filter_fields_oob"] = "HX-Request" in self.request.headers

        # Add colleague URLs to placement objects
        for placement in context["object_list"]:
            placement.colleague_url = _build_panel_url(self.request, collega=placement.colleague.id)

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
            if label_id != "":
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

        # Build next page URL with all current filters
        if context.get("page_obj") and context["page_obj"].has_next():
            params = self.request.GET.copy()
            params["pagina"] = context["page_obj"].next_page_number()
            context["next_page_url"] = f"?{params.urlencode()}"
        else:
            context["next_page_url"] = None

        colleague_id = self.request.GET.get("collega")
        assignment_id = self.request.GET.get("opdracht")

        if colleague_id and not assignment_id:
            try:
                colleague = Colleague.objects.get(id=colleague_id)
                context["panel_data"] = _build_colleague_panel_data(colleague, self.request)
            except Colleague.DoesNotExist:
                pass
        elif assignment_id:
            try:
                assignment = Assignment.objects.get(id=assignment_id)
                context["panel_data"] = _build_assignment_panel_data(assignment, self.request, self.request.path)
            except Assignment.DoesNotExist:
                pass
        return context


class AssignmentListView(ListView):
    """View for vacancy assignments displayed as cards with infinite scroll pagination"""

    model = Assignment
    template_name = "assignment_card_grid.html"
    paginate_by = 24
    page_kwarg = "pagina"

    def _get_base_queryset(self):
        has_unfilled_open_service = Exists(
            Service.objects.filter(
                assignment=OuterRef("pk"),
                status="OPEN",
                placements__isnull=True,
            )
        )
        qs = Assignment.objects.filter(has_unfilled_open_service).order_by("-created_at")
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
            rol_filter = self.request.GET.getlist("rol")
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
            if self.request.headers.get("HX-Target") == "side_panel-container":
                return ["parts/side_panel.html"]
            if self.request.headers.get("HX-Target") == "side_panel-content":
                colleague_id = self.request.GET.get("collega")
                assignment_id = self.request.GET.get("opdracht")
                if colleague_id and not assignment_id:
                    return ["parts/colleague_panel_content.html"]
                return ["parts/assignment_panel_content.html"]
            if self.request.GET.get("pagina"):
                return ["parts/assignment_card_rows.html"]
            return ["parts/filter_and_card_container.html"]
        return ["assignment_card_grid.html"]

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
            if rol_id != "":
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

        # Build next page URL with all current filters
        if context.get("page_obj") and context["page_obj"].has_next():
            params = self.request.GET.copy()
            params["pagina"] = context["page_obj"].next_page_number()
            context["next_page_url"] = f"?{params.urlencode()}"
        else:
            context["next_page_url"] = None

        # Primary button for assignment creation (BDM permission)
        if self.request.user.has_perm("core.add_assignment"):
            context["primary_button"] = {
                "button_text": "Opdracht invoeren",
                "href": reverse("assignment-create"),
            }

        # Side panel
        colleague_id = self.request.GET.get("collega")
        assignment_id = self.request.GET.get("opdracht")

        if colleague_id and not assignment_id:
            try:
                colleague = Colleague.objects.get(id=colleague_id)
                context["panel_data"] = _build_colleague_panel_data(colleague, self.request)
            except Colleague.DoesNotExist:
                pass
        elif assignment_id:
            try:
                assignment = Assignment.objects.select_related("owner").get(id=assignment_id)
                context["panel_data"] = _build_assignment_panel_data(assignment, self.request, self.request.path)
            except Assignment.DoesNotExist:
                pass

        return context


class UserListView(PermissionRequiredMixin, ListView):
    """View for user list with filtering and infinite scroll pagination"""

    model = User
    template_name = "user_admin.html"
    paginate_by = 50
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
        label_ids = [int(lid) for lid in self.request.GET.getlist("labels") if lid]
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
        label_ids = [int(lid) for lid in self.request.GET.getlist("labels") if lid]
        if label_ids and not self._get_labels_by_category():
            return User.objects.none()
        qs = self._apply_filters(qs)
        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if "HX-Request" in self.request.headers:
            # If paginating, return only rows
            if self.request.GET.get("pagina"):
                return ["parts/user_table_rows.html"]
            # Otherwise, return full table (for filter changes)
            return ["parts/user_table.html"]
        return ["user_admin.html"]

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)

        context["search_field"] = "zoek"
        context["search_placeholder"] = "Zoek op naam of email..."
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters = {}

        # label filter supports multi-select
        label_filter = set()
        for label_id in self.request.GET.getlist("labels"):
            if label_id != "":
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
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Toevoegen",
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
            )
            # For HTMX requests, use HX-Redirect header to force full page redirect
            # For standard form posts, use normal redirect
            if "HX-Request" in request.headers:
                response = HttpResponse(status=200)
                response["HX-Redirect"] = reverse("admin-users")
                return response
            return redirect("admin-users")
        # Re-render form with errors (stays in modal with HTMX)
        return render(
            request,
            "parts/user_form_modal.html",
            {
                "content": form,
                "form_post_url": form_post_url,
                "modal_title": modal_title,
                "form_button_label": "Toevoegen",
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
                **get_delete_context(
                    "user-delete", edited_user.pk, f"{edited_user.first_name} {edited_user.last_name}"
                ),
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
            )
            # For HTMX requests, use HX-Redirect header to force full page redirect
            # For standard form posts, use normal redirect
            if "HX-Request" in request.headers:
                response = HttpResponse(status=200)
                response["HX-Redirect"] = reverse("admin-users")
                return response
            return redirect("admin-users")
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
                **get_delete_context(
                    "user-delete", edited_user.pk, f"{edited_user.first_name} {edited_user.last_name}"
                ),
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
            "parts/generic_form_modal.html",
            {
                "modal_title": f"Verwijder gebruiker: {user.first_name} {user.last_name}",
                "warning_modal": True,
                "modal_element_id": "userFormModal",
                "target_element_id": "user_table",
                "delete_warning": f"Weet je zeker dat je {user.first_name} {user.last_name} wilt verwijderen?",
                "form_post_url": reverse("user-delete", kwargs={"pk": pk}),
                "form_button_label": "Verwijderen",
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
            context=context,
        )
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("admin-users")
        return response
    return HttpResponse(status=405)


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

        try:
            csv_content = csv_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return render(
                request,
                "user_import.html",
                {"result": {"success": False, "errors": ["Ongeldige bestandscodering. Gebruik UTF-8."]}},
            )

        result = create_users_from_csv(request.user, csv_content)

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

        try:
            csv_content = csv_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return render(
                request,
                "assignment_import.html",
                {"result": {"success": False, "errors": ["Invalid CSV file encoding. Please use UTF-8."]}},
            )

        result = create_assignments_from_csv(request.user, csv_content)

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
            hx_redirect = reverse("label-admin")
            # redirecting to part of the page does using anchor does not seem to work yet
            response["HX-Redirect"] = hx_redirect
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


@permission_required("core.delete_labelcategory", raise_exception=True)
def label_category_delete(request, pk):
    """
    To be used with htmx
    """
    category = get_object_or_404(LabelCategory, pk=pk)
    if request.method == "GET":
        return render(
            request,
            "parts/generic_form_modal.html",
            {
                "modal_title": f"Verwijder categorie: {category.name}",
                "warning_modal": True,
                "modal_element_id": "labelFormModal",
                "target_element_id": "labelFormModal",
                "delete_warning": (
                    f"Weet je zeker dat je deze categorie wilt verwijderen? "
                    f"Dit verwijdert ook alle {category.labels.count()} labels."
                ),
                "form_post_url": reverse("label-category-delete", kwargs={"pk": pk}),
                "form_button_label": "Verwijderen",
            },
        )
    if request.method == "POST":
        category_name = category.name  # Store name before deleting
        category.delete()
        messages.success(request, f"Categorie '{category_name}' succesvol verwijderd")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("label-admin")
        return response
    return HttpResponse(status=405)


@permission_required("core.add_label", raise_exception=True)
def label_create(request, pk):
    """
    Returns a partial html page, to be used with htmx
    """

    if request.method == "POST":
        category = get_object_or_404(LabelCategory, pk=pk)
        form = LabelForm(request.POST, category_id=category.id)
        if form.is_valid():
            new_instance = form.save(commit=False)
            new_instance.category = category
            new_instance.save()

            category_qs = LabelCategory.objects.filter(id=category.id)
            category = annotate_usage_counts(category_qs).get()

            return render(request, "parts/label_category.html", {"category": category})
        errors = dict(form.errors.items())
        return render(
            request,
            "parts/label_category.html",
            {
                "category": category,
                "errors": errors,
            },
        )
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
    events = (
        Event.objects.filter(
            object_type="Assignment",
            object_id=assignment.id,
        )
        .select_related("user__colleague")
        .order_by("-timestamp")[:20]
    )
    return render(request, "parts/assignment_events_timeline.html", {"events": events})


def user_profile(request):
    """User's own profile page with editable fields and full assignment history."""
    user = request.user
    colleague = getattr(user, "colleague", None)

    # Side panel handling
    colleague_id = request.GET.get("collega")
    assignment_id = request.GET.get("opdracht")
    panel_data = None

    if assignment_id:
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            panel_data = _build_assignment_panel_data(assignment, request, reverse("home"))
        except Assignment.DoesNotExist:
            pass
    elif colleague_id:
        try:
            panel_colleague = Colleague.objects.get(id=colleague_id)
            panel_data = _build_colleague_panel_data(panel_colleague, request)
        except Colleague.DoesNotExist:
            pass

    # HTMX partial responses for panel swaps
    if "HX-Request" in request.headers:
        hx_target = request.headers.get("HX-Target")
        if hx_target == "side_panel-container" and panel_data:
            return render(request, "parts/side_panel.html", {"panel_data": panel_data})
        if hx_target == "side_panel-content" and panel_data:
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


@login_not_required
def contact(request):
    return render(request, "contact.html")


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
        total_forms = min(int(request.POST.get("service-TOTAL_FORMS", 0)), 100)
        has_any_service = any(request.POST.get(f"service-{i}-skill") for i in range(total_forms))
        services_error = "" if has_any_service else "Voeg minimaal één dienst toe."

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
    return render(request, "parts/search_suggestions.html", {"org_suggestions": orgs})


def _get_org_counts(count_mode: str, excluded_org_ids: list[int]) -> Counter[int]:
    """Return per-org self-counts based on count_mode."""
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
        active_placements = annotate_placement_dates(Placement.objects.all()).filter(
            actual_end_date__gte=timezone.now().date()
        )
        if excluded_org_ids:
            active_placements = active_placements.exclude(service__assignment__organizations__id__in=excluded_org_ids)
        org_id_list = active_placements.values_list("service__assignment__organizations__id", flat=True)
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

    org_self_counts = _get_org_counts(count_mode, excluded_org_ids)
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


def _permission_denied(
    editable_set: type[EditableSet],
    spec: Editable | EditableGroup | EditableCollection,
    user,
    obj,
) -> dict | None:
    """Return the denial alert when the user can't UPDATE this field; None when allowed.

    Permission lookup goes through the registry in
    ``wies.core.permission_rules``. Field-level rules win over the
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
        "url": reverse("inline-edit", args=[model_label, obj.pk, spec.name]),
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
    # `saved=True` triggers the pencil→check flash; `alert` carries a denial warning.
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
    ctx = {
        **_inline_edit_base_ctx(editable_set, spec, obj),
        "value": value,
        "display": display,
        "user_can_edit": (
            user_can_edit
            if user_can_edit is not None
            else _permission_denied(editable_set, spec, request.user, obj) is None
        ),
        "alert": alert,
        "saved": saved,
    }
    return render(request, "parts/inline_edit/display.html", ctx)


def _render_inline_edit_form(request, editable_set, spec, editables, obj, form) -> HttpResponse:
    # Edit-mode partial: form + save/cancel. On validation failure, `form` carries inline errors.
    ctx = {**_inline_edit_base_ctx(editable_set, spec, obj), "form": form}
    return render(request, "parts/inline_edit/form.html", ctx)


def _render_inline_edit_collection_form(request, editable_set, spec, obj, formset) -> HttpResponse:
    # Inner body from spec.form_template; receives the formset as `formset`.
    ctx = {**_inline_edit_base_ctx(editable_set, spec, obj), "formset": formset}
    return render(request, "parts/inline_edit/collection_form.html", ctx)


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
            try:
                spec.save(obj, formset)
            except ValidationError as exc:
                for message in exc.messages:
                    _attach_formset_error(formset, message)
                return _render_inline_edit_collection_form(request, editable_set, spec, obj, formset)
            return _render_inline_edit_display(request, editable_set, spec, editables=[], obj=obj, saved=True)
        return _render_inline_edit_collection_form(request, editable_set, spec, obj, formset)

    if request.GET.get("cancel"):
        return _render_inline_edit_display(request, editable_set, spec, editables=[], obj=obj)
    if request.GET.get("edit"):
        formset = spec.formset_factory(initial=spec.initial(obj))
        return _render_inline_edit_collection_form(request, editable_set, spec, obj, formset)
    return _render_inline_edit_display(request, editable_set, spec, editables=[], obj=obj)


_AUDIT_OBJECT_TYPES = {"Assignment": "Assignment", "User": "User", "OrganizationUnit": "OrganizationUnit"}


def _emit_inline_edit_audit_event(spec, obj, old_value, new_value, user) -> None:
    """Record an audit event for a single-Editable change on a tracked model.

    Only fires for `Editable` (not Group/Collection) on models in
    `_AUDIT_OBJECT_TYPES`. No-op when old == new so editing without a
    real change doesn't create noise.
    """
    if not isinstance(spec, Editable):
        return
    object_type = _AUDIT_OBJECT_TYPES.get(type(obj).__name__)
    if object_type is None:
        return
    if str(old_value or "") == str(new_value or ""):
        return
    from django import forms  # noqa: PLC0415

    widget = spec.widget
    is_textarea = isinstance(widget, forms.Textarea) or (
        isinstance(widget, type) and issubclass(widget, forms.Textarea)
    )
    create_event(
        object_type=object_type,
        action="update",
        source="user",
        object_id=obj.id,
        user=user,
        context={
            "field_type": "textarea" if is_textarea else "text",
            "field_name": spec.field or spec.name or "",
            "field_label": spec.label or spec.name or "",
            "old_value": str(old_value or ""),
            "new_value": str(new_value or ""),
        },
    )


def inline_edit_view(request, model_label, pk, name):
    """Generic HTMX endpoint. See ``features/inline-editing.md`` for the full contract."""
    editable_set = REGISTRY.get(model_label)
    if editable_set is None:
        raise Http404("Unknown model")
    spec = editable_set._editables.get(name) or editable_set.resolve_dynamic(name)
    if spec is None:
        raise Http404("Unknown editable")

    obj = get_object_or_404(editable_set.model, pk=pk)

    # Permission ladder — denial always returns display partial with alert.
    denial = _permission_denied(editable_set, spec, request.user, obj)
    if denial:
        editables_for_display: list[Editable] = (
            [] if isinstance(spec, EditableCollection) else resolve_editables(editable_set, spec)
        )
        return _render_inline_edit_display(
            request,
            editable_set,
            spec,
            editables_for_display,
            obj,
            alert=denial,
            user_can_edit=False,
        )

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
            old_value = _current_value(obj, spec) if isinstance(spec, Editable) else None
            save_spec(spec, editables, form.cleaned_data, obj)
            new_value = _current_value(obj, spec) if isinstance(spec, Editable) else None
            _emit_inline_edit_audit_event(spec, obj, old_value, new_value, request.user)
            return _render_inline_edit_display(
                request,
                editable_set,
                spec,
                editables,
                obj,
                saved=True,
            )
        return _render_inline_edit_form(request, editable_set, spec, editables, obj, form)

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
