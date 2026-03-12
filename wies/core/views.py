import logging
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate as auth_authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_not_required, permission_required, user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core import management
from django.db.models import Case, Prefetch, Q, Value, When
from django.db.models.functions import Concat
from django.http import Http404, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic.list import ListView

from .forms import LabelCategoryForm, LabelForm, UserForm
from .models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    User,
)
from .querysets import annotate_placement_dates, annotate_usage_counts
from .roles import user_can_edit_assignment
from .services.events import create_event
from .services.organizations import get_excluded_org_ids, get_org_breadcrumb, get_org_descendant_ids
from .services.placements import (
    create_assignments_from_csv,
    filter_placements_by_min_end_date,
    filter_placements_by_period,
)
from .services.sync import sync_all_otys_iir_records
from .services.tasks import create_task, get_latest_tasks, has_active_task
from .services.users import create_user, create_users_from_csv, is_allowed_email_domain, update_user

logger = logging.getLogger(__name__)

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


oauth = OAuth()
oauth.register(
    name="oidc",
    server_metadata_url=settings.OIDC_DISCOVERY_URL,
    client_id=settings.OIDC_CLIENT_ID,
    client_secret=settings.OIDC_CLIENT_SECRET,
    client_kwargs={"scope": "openid profile email"},
)


@login_not_required  # login page cannot require login
def login(request):
    """Redirect directly to Keycloak for authentication"""
    redirect_uri = request.build_absolute_uri(reverse_lazy("auth"))
    return oauth.oidc.authorize_redirect(request, redirect_uri)


@login_not_required  # called by oidc, cannot have login
def auth(request):
    oidc_response = oauth.oidc.authorize_access_token(request)
    username = oidc_response["userinfo"]["sub"]
    first_name = oidc_response["userinfo"]["given_name"]
    last_name = oidc_response["userinfo"]["family_name"]
    email = oidc_response["userinfo"]["email"]
    user = auth_authenticate(
        request, username=username, email=email, extra_fields={"first_name": first_name, "last_name": last_name}
    )
    if user:
        auth_login(request, user)
        logger.info("login successful, access granted")
        create_event(user.email, "Login.success")
        return redirect(request.build_absolute_uri(reverse("home")))

    logger.info("login not successful, access denied")
    # Store email for no_access page
    request.session["failed_login_email"] = email
    return redirect("/geen-toegang/")


@login_not_required  # page cannot require login because you land on this after unsuccesful login
def no_access(request):
    email = request.session.pop("failed_login_email", None)
    is_allowed_domain = email and is_allowed_email_domain(email)
    return render(request, "no_access.html", {"email": email, "is_allowed_domain": is_allowed_domain})


@login_not_required  # logout should be accessible without login
def logout(request):
    if request.user and request.user.is_authenticated:
        auth_logout(request)
    return redirect(reverse("login"))


