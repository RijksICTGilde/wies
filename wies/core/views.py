import logging
from datetime import date

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
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic.list import ListView

from .forms import LabelCategoryForm, LabelForm, OrganizationUnitForm, UserForm
from .models import (
    Assignment,
    Colleague,
    Label,
    LabelCategory,
    OrganizationType,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    User,
)
from .querysets import annotate_usage_counts
from .roles import user_can_edit_assignment
from .services.events import create_event
from .services.placements import create_placements_from_csv, filter_placements_by_period
from .services.sync import sync_all_otys_iir_records
from .services.users import create_user, create_users_from_csv, update_user

logger = logging.getLogger(__name__)


def get_delete_context(delete_url_name, object_pk, object_name):
    """Helper function to generate delete context for modals"""
    return {
        "delete_url": reverse(delete_url_name, args=[object_pk]),
        "delete_confirm_message": f"Weet je zeker dat je {object_name} wilt verwijderen?",
    }


def htmx_redirect(request, url_name, *args):
    """Return appropriate redirect response for HTMX or regular requests."""
    url = reverse(url_name, args=args) if args else reverse(url_name)
    if "HX-Request" in request.headers:
        response = HttpResponse(status=200)
        response["HX-Redirect"] = url
        return response
    return redirect(url_name, *args)