@user_passes_test(lambda u: u.is_superuser and u.is_authenticated, login_url="/djadmin/login/")
def admin_db(request):
    context = {
        "assignment_count": Assignment.objects.count(),
        "colleague_count": Colleague.objects.count(),
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
        elif action == "load_base_data":
            management.call_command("loaddata", "base_dummy_data.json")
            messages.success(request, "Data geladen uit base_dummy_data.json")
        elif action == "add_dev_user":
            management.call_command("add_developer_user")
            messages.success(request, "Developer user added")
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
                return redirect("djadmin-db")

            json_file = request.FILES["json_file"]

            # Validate file extension
            if not json_file.name.endswith(".json"):
                messages.error(request, "Ongeldig bestandstype. Upload een JSON-bestand.")
                return redirect("djadmin-db")

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

                # Load data using Django's loaddata command
                management.call_command("loaddata", tmp_path)
                messages.success(request, "Database succesvol geïmporteerd")
            except Exception as e:  # noqa: BLE001
                # Catch all exceptions to show user-friendly error message
                messages.error(request, f"Import mislukt: {e!s}")
            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)

            return redirect("djadmin-db")
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

            return redirect("djadmin-db")
        return redirect("djadmin-db")

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
            .filter(service__assignment__status="INGEVULD")
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
                | Q(service__assignment__organizations__name__icontains=search_filter)
                | Q(service__assignment__organizations__label__icontains=search_filter)
                | Q(service__assignment__organizations__abbreviations__icontains=search_filter)
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
        qs = filter_placements_by_min_end_date(qs, timezone.now().date())

        # Apply period filtering for overlapping periods
        periode = self.request.GET.get("periode")
        if periode and "_" in periode:
            try:
                period_from_str, period_to_str = periode.split("_", 1)
                period_from = date.fromisoformat(period_from_str)
                period_to = date.fromisoformat(period_to_str)
                qs = filter_placements_by_period(qs, period_from, period_to)
            except Value:
                pass  # Invalid date format, ignore filter

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

        exclude_filter can be: "rol", "org", or a category_id (int) for labels.
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
                return ["parts/side_panel_response.html"]
            if self.request.headers.get("HX-Target") == "side_panel-content":
                return ["parts/side_panel_content_response.html"]
            if self.request.GET.get("pagina"):
                return ["parts/placement_table_rows.html"]
            return ["parts/filter_and_table_container.html"]
        return ["placement_table.html"]

    def _build_close_url(self, request):
        """Build close URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(request.GET)
        params.pop("collega", None)
        params.pop("opdracht", None)
        return f"{reverse('home')}?{params.urlencode()}" if params else reverse("home")

    def _build_assignment_url(self, request, assignment_id):
        """Build assignment panel URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(request.GET)
        params.pop("opdracht", None)
        params["opdracht"] = assignment_id
        return f"{reverse('home')}?{params.urlencode()}"

    def _build_colleague_url(self, colleague_id):
        """Build colleague panel URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(self.request.GET)
        params.pop("collega", None)
        params.pop("opdracht", None)
        params["collega"] = colleague_id
        return f"{reverse('home')}?{params.urlencode()}"

    def _get_colleague_placements(self, colleague):
        """Get assignments for a colleague"""
        return (
            Placement.objects.filter(colleague=colleague)
            .select_related("service__assignment", "service__skill")
            .values(
                "id",
                "service__assignment__id",
                "service__assignment__name",
                "service__assignment__start_date",
                "service__assignment__end_date",
                "service__skill__name",
            )
            .distinct()
        )

    def _get_colleague_panel_data(self, colleague):
        """Get colleague panel data for server-side rendering"""

        placement_qs = self._get_colleague_placements(colleague)

        # filter out historical placements
        placement_qs = annotate_placement_dates(placement_qs)
        placement_qs = filter_placements_by_min_end_date(placement_qs, timezone.now().date())

        assignment_list = [
            {
                "name": item["service__assignment__name"],
                "id": item["service__assignment__id"],
                "start_date": item["service__assignment__start_date"],
                "end_date": item["service__assignment__end_date"],
                "skill": item["service__skill__name"],
                "assignment_url": self._build_assignment_url(self.request, item["service__assignment__id"]),
            }
            for item in placement_qs
        ]

        return {
            "panel_content_template": "parts/colleague_panel_content.html",
            "panel_title": colleague.name,
            "close_url": self._build_close_url(self.request),
            "colleague": colleague,
            "assignment_list": assignment_list,
        }

    @staticmethod
    def _get_org_breadcrumb(org: OrganizationUnit) -> dict:
        """Build breadcrumb data for an organization: label + clickable ancestor path."""
        # Walk up to build ancestor chain (excluding the org itself)
        ancestors = []
        current = org.parent
        while current:
            label = current.abbreviation or current.label or current.name
            ancestors.append({"label": label, "url": f"/?org={current.id}"})
            current = current.parent
        ancestors.reverse()  # root → ... → direct parent

        # Determine if this org is a "self-node": has children with assignment links
        is_self = org.children.filter(assignment_relations__isnull=False).exists()

        label = org.label or org.name
        url = f"/?org_self={org.id}" if is_self else f"/?org={org.id}"

        return {"label": label, "url": url, "ancestors": ancestors}

    def _get_assignment_panel_data(self, assignment, colleague):
        """Get assignment panel data for server-side rendering"""
        # Fetch services with their current placements
        services = assignment.services.select_related("skill").prefetch_related(
            Prefetch(
                "placements",
                queryset=filter_placements_by_min_end_date(
                    annotate_placement_dates(Placement.objects.select_related("colleague")),
                    timezone.now().date(),
                ),
                to_attr="current_placements",
            )
        )

        # Add colleague URLs to placements
        for service in services:
            for placement in service.current_placements:
                placement.colleague_url = self._build_colleague_url(placement.colleague.id)

        # Check if user can edit assignment
        user_can_edit = user_can_edit_assignment(self.request.user, assignment)

        # Build organization breadcrumbs (primary first, then involved)
        primary = assignment.organization_relations.filter(role="PRIMARY").select_related(
            "organization__parent__parent__parent__parent"
        )
        involved = assignment.organization_relations.filter(role="INVOLVED").select_related(
            "organization__parent__parent__parent__parent"
        )
        org_breadcrumbs = [
            {**self._get_org_breadcrumb(rel.organization), "role": rel.role} for rel in [*primary, *involved]
        ]

        return {
            "panel_content_template": "parts/assignment_panel_content.html",
            "panel_title": assignment.name,
            "close_url": self._build_close_url(self.request),
            "assignment": assignment,
            "services": services,
            "user_can_edit": user_can_edit,
            "owner_url": self._build_colleague_url(assignment.owner.id) if assignment.owner else "",
            "org_breadcrumbs": org_breadcrumbs,
        }

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)
        context["render_filter_fields_oob"] = "HX-Request" in self.request.headers

        # Add colleague URLs to placement objects
        for placement in context["object_list"]:
            placement.colleague_url = self._build_colleague_url(placement.colleague.id)

        context["filter_target_url"] = reverse("home")
        context["search_field"] = "zoek"
        context["search_placeholder"] = "Zoek op collega, opdracht of opdrachtgever..."
        context["search_filter"] = self.request.GET.get("zoek")

        active_filters: dict = {}
        for filter_param in ["periode"]:
            val = self.request.GET.get(filter_param)
            if val:
                active_filters[filter_param] = val

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

        if active_filters.get("periode"):
            periode_from, periode_to = active_filters["periode"].split("_")
            active_filters["periode"] = {
                "from": date.fromisoformat(periode_from),
                "to": date.fromisoformat(periode_to),
            }

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
                "type": "date_range",
                "name": "periode",
                "label": "Periode",
                "from_label": "Van",
                "to_label": "Tot",
                "require_both": True,
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

        # if one or both of the ids are invalid, the panel_data is skipped
        if colleague_id and not assignment_id:
            try:
                colleague = Colleague.objects.get(id=colleague_id)
                context["panel_data"] = self._get_colleague_panel_data(colleague)
            except Colleague.DoesNotExist:
                pass
        elif colleague_id and assignment_id:
            try:
                colleague = Colleague.objects.get(id=colleague_id)
                assignment = Assignment.objects.get(id=assignment_id)
                context["panel_data"] = self._get_assignment_panel_data(assignment, colleague)
            except (Colleague.DoesNotExist, Assignment.DoesNotExist):
                pass
        return context


class AssignmentListView(ListView):
    """View for vacancy assignments displayed as cards with infinite scroll pagination"""

    model = Assignment
    template_name = "assignment_card_grid.html"
    paginate_by = 24
    page_kwarg = "pagina"

    def _get_base_queryset(self):
        qs = Assignment.objects.filter(status="OPEN").order_by("-created_at")
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
                qs = qs.filter(services__skill__id__in=rol_filter)

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
                queryset=Service.objects.filter(skill__isnull=False).select_related("skill"),
                to_attr="services_with_skills",
            )
        )

    def get_template_names(self):
        if "HX-Request" in self.request.headers:
            if self.request.headers.get("HX-Target") == "side_panel-container":
                return ["parts/side_panel_response.html"]
            if self.request.headers.get("HX-Target") == "side_panel-content":
                return ["parts/side_panel_content_response.html"]
            if self.request.GET.get("pagina"):
                return ["parts/assignment_card_rows.html"]
            return ["parts/filter_and_card_container.html"]
        return ["assignment_card_grid.html"]

    def _build_close_url(self):
        params = QueryDict(mutable=True)
        params.update(self.request.GET)
        params.pop("opdracht", None)
        base = reverse("assignment-list")
        return f"{base}?{params.urlencode()}" if params else base

    def _build_panel_url(self, assignment_id):
        params = QueryDict(mutable=True)
        params.update(self.request.GET)
        params.pop("opdracht", None)
        params["opdracht"] = assignment_id
        return f"{reverse('assignment-list')}?{params.urlencode()}"

    def _get_vacancy_panel_data(self, assignment):
        # Fetch services with their current placements
        services = assignment.services.select_related("skill").prefetch_related(
            Prefetch(
                "placements",
                queryset=filter_placements_by_min_end_date(
                    annotate_placement_dates(Placement.objects.select_related("colleague")),
                    timezone.now().date(),
                ),
                to_attr="current_placements",
            )
        )

        # Build organization breadcrumbs from organization_relations
        base_url = reverse("assignment-list")
        primary = assignment.organization_relations.filter(role="PRIMARY").select_related(
            "organization__parent__parent__parent__parent"
        )
        involved = assignment.organization_relations.filter(role="INVOLVED").select_related(
            "organization__parent__parent__parent__parent"
        )
        org_breadcrumbs = [
            {**get_org_breadcrumb(rel.organization, base_url), "role": rel.role} for rel in [*primary, *involved]
        ]

        return {
            "panel_content_template": "parts/assignment_panel_content.html",
            "panel_title": assignment.name,
            "close_url": self._build_close_url(),
            "assignment": assignment,
            "services": services,
            "org_breadcrumbs": org_breadcrumbs,
            "owner_url": reverse("home") + f"?collega={assignment.owner.id}" if assignment.owner else "",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["render_filter_fields_oob"] = "HX-Request" in self.request.headers

        base_url = reverse("assignment-list")
        for assignment in context["object_list"]:
            assignment.panel_url = self._build_panel_url(assignment.id)
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

        # Side panel
        assignment_id = self.request.GET.get("opdracht")
        if assignment_id:
            try:
                assignment = Assignment.objects.select_related("owner").get(id=assignment_id, status="OPEN")
                context["panel_data"] = self._get_vacancy_panel_data(assignment)
            except Assignment.DoesNotExist:
                pass

        return context


class UserListView(PermissionRequiredMixin, ListView):
    """View for user list with filtering and infinite scroll pagination"""

    model = User
    template_name = "user_admin.html"
    paginate_by = 50
    page_kwarg = "pagina"
    permission_required = "core.view_user"

    def _get_base_queryset(self):
        """Base queryset with search applied."""
        qs = (
            User.objects.prefetch_related("groups", "labels__category")
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
                qs = qs.filter(labels__id__in=cat_label_ids)

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
            cat_label_ids = cat_user_qs.values_list("labels__id", flat=True)
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


@permission_required("core.add_user", raise_exception=True)
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


@permission_required("core.change_user", raise_exception=True)
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


@permission_required("core.delete_user", raise_exception=True)
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
        label_names = [label.name for label in user.labels.all()]
        context = {
            "id": pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "label_names": label_names,
            "group_names": [g.name for g in user.groups.all()],
        }
        user.delete()
        create_event(request.user.email, "User.delete", context)
        response = HttpResponse(status=200)
        response["HX-Redirect"] = reverse("admin-users")
        return response
    return HttpResponse(status=405)


@permission_required("core.add_user", raise_exception=True)
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
            return {"success": False, "errors": ["Invalid CSV file encoding. Please use UTF-8."]}

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

        result = create_assignments_from_csv(csv_content)

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

    label_use_count = label.users.count() + label.colleagues.count()

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


# Configuration for editable assignment fields
EDITABLE_ASSIGNMENT_FIELDS = {
    "name": {
        "field_type": "text",
        "field_name": "name",
        "max_length": 200,
        "required": True,
        "label": "Opdracht naam",
        "display_template": "parts/editable_text_field.html",
        "form_template": "parts/editable_text_field_form.html",
        "target_element": "assignment-name-content",
    },
    "extra_info": {
        "field_type": "textarea",
        "field_name": "extra_info",
        "max_length": 5000,
        "required": False,
        "label": "Beschrijving",
        "display_template": "parts/editable_textarea_field.html",
        "form_template": "parts/editable_textarea_field_form.html",
        "target_element": "assignment-extra-info-content",
    },
}


# Permission check is done in function body, not decorator
def assignment_edit_attribute(request, pk, attribute):
    """
    Generic inline editor for assignment attributes.
    Handles both GET (show form) and POST (save) for any configured attribute.
    Returns a partial html page, to be used with htmx.

    Args:
        request: HttpRequest object
        pk: Assignment primary key
        attribute: Name of the attribute to edit (must be in EDITABLE_ASSIGNMENT_FIELDS)
    """
    # Validate attribute
    if attribute not in EDITABLE_ASSIGNMENT_FIELDS:
        return HttpResponse(status=404)

    field_config = EDITABLE_ASSIGNMENT_FIELDS[attribute]
    assignment = get_object_or_404(Assignment, pk=pk)

    # Check if user is authorized: has permission OR is owner OR is assigned colleague
    if not user_can_edit_assignment(request.user, assignment):
        return HttpResponse(status=403)

    # Build edit URL
    edit_url = reverse("assignment-edit-attribute", kwargs={"pk": assignment.id, "attribute": attribute})

    if request.method == "POST":
        # Process form submission
        field_name = field_config["field_name"]
        new_value = request.POST.get(field_name, "").strip()

        # Validate
        errors = {}
        if field_config["required"] and not new_value:
            errors[field_name] = f"{field_config['label']} is verplicht"
        elif field_config.get("max_length") and len(new_value) > field_config["max_length"]:
            errors[field_name] = f"{field_config['label']} mag maximaal {field_config['max_length']} tekens bevatten"

        if errors:
            # Return form with errors
            return render(
                request,
                field_config["form_template"],
                {
                    "target_element": field_config["target_element"],
                    "field_name": field_name,
                    "field_value": new_value,
                    "edit_url": edit_url,
                    "errors": errors,
                },
            )

        # Save
        setattr(assignment, field_name, new_value)
        assignment.save()

        # Return updated display after save
        return render(
            request,
            field_config["display_template"],
            {
                "target_element": field_config["target_element"],
                "field_label": field_config["label"],
                "field_value": getattr(assignment, field_name),
                "edit_url": edit_url,
                "user_can_edit": True,
            },
        )

    if request.method == "GET":
        current_value = getattr(assignment, field_config["field_name"])

        # Check if this is a cancel request
        if request.GET.get("cancel"):
            # Return display mode
            return render(
                request,
                field_config["display_template"],
                {
                    "target_element": field_config["target_element"],
                    "field_label": field_config["label"],
                    "field_value": current_value,
                    "edit_url": edit_url,
                    "user_can_edit": True,
                },
            )
        # Return edit form
        return render(
            request,
            field_config["form_template"],
            {
                "target_element": field_config["target_element"],
                "field_name": field_config["field_name"],
                "field_value": current_value or "",
                "edit_url": edit_url,
            },
        )

    return HttpResponse(status=405)


@login_not_required
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


def client_modal(request):
    """Return the client tree selection modal (HTMX partial)."""
    excluded_org_ids = get_excluded_org_ids()
    count_mode = request.GET.get("count_mode", "placements")

    if count_mode == "open_assignments":
        # Count open assignments per OrganizationUnit
        assignment_qs = Assignment.objects.filter(status="OPEN")
        if excluded_org_ids:
            assignment_qs = assignment_qs.exclude(organizations__id__in=excluded_org_ids)
        org_id_list = assignment_qs.values_list("organizations__id", flat=True)
        org_self_counts: Counter[int] = Counter(org_id for org_id in org_id_list if org_id is not None)
    else:
        # Count active placements per OrganizationUnit (self-count only — direct link).
        active_placements = annotate_placement_dates(
            Placement.objects.filter(service__assignment__status="INGEVULD")
        ).filter(actual_end_date__gte=timezone.now().date())
        if excluded_org_ids:
            active_placements = active_placements.exclude(service__assignment__organizations__id__in=excluded_org_ids)
        org_id_list = active_placements.values_list("service__assignment__organizations__id", flat=True)
        org_self_counts: Counter[int] = Counter(org_id for org_id in org_id_list if org_id is not None)

    # Load all OrganizationUnits (excluding hidden organizations)
    all_orgs = list(
        OrganizationUnit.objects.exclude(id__in=excluded_org_ids).values(
            "id", "parent_id", "name", "label", "abbreviations"
        )
    )

    # Build lightweight tree in Python
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

    # Compute total counts bottom-up (self + all descendants)
    def compute_total(node: dict) -> int:
        total = node["self_count"]
        for child in node["children_data"]:
            total += compute_total(child)
        node["total_count"] = total
        return total

    for root in roots:
        compute_total(root)

    # Prune branches with zero placements
    def prune(node: dict) -> None:
        node["children_data"] = [c for c in node["children_data"] if c["total_count"] > 0]
        for child in node["children_data"]:
            prune(child)

    for root in roots:
        prune(root)
    roots = [r for r in roots if r["total_count"] > 0]

    def sort_key(node: dict) -> str:
        return node.get("label") or node.get("name") or ""

    # Convert to JSON-serializable tree, injecting self-nodes
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

    # Group roots by OrganizationUnit type (same logic as organization_admin view)
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

    # Build hierarchy: group nodes (not selectable) containing the actual root orgs
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

    # Build current selections dict for state restoration in client_tree.js
    # Maps tree node ID (string) → display label
    current_selections: dict[str, str] = {}

    # normal orgs
    org_ids = [org_id for org_id in request.GET.getlist("org") if org_id.isdigit()]
    for org in OrganizationUnit.objects.filter(id__in=org_ids).values("id", "label"):
        current_selections[org["id"]] = org["label"]

    # self-node orgs
    self_org_ids = [org_id for org_id in request.GET.getlist("org_self") if org_id.isdigit()]
    for org in OrganizationUnit.objects.filter(id__in=self_org_ids).values("id", "label"):
        current_selections[org[f"self-{org['id']}"]] = f'Direct onder "{org["label"]}"'

    # type-node orgs
    for type_label in request.GET.getlist("org_type"):
        if type_label:
            current_selections[f"group-{type_label}"] = ORG_TYPE_PLURAL.get(type_label, type_label)

    return render(
        request,
        "parts/client_modal.html",
        {"hierarchy": hierarchy, "current_selections": current_selections},
    )