def modal_context(form, form_post_url, modal_title, button_label, element_id, **extra):
    """Build standard modal context dict."""
    return {
        "content": form,
        "form_post_url": form_post_url,
        "modal_title": modal_title,
        "form_button_label": button_label,
        "modal_element_id": element_id,
        "target_element_id": element_id,
        **extra,
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
    """Display login page or handle login action"""
    if request.method == "GET":
        # Show the login page
        return render(request, "login.html")
    if request.method == "POST":
        # Handle login action
        redirect_uri = request.build_absolute_uri(reverse_lazy("auth"))
        return oauth.oidc.authorize_redirect(request, redirect_uri)
    return None


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
    return redirect("/geen-toegang/")


@login_not_required  # page cannot require login because you land on this after unsuccesful login
def no_access(request):
    return render(request, "no_access.html")


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
            OrganizationUnit.objects.all().delete()
            LabelCategory.objects.all().delete()
            Label.objects.all().delete()
        elif action == "load_data":
            management.call_command("loaddata", "dummy_data.json")
            messages.success(request, "Data loaded successfully from dummy_data.json")
        elif action == "add_dev_user":
            management.call_command("add_developer_user")
            messages.success(request, "Developer user added")
        elif action == "sync_all_otys_records":
            sync_all_otys_iir_records()
            messages.success(request, "All records synced successfully from OTYS IIR")
        return redirect("djadmin-db")

    return render(request, "admin_db.html", context)


class PlacementListView(ListView):
    """View for placements table view with infinite scroll pagination"""

    model = Placement
    template_name = "placement_table.html"
    paginate_by = 50

    def get_queryset(self):
        """Apply filters to placements queryset - only show INGEVULD assignments, not LEAD"""
        qs = (
            Placement.objects.select_related("colleague", "service", "service__skill", "service__assignment")
            .prefetch_related("colleague__labels")
            .filter(service__assignment__status="INGEVULD")
            .order_by("-service__assignment__start_date")
        )

        search_filter = self.request.GET.get("zoek")
        if search_filter:
            qs = qs.filter(
                Q(colleague__name__icontains=search_filter)
                | Q(service__assignment__name__icontains=search_filter)
                | Q(service__assignment__extra_info__icontains=search_filter)
                | Q(service__assignment__organization_relations__organization__name__icontains=search_filter)
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

        # Filtering

        if self.request.GET.get("rol"):
            qs = qs.filter(service__skill__id=self.request.GET["rol"])

        if self.request.GET.get("organisatie"):
            # Hierarchical filter: include selected org and all descendants
            org_id = int(self.request.GET["organisatie"])
            selected_org = OrganizationUnit.objects.filter(id=org_id).first()
            if selected_org:
                org_ids = [org_id] + [d.id for d in selected_org.get_descendants()]
                qs = qs.filter(
                    service__assignment__organization_relations__organization_id__in=org_ids,
                    service__assignment__organization_relations__role="PRIMARY",
                )

        # Label filter support multiselect
        for label_id in self.request.GET.getlist("labels"):
            if label_id != "":
                qs = qs.filter(colleague__labels__id=int(label_id))

        # Apply period filtering for overlapping periods
        periode = self.request.GET.get("periode")
        if periode:
            qs = filter_placements_by_period(qs, periode)

        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if "HX-Request" in self.request.headers:
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
        return f"/plaatsingen/?{params.urlencode()}" if params else "/plaatsingen/"

    def _build_assignment_url(self, request, assignment_id):
        """Build assignment panel URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(request.GET)
        params.pop("opdracht", None)
        params["opdracht"] = assignment_id
        return f"/plaatsingen/?{params.urlencode()}"

    def _build_organization_url(self, organization_id):
        """Build organization filter URL"""
        params = QueryDict(mutable=True)
        params["organisatie"] = organization_id
        return f"/plaatsingen/?{params.urlencode()}"

    def _build_colleague_url(self, colleague_id):
        """Build colleague panel URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(self.request.GET)
        params.pop("collega", None)
        params.pop("opdracht", None)
        params["collega"] = colleague_id
        return f"/plaatsingen/?{params.urlencode()}"

    def _get_colleague_assignments(self, colleague):
        """Get assignments for a colleague with organization info"""
        placements = (
            Placement.objects.filter(colleague=colleague)
            .select_related("service__assignment", "service__skill")
            .prefetch_related("service__assignment__organization_relations__organization")
        )
        # Build list with organization from M2M
        results = []
        seen_assignments = set()
        for p in placements:
            assignment = p.service.assignment
            if assignment.id in seen_assignments:
                continue
            seen_assignments.add(assignment.id)
            org = assignment.get_primary_organization()
            results.append(
                {
                    "id": assignment.id,
                    "name": assignment.name,
                    "organization": org.name if org else None,
                    "start_date": assignment.start_date,
                    "end_date": assignment.end_date,
                    "skill": p.service.skill.name if p.service.skill else None,
                }
            )
        return results

    def _get_colleague_panel_data(self, colleague):
        """Get colleague panel data for server-side rendering"""

        colleague_assignments = self._get_colleague_assignments(colleague)
        assignment_list = [
            {
                **item,
                "assignment_url": self._build_assignment_url(self.request, item["id"]),
            }
            for item in colleague_assignments
        ]

        return {
            "panel_content_template": "parts/colleague_panel_content.html",
            "panel_title": colleague.name,
            "close_url": self._build_close_url(self.request),
            "colleague": colleague,
            "assignment_list": assignment_list,
        }

    def _get_assignment_panel_data(self, assignment, colleague):
        """Get assignment panel data for server-side rendering"""
        placements_qs = Placement.objects.filter(service__assignment=assignment).select_related(
            "colleague", "service__skill"
        )

        # Add colleague URLs to placements
        placements = []
        for placement in placements_qs:
            placement.colleague_url = self._build_colleague_url(placement.colleague.id)
            placements.append(placement)

        # Check if user can edit assignment
        user_can_edit = user_can_edit_assignment(self.request.user, assignment)

        primary_org = assignment.get_primary_organization()
        return {
            "panel_content_template": "parts/assignment_panel_content.html",
            "panel_title": assignment.name,
            "close_url": self._build_close_url(self.request),
            "assignment": assignment,
            "placements": placements,
            "organization_url": self._build_organization_url(primary_org.id) if primary_org else "",
            "user_can_edit": user_can_edit,
            "owner_url": self._build_colleague_url(assignment.owner.id) if assignment.owner else "",
        }

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)

        # Add colleague URLs to placement objects
        for placement in context["object_list"]:
            placement.colleague_url = self._build_colleague_url(placement.colleague.id)

        context["search_field"] = "zoek"
        context["search_placeholder"] = "Zoek op collega, opdracht of opdrachtgever..."
        context["search_filter"] = self.request.GET.get("zoek", "")

        active_filters = {}  # key: val
        for filter_param in ["rol", "organisatie", "periode"]:
            val = self.request.GET.get(filter_param)
            if val:
                active_filters[filter_param] = val

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

        label_filter_groups = []
        for category in LabelCategory.objects.all():
            select_label = category.name
            options = [
                {"value": "", "label": ""},
            ]
            value = ""
            for label in Label.objects.filter(category=category):
                options.append({"value": str(label.id), "label": f"{label.name}", "category_color": category.color})
                if str(label.id) in active_filters.get("labels", set()):
                    options[-1]["selected"] = True
                    value = str(label.id)

            filter_group = {
                "type": "select",
                "name": "labels",
                "label": select_label,
                "options": options,
                "value": value,
            }

            label_filter_groups.append(filter_group)

        skill_options = [{"value": "", "label": ""}]
        skill_value = ""
        for skill in Skill.objects.order_by("name"):
            skill_options.append({"value": str(skill.id), "label": skill.name})
            if active_filters.get("rol") == str(skill.id):
                skill_options[-1]["selected"] = True
                skill_value = str(skill.id)

        # Get organizations linked to assignments + their ancestors (for hierarchical filtering)
        linked_org_ids = set(
            Assignment.objects.filter(status="INGEVULD")
            .values_list("organization_relations__organization_id", flat=True)
            .distinct()
        )
        # Add all ancestors so clicking breadcrumb links works
        all_org_ids = set(linked_org_ids)
        for org in OrganizationUnit.objects.filter(id__in=linked_org_ids):
            for ancestor in org.get_ancestors():
                all_org_ids.add(ancestor.id)

        organization_options = [
            {"value": "", "label": ""},
        ]
        organization_value = ""
        for org in OrganizationUnit.objects.filter(id__in=all_org_ids).order_by("name"):
            organization_options.append({"value": str(org.id), "label": org.name})
            if active_filters.get("organisatie") == str(org.id):
                organization_options[-1]["selected"] = True
                organization_value = str(org.id)

        context["active_filters"] = active_filters
        context["active_filter_count"] = len(active_filters)

        # TODO: this can be become an object to help defining correctly and performing extra preprocessing on context
        # introduce value_key, label_key:
        context["filter_groups"] = [
            {
                "type": "select",
                "name": "organisatie",
                "label": "Opdrachtgever",
                "options": organization_options,
                "value": organization_value,
            },
            {
                "type": "select",
                "name": "rol",
                "label": "Rollen",
                "options": skill_options,
                "value": skill_value,
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
            filter_params = []
            for key, value in self.request.GET.items():
                if key != "pagina":  # Exclude page param
                    filter_params.append(f"{key}={value}")
            params_str = "&".join(filter_params)
            next_page = context["page_obj"].next_page_number()
            context["next_page_url"] = f"?pagina={next_page}" + (f"&{params_str}" if params_str else "")
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


class UserListView(PermissionRequiredMixin, ListView):
    """View for user list with filtering and infinite scroll pagination"""

    model = User
    template_name = "user_admin.html"
    paginate_by = 50
    permission_required = "core.view_user"

    def get_queryset(self):
        """Apply filters to users queryset - exclude superusers"""
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

        # Label filter support multiselect
        for label_id in self.request.GET.getlist("labels"):
            if label_id != "":
                qs = qs.filter(labels__id__contains=label_id)

        # Role filter
        role_filter = self.request.GET.get("rol")
        if role_filter:
            qs = qs.filter(groups__id=role_filter)

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
        context["search_placeholder"] = "Zoek op naam of e-mail..."
        context["search_filter"] = self.request.GET.get("zoek", "")

        active_filters = {}

        # label filter supports multi-select
        label_filter = set()
        for label_id in self.request.GET.getlist("labels"):
            if label_id != "":
                label_filter.add(label_id)
        if len(label_filter) > 0:
            active_filters["labels"] = label_filter

        role_filter = self.request.GET.get("rol")
        if role_filter:
            active_filters["rol"] = role_filter

        label_filter_groups = []
        for category in LabelCategory.objects.all():
            select_label = category.name
            options = [
                {"value": "", "label": "Allemaal"},
            ]
            value = ""
            for label in Label.objects.filter(category=category):
                options.append({"value": str(label.id), "label": f"{label.name}"})
                if str(label.id) in active_filters.get("labels", set()):
                    options[-1]["selected"] = True
                    value = str(label.id)

            filter_group = {
                "type": "select",
                "name": "labels",
                "label": select_label,
                "options": options,
                "value": value,
            }

            label_filter_groups.append(filter_group)

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
            filter_params = []
            for key, value in self.request.GET.items():
                if key != "pagina":
                    filter_params.append(f"{key}={value}")
            params_str = "&".join(filter_params)
            next_page = context["page_obj"].next_page_number()
            context["next_page_url"] = f"?pagina={next_page}" + (f"&{params_str}" if params_str else "")
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
def placement_import_csv(request):
    """
    Import placements from a CSV file.

    GET: Display the import form
    POST: Process the uploaded CSV file and create placements
          (with related assignments, services, colleagues, and skills)

    For expected CSV format, see create_placements_from_csv function
    """
    if request.method == "GET":
        return render(request, "placement_import.html")
    if request.method == "POST":
        if "csv_file" not in request.FILES:
            return render(
                request,
                "placement_import.html",
                {"result": {"success": False, "errors": ["Geen bestand geüpload. Upload een CSV-bestand."]}},
            )

        csv_file = request.FILES["csv_file"]

        if not csv_file.name.endswith(".csv"):
            return render(
                request,
                "placement_import.html",
                {"result": {"success": False, "errors": ["Ongeldig bestandstype. Upload een CSV-bestand."]}},
            )

        try:
            csv_content = csv_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return render(
                request,
                "placement_import.html",
                {"result": {"success": False, "errors": ["Invalid CSV file encoding. Please use UTF-8."]}},
            )

        result = create_placements_from_csv(csv_content)

        # Return results in the form
        return render(request, "placement_import.html", {"result": result})
    return HttpResponse(status=405)


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


# === OrganizationUnit Admin Views ===


class OrganizationUnitListView(PermissionRequiredMixin, ListView):
    """View for organization unit list with filtering."""

    model = OrganizationUnit
    template_name = "organization_admin.html"
    context_object_name = "organizations"
    permission_required = "core.view_organizationunit"

    def get_queryset(self):
        """Filter organizations (active only)."""
        qs = OrganizationUnit.objects.active().select_related("parent").order_by("name")

        # Search filter (JSONFields searched via icontains on text representation)
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(abbreviations__icontains=search) | Q(previous_names__icontains=search)
            )

        # Type filter
        org_type = self.request.GET.get("type")
        if org_type:
            qs = qs.filter(organization_type=org_type)

        # Top-level filter (optional)
        top_level_only = self.request.GET.get("toplevel") == "1"
        if top_level_only:
            qs = qs.filter(parent__isnull=True)

        return qs

    def get_template_names(self):
        """Return appropriate template based on request type."""
        if "HX-Request" in self.request.headers:
            return ["parts/organization_table.html"]
        return ["organization_admin.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["search_placeholder"] = "Zoek op naam of afkorting..."
        context["search_filter"] = self.request.GET.get("search", "")

        # Build filter options
        type_options = [{"value": "", "label": "Alle types"}]
        current_type = self.request.GET.get("type", "")
        for choice in OrganizationType.choices:
            opt = {"value": choice[0], "label": choice[1]}
            if choice[0] == current_type:
                opt["selected"] = True
            type_options.append(opt)

        # Top-level filter
        top_level_only = self.request.GET.get("toplevel") == "1"
        toplevel_options = [
            {"value": "", "label": "Alle organisaties"},
            {"value": "1", "label": "Alleen top-level", "selected": top_level_only},
        ]

        context["filter_groups"] = [
            {
                "type": "select",
                "name": "type",
                "label": "Type",
                "options": type_options,
                "value": current_type,
            },
            {
                "type": "select",
                "name": "toplevel",
                "label": "Niveau",
                "options": toplevel_options,
                "value": "1" if top_level_only else "",
            },
        ]

        # Count active filters
        active_filter_count = 0
        if current_type:
            active_filter_count += 1
        if top_level_only:
            active_filter_count += 1

        context["active_filter_count"] = active_filter_count

        context["primary_button"] = {
            "button_text": "Organisatie-eenheid toevoegen",
            "attrs": {
                "hx-get": reverse("organization-create"),
                "hx-target": "#organizationFormModal",
                "hx-push-url": "false",
            },
        }

        return context


@permission_required("core.add_organizationunit", raise_exception=True)
def organization_create(request):
    """Handle organization unit creation."""
    template = "parts/organization_form_modal.html"
    ctx_base = {
        "form_post_url": reverse("organization-create"),
        "modal_title": "Nieuwe organisatie-eenheid",
        "element_id": "organizationFormModal",
    }

    if request.method == "GET":
        form = OrganizationUnitForm()
        return render(request, template, modal_context(form, **ctx_base, button_label="Toevoegen"))

    if request.method == "POST":
        form = OrganizationUnitForm(request.POST)
        if form.is_valid():
            form.save()
            return htmx_redirect(request, "organization-list")
        return render(request, template, modal_context(form, **ctx_base, button_label="Toevoegen"))

    return HttpResponse(status=405)


@permission_required("core.change_organizationunit", raise_exception=True)
def organization_edit(request, pk):
    """Handle organization unit editing."""
    organization = get_object_or_404(OrganizationUnit, pk=pk)
    template = "parts/organization_form_modal.html"
    has_children = organization.children.exists()
    has_assignments = organization.assignment_relations.exists()
    has_tooi = bool(organization.tooi_identifier)
    # Can't delete if has TOOI, children, or assignments
    can_delete = not has_tooi and not has_children and not has_assignments
    delete_ctx = get_delete_context("organization-delete", pk, organization.name) if can_delete else {}
    ctx_base = {
        "form_post_url": reverse("organization-edit", args=[pk]),
        "modal_title": "Organisatie-eenheid bewerken",
        "element_id": "organizationFormModal",
    }

    if request.method == "GET":
        form = OrganizationUnitForm(instance=organization)
        ctx = modal_context(
            form,
            **ctx_base,
            button_label="Opslaan",
            has_children=has_children,
            has_assignments=has_assignments,
            has_tooi=has_tooi,
            organization=organization,
            **delete_ctx,
        )
        return render(request, template, ctx)

    if request.method == "POST":
        form = OrganizationUnitForm(request.POST, instance=organization)
        if form.is_valid():
            form.save()
            return htmx_redirect(request, "organization-list")
        ctx = modal_context(
            form,
            **ctx_base,
            button_label="Opslaan",
            has_children=has_children,
            has_assignments=has_assignments,
            has_tooi=has_tooi,
            organization=organization,
            **delete_ctx,
        )
        return render(request, template, ctx)

    return HttpResponse(status=405)


@permission_required("core.delete_organizationunit", raise_exception=True)
def organization_delete(request, pk):
    """Handle organization unit deletion (soft delete)."""
    organization = get_object_or_404(OrganizationUnit, pk=pk)
    element_id = "organizationFormModal"

    def _render_cannot_delete(message):
        if "HX-Request" in request.headers:
            return render(
                request,
                "parts/generic_form_modal.html",
                {
                    "modal_title": "Kan niet verwijderen",
                    "modal_element_id": element_id,
                    "target_element_id": element_id,
                    "delete_warning": message,
                    "form_post_url": reverse("organization-edit", args=[pk]),
                    "form_button_label": "Terug",
                    "warning_modal": True,
                },
            )
        return HttpResponse(message, status=400)

    # Block deletion if organization has TOOI identifier (synced from government registry)
    if organization.tooi_identifier:
        return _render_cannot_delete(
            f"'{organization.name}' komt uit het overheidsregister (TOOI) en kan niet worden verwijderd."
        )

    # Block deletion if organization has children
    if organization.children.exists():
        return _render_cannot_delete(
            f"'{organization.name}' heeft onderliggende eenheden. Verwijder of verplaats deze eerst."
        )

    # Block deletion if organization has assignments
    if organization.assignment_relations.exists():
        return _render_cannot_delete(f"'{organization.name}' heeft gekoppelde opdrachten.")

    if request.method == "GET":
        return render(
            request,
            "parts/generic_form_modal.html",
            {
                "modal_title": f"Verwijder organisatie-eenheid: {organization.name}",
                "warning_modal": True,
                "modal_element_id": element_id,
                "target_element_id": "organization_table",
                "delete_warning": f"Weet je zeker dat je '{organization.name}' wilt verwijderen?",
                "form_post_url": reverse("organization-delete", kwargs={"pk": pk}),
                "form_button_label": "Verwijderen",
            },
        )

    if request.method == "POST":
        organization.delete()  # Soft delete
        return htmx_redirect(request, "organization-list")

    return HttpResponse(status=405)
