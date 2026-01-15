import logging
from datetime import datetime

from django.views.generic.list import ListView
from django.views.generic import DetailView
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Prefetch, Value, Count
from django.db.models.functions import Concat
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, permission_required
from django.contrib.auth import authenticate as auth_authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core import management
from django.conf import settings
from django.http import HttpResponse, QueryDict
from django.utils.safestring import mark_safe
from django.db.models.functions import Lower
from django.http import HttpResponseNotFound


from authlib.integrations.django_client import OAuth

from .models import Assignment, Colleague, Skill, Placement, Service, Ministry, LabelCategory, Label, User
from .services.sync import sync_all_otys_iir_records
from .services.placements import filter_placements_by_period, create_placements_from_csv
from .services.users import create_user, update_user, create_users_from_csv
from .services.events import create_event
from .forms import UserForm, LabelCategoryForm, LabelForm
from .querysets import annotate_usage_counts


logger = logging.getLogger(__name__)



def get_delete_context(delete_url_name, object_pk, object_name):
    """Helper function to generate delete context for modals"""
    return {
        'delete_url': reverse(delete_url_name, args=[object_pk]),
        'delete_confirm_message': f'Weet je zeker dat je {object_name} wilt verwijderen?',
    }

oauth = OAuth()
oauth.register(
    name='oidc',
    server_metadata_url=settings.OIDC_DISCOVERY_URL,
    client_id=settings.OIDC_CLIENT_ID,
    client_secret=settings.OIDC_CLIENT_SECRET,
    client_kwargs={"scope": "openid profile email"},
)


@login_not_required  # login page cannot require login
def login(request):
    """Display login page or handle login action"""
    if request.method == 'GET':
        # Show the login page
        return render(request, 'login.html')
    elif request.method == 'POST':
        # Handle login action
        redirect_uri = request.build_absolute_uri(reverse_lazy('auth'))
        return oauth.oidc.authorize_redirect(request, redirect_uri)

@login_not_required  # called by oidc, cannot have login
def auth(request):
    oidc_response = oauth.oidc.authorize_access_token(request)
    username = oidc_response['userinfo']['sub']
    first_name = oidc_response['userinfo']['given_name']
    last_name = oidc_response['userinfo']['family_name']
    email = oidc_response['userinfo']['email']
    user = auth_authenticate(request, 
                             username=username,
                             email=email,
                             extra_fields={
                                 'first_name': first_name,
                                 'last_name': last_name
                             }
    )
    if user:
        auth_login(request, user)
        logger.info('login successful, access granted')
        create_event(user.email, 'Login.success')
        return redirect(request.build_absolute_uri(reverse("home")))

    logger.info('login not successful, access denied')
    return redirect('/geen-toegang/')


@login_not_required  # page cannot require login because you land on this after unsuccesful login
def no_access(request):
    return render(request, 'no_access.html')


@login_not_required  # logout should be accessible without login
def logout(request):
    if request.user and request.user.is_authenticated:
        auth_logout(request)
    return redirect(reverse('login'))


@user_passes_test(lambda u: u.is_superuser and u.is_authenticated, login_url='/djadmin/login/')
def admin_db(request):
    context = {
        'assignment_count': Assignment.objects.count(),
        'colleague_count': Colleague.objects.count(),
    }
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'clear_data':
            # not using flush, since that would clear users
            Assignment.objects.all().delete()
            Colleague.objects.all().delete()
            Skill.objects.all().delete()
            Placement.objects.all().delete()
            Service.objects.all().delete()
            Ministry.objects.all().delete()
            LabelCategory.objects.all().delete()
            Label.objects.all().delete()
        elif action == 'load_data':
            management.call_command('loaddata', 'dummy_data.json')
            messages.success(request, 'Data loaded successfully from dummy_data.json')
        elif action == 'add_dev_user':
            management.call_command('add_developer_user')
            messages.success(request, 'Developer user added')
        elif action == 'sync_all_otys_records':
            sync_all_otys_iir_records()
            messages.success(request, 'All records synced successfully from OTYS IIR')
        return redirect('djadmin-db')

    
    return render(request, 'admin_db.html', context)


class PlacementListView(ListView):
    """View for placements table view with infinite scroll pagination"""
    model = Placement
    template_name = 'placement_table.html'
    paginate_by = 50

    def get_queryset(self):
        """Apply filters to placements queryset - only show INGEVULD assignments, not LEAD"""
        qs = Placement.objects.select_related(
            'colleague', 'service', 'service__skill', 'service__assignment__ministry'
        ).prefetch_related('colleague__labels').filter(
            service__assignment__status='INGEVULD'
        ).order_by('-service__assignment__start_date')

        search_filter = self.request.GET.get('zoek')
        if search_filter:
            qs = qs.filter(
                Q(colleague__name__icontains=search_filter) |
                Q(service__assignment__name__icontains=search_filter) |
                Q(service__assignment__extra_info__icontains=search_filter) |
                Q(service__assignment__organization__icontains=search_filter) |
                Q(service__assignment__ministry__name__icontains=search_filter) |
                Q(service__assignment__ministry__abbreviation__icontains=search_filter)
            )

        order_mapping = {
            'name': 'colleague__name',
            'assignment': 'service__assignment__name',
            'skill': 'service__skill__name',
        }

        order_param = self.request.GET.get('order')
        if order_param:
            order_by = order_mapping.get(order_param)
            if order_by:
                qs = qs.order_by(order_by)


        # Filtering

        if self.request.GET.get('rol'):
            qs = qs.filter(service__skill__id=self.request.GET['rol'])

        if self.request.GET.get('opdrachtgever'):
            qs = qs.filter(service__assignment__organization=self.request.GET['opdrachtgever'])

        if self.request.GET.get('ministerie'):
            qs = qs.filter(service__assignment__ministry__id=self.request.GET['ministerie'])

        # Label filter support multiselect
        for l in self.request.GET.getlist('labels'):
            if l != '':
                 qs = qs.filter(colleague__labels__id__contains=l)

        # Apply period filtering for overlapping periods
        periode = self.request.GET.get('periode')
        if periode:
            qs = filter_placements_by_period(qs, periode)

        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if 'HX-Request' in self.request.headers:
            if self.request.GET.get('pagina'):
                return ['parts/placement_table_rows.html']
            return ['parts/filter_and_table_container.html']
        return ['placement_table.html']

    def _build_close_url(self, request):
        """Build close URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(request.GET)
        params.pop('collega', None)
        params.pop('opdracht', None)
        return f"/plaatsingen/?{params.urlencode()}" if params else "/plaatsingen/"

    def _build_assignment_url(self, request, assignment_id):
        """Build assignment panel URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(request.GET)
        params.pop('opdracht', None)
        params['opdracht'] = assignment_id
        return f"/plaatsingen/?{params.urlencode()}"

    def _build_client_url(self, client_name):
        """Build client filter URL"""
        params = QueryDict(mutable=True)
        params['client'] = client_name
        return f"/plaatsingen/?{params.urlencode()}"

    def _build_ministry_url(self, ministry_id):
        """Build ministry filter URL"""
        params = QueryDict(mutable=True)
        params['ministry'] = ministry_id
        return f"/plaatsingen/?{params.urlencode()}"

    def _build_colleague_url(self, colleague_id):
        """Build colleague panel URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(self.request.GET)
        params.pop('collega', None)
        params.pop('opdracht', None)
        params['collega'] = colleague_id
        return f"/plaatsingen/?{params.urlencode()}"

    def _get_colleague_assignments(self, colleague):
        """Get assignments for a colleague"""
        return Placement.objects.filter(
            colleague=colleague
        ).select_related(
            'service__assignment',
            'service__assignment__ministry',
            'service__skill'
        ).values(
            'id', 'service__assignment__id', 'service__assignment__name',
            'service__assignment__organization', 'service__assignment__ministry__name',
            'service__assignment__start_date', 'service__assignment__end_date',
            'service__skill__name'
        ).distinct()

    def _get_colleague_panel_data(self, colleague):
        """Get colleague panel data for server-side rendering"""
        
        colleague_assignments = self._get_colleague_assignments(colleague)
        assignment_list = [
            {
                'name': item['service__assignment__name'],
                'id': item['service__assignment__id'],
                'organization': item['service__assignment__organization'],
                'ministry': {'name': item['service__assignment__ministry__name']} if item['service__assignment__ministry__name'] else None,
                'start_date': item['service__assignment__start_date'],
                'end_date': item['service__assignment__end_date'],
                'skill': item['service__skill__name'],
                'assignment_url': self._build_assignment_url(self.request, item['service__assignment__id']),
            }
            for item in colleague_assignments
        ]
        
        return {
            'panel_content_template': 'parts/colleague_panel_content.html',
            'panel_title': colleague.name,
            'breadcrumb_items': None,
            'close_url': self._build_close_url(self.request),
            'colleague': colleague,
            'assignment_list': assignment_list,
        }

    def _get_assignment_panel_data(self, assignment, colleague):
        """Get assignment panel data for server-side rendering"""
        placements_qs = Placement.objects.filter(
            service__assignment=assignment
        ).select_related('colleague', 'service__skill')
        
        # Add colleague URLs to placements
        placements = []
        for placement in placements_qs:
            placement.colleague_url = self._build_colleague_url(placement.colleague.id)
            placements.append(placement)
        
        # Build breadcrumb items
        params = QueryDict(mutable=True)
        params.update(self.request.GET)
        params.pop('opdracht', None)
        colleague_url = f"/plaatsingen/?{params.urlencode()}"

        breadcrumb_items = [
            {'text': colleague.name, 'url': colleague_url},
            {'text': assignment.name, 'url': None}
        ]
        
        return {
            'panel_content_template': 'parts/assignment_panel_content.html',
            'panel_title': assignment.name,
            'breadcrumb_items': breadcrumb_items,
            'close_url': self._build_close_url(self.request),
            'assignment': assignment,
            'placements': placements,
            'client_url': self._build_client_url(assignment.organization),
            'ministry_url': self._build_ministry_url(assignment.ministry.id) if assignment.ministry else None,
        }

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)
        
        # Add colleague URLs to placement objects
        for placement in context['object_list']:
            placement.colleague_url = self._build_colleague_url(placement.colleague.id)

        context['search_field'] = 'zoek'
        context['search_placeholder'] = 'Zoek op collega, opdracht of opdrachtgever...'
        context['search_filter'] = self.request.GET.get('zoek')

        active_filters = {}  # key: val
        for filter_param in ['rol', 'opdrachtgever', 'ministerie', 'periode']:
            val = self.request.GET.get(filter_param)
            if val:
                active_filters[filter_param] = val

        # label filter supports multi-select
        label_filter = set()
        for l in self.request.GET.getlist('labels'):
            if l != '':
                label_filter.add(l)
        if len(label_filter) > 0:
            active_filters['labels'] = label_filter

        if active_filters.get('periode'):
            periode_from, periode_to = active_filters['periode'].split('_')
            active_filters['periode'] = {
                'from': datetime.strptime(periode_from, '%Y-%m').date(),
                'to': datetime.strptime(periode_to, '%Y-%m').date(),
            }

        label_filter_groups = []
        for category in LabelCategory.objects.all():

            select_label = category.name
            options = [
                {'value': '', 'label': ''},
            ]
            value = ''
            for label in Label.objects.filter(category=category):
                options.append({
                    'value': str(label.id),
                    'label': f"{label.name}",
                    'category_color': category.color
                })
                if str(label.id) in active_filters.get('labels', set()):
                    options[-1]['selected'] = True
                    value = str(label.id)

            filter_group = {
                'type': 'select',
                'name': 'labels',
                'label': select_label,
                'options': options,
                'value': value,
            }

            label_filter_groups.append(filter_group)


        skill_options = [
            {'value': '', 'label': ''}
        ]
        skill_value = ''
        for skill in Skill.objects.order_by('name'):
            skill_options.append({'value': str(skill.id), 'label': skill.name})
            if active_filters.get('rol') == str(skill.id):
                skill_options[-1]['selected'] = True
                skill_value = str(skill.id)

        clients = [
            {'id': org, 'name': org}
            for org in Assignment.objects.values_list('organization', flat=True).distinct().exclude(organization='').order_by('organization')
        ]

        client_options = [
            {'value': '', 'label': ''},
        ]
        client_value = ''
        for client in clients:
            client_options.append({'value': client['id'], 'label': client['name']})
            if active_filters.get('opdrachtgever') == str(client['id']):
                client_options[-1]['selected'] = True
                client_value = str(client['id'])

        ministry_options = [
            {'value': '', 'label': ''},
        ]
        ministry_value = ''
        for ministry in Ministry.objects.order_by('name'):
            ministry_options.append({'value': str(ministry.id), 'label': ministry.name})
            if active_filters.get('ministerie') == str(ministry.id):
                ministry_options[-1]['selected'] = True
                ministry_value = str(ministry.id)

        context['active_filters'] = active_filters
        context['active_filter_count'] = len(active_filters)

        # TODO: this can be become an object to help defining correctly and performing extra preprocessing on context
        # introduce value_key, label_key:
        context['filter_groups'] = [
            *label_filter_groups,
            {
                'type': 'select',
                'name': 'rol',
                'label': 'Rollen',
                'options': skill_options,
                'value': skill_value,
            },
            {
                'type': 'select',
                'name': 'opdrachtgever',
                'label': 'Opdrachtgever',
                'options': client_options,
                'value': client_value,
            },
            {
                'type': 'select',
                'name': 'ministerie',
                'label': 'Ministerie',
                'options': ministry_options,
                'value': ministry_value,
            },
            {
                'type': 'date_range',
                'name': 'periode',
                'label': 'Periode',
                'from_label': 'Van',
                'to_label': 'Tot',
                'require_both': True,
            },
        ]

        # Build next page URL with all current filters
        if context.get('page_obj') and context['page_obj'].has_next():
            filter_params = []
            for key, value in self.request.GET.items():
                if key != 'pagina':  # Exclude page param
                    filter_params.append(f'{key}={value}')
            params_str = '&'.join(filter_params)
            next_page = context['page_obj'].next_page_number()
            context['next_page_url'] = f'?pagina={next_page}' + (f'&{params_str}' if params_str else '')
        else:
            context['next_page_url'] = None

        colleague_id = self.request.GET.get('collega')
        assignment_id = self.request.GET.get('opdracht')

        # if one or both of the ids are invalid, the panel_data is skipped
        if colleague_id and not assignment_id:
            try:
                colleague = Colleague.objects.get(id=colleague_id)
                context['panel_data'] = self._get_colleague_panel_data(colleague)
            except Colleague.DoesNotExist:
                pass
        elif colleague_id and assignment_id:
            try:
                colleague = Colleague.objects.get(id=colleague_id)
                assignment = Assignment.objects.get(id=assignment_id)
                context['panel_data'] = self._get_assignment_panel_data(assignment, colleague)
            except (Colleague.DoesNotExist, Assignment.DoesNotExist):
                pass
        return context


class UserListView(PermissionRequiredMixin, ListView):
    """View for user list with filtering and infinite scroll pagination"""
    model = User
    template_name = 'user_admin.html'
    paginate_by = 50
    permission_required = 'core.view_user'

    def get_queryset(self):
        """Apply filters to users queryset - exclude superusers"""
        qs = User.objects.prefetch_related('groups', 'labels__category').filter(
            is_superuser=False
        ).order_by('last_name', 'first_name')

        search_filter = self.request.GET.get('zoek')
        if search_filter:
            qs = qs.annotate(
                full_name=Concat('first_name', Value(' '), 'last_name'),
            ).filter(
                Q(full_name__icontains=search_filter) |
                Q(first_name__icontains=search_filter) |
                Q(last_name__icontains=search_filter) |
                Q(email__icontains=search_filter)
            )

        # Label filter support multiselect
        for l in self.request.GET.getlist('labels'):
            if l != '':
                 qs = qs.filter(labels__id__contains=l)

        # Role filter
        role_filter = self.request.GET.get('rol')
        if role_filter:
            qs = qs.filter(groups__id=role_filter)

        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if 'HX-Request' in self.request.headers:
            # If paginating, return only rows
            if self.request.GET.get('pagina'):
                return ['parts/user_table_rows.html']
            # Otherwise, return full table (for filter changes)
            return ['parts/user_table.html']
        return ['user_admin.html']

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)

        context['search_field'] = 'zoek'
        context['search_placeholder'] = 'Zoek op naam of email...'
        context['search_filter'] = self.request.GET.get('zoek')

        active_filters = {}

        # label filter supports multi-select
        label_filter = set()
        for l in self.request.GET.getlist('labels'):
            if l != '':
                label_filter.add(l)
        if len(label_filter) > 0:
            active_filters['labels'] = label_filter

        role_filter = self.request.GET.get('rol')
        if role_filter:
            active_filters['rol'] = role_filter

        label_filter_groups = []
        for category in LabelCategory.objects.all():

            select_label = category.name
            options = [
                {'value': '', 'label': 'Allemaal'},
            ]
            value = ''
            for label in Label.objects.filter(category=category):
                options.append({
                    'value': str(label.id),
                    'label': f"{label.name}"
                })
                if str(label.id) in active_filters.get('labels', set()):
                    options[-1]['selected'] = True
                    value = str(label.id)

            filter_group = {
                'type': 'select',
                'name': 'labels',
                'label': select_label,
                'options': options,
                'value': value,
            }

            label_filter_groups.append(filter_group)

        role_options = [
            {'value': '', 'label': 'Alle rollen'},
        ]
        role_value = ''
        for group in Group.objects.all().order_by('name'):
            role_options.append({'value': str(group.id), 'label': group.name})
            if active_filters.get('rol') == str(group.id):
                role_options[-1]['selected'] = True
                role_value = str(group.id)

        context['active_filters'] = active_filters
        context['active_filter_count'] = len(active_filters)

        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'rol',
                'label': 'Rol',
                'options': role_options,
                'value': role_value,
            },
            *label_filter_groups
        ]
        
        context['primary_button'] = {
            'button_text': 'Gebruiker toevoegen',
            'attrs': {
                'hx-get': reverse('user-create'),
                'hx-target': '#userFormModal',
                'hx-push-url': 'false',  # necessary because nested in htmx powered form
            }
        }

        # Build next page URL with all current filters
        if context.get('page_obj') and context['page_obj'].has_next():
            filter_params = []
            for key, value in self.request.GET.items():
                if key != 'pagina':
                    filter_params.append(f'{key}={value}')
            params_str = '&'.join(filter_params)
            next_page = context['page_obj'].next_page_number()
            context['next_page_url'] = f'?pagina={next_page}' + (f'&{params_str}' if params_str else '')
        else:
            context['next_page_url'] = None

        return context


@permission_required('core.add_user', raise_exception=True)
def user_create(request):
    """Handle user creation - GET returns form modal, POST processes creation"""
    
    form_post_url = reverse('user-create')
    modal_title = 'Nieuwe gebruiker'
    element_id = 'userFormModal'
    
    if request.method == 'GET':
        # Return modal HTML with empty UserForm
        form = UserForm()
        return render(request, 'parts/user_form_modal.html', {
            'content': form, 
            'form_post_url': form_post_url, 
            'modal_title': modal_title, 
            'form_button_label': 'Toevoegen',
            'modal_element_id': element_id,
            'target_element_id': element_id,
        })
    elif request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            create_user(
                request.user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                labels=form.cleaned_data.get('labels'),
                groups=form.cleaned_data.get('groups')
            )
            # For HTMX requests, use HX-Redirect header to force full page redirect
            # For standard form posts, use normal redirect
            if 'HX-Request' in request.headers:
                response = HttpResponse(status=200)
                response['HX-Redirect'] = reverse('admin-users')
                return response
            else:
                return redirect('admin-users')
        else:
            # Re-render form with errors (stays in modal with HTMX)
            return render(request, 'parts/user_form_modal.html', {
                'content': form, 
                'form_post_url': form_post_url, 
                'modal_title': modal_title, 
                'form_button_label': 'Toevoegen',
                'modal_element_id': element_id,
                'target_element_id': element_id,
            })
    return HttpResponse(status=405)


@permission_required('core.change_user', raise_exception=True)
def user_edit(request, pk):
    """Handle user editing - GET returns form modal with user data, POST processes update"""
    edited_user = get_object_or_404(User, pk=pk, is_superuser=False)
    form_post_url = reverse('user-edit', args=[edited_user.id])
    modal_title = 'Gebruiker bewerken'
    element_id = 'userFormModal'

    if request.method == 'GET':
        # Return modal HTML with UserForm populated with user data
        form = UserForm(instance=edited_user)
        return render(request, 'parts/user_form_modal.html', {
            'content': form, 
            'form_post_url': form_post_url, 
            'modal_title': modal_title, 
            'form_button_label': 'Opslaan',
            'modal_element_id': element_id,
            'target_element_id': element_id,
            **get_delete_context('user-delete', edited_user.pk, f'{edited_user.first_name} {edited_user.last_name}'),
        })
    elif request.method == 'POST':
        form = UserForm(request.POST, instance=edited_user)
        if form.is_valid():
            update_user(
                updater=request.user,
                user=edited_user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                labels=form.cleaned_data.get('labels'),
                groups=form.cleaned_data.get('groups')
            )
            # For HTMX requests, use HX-Redirect header to force full page redirect
            # For standard form posts, use normal redirect
            if 'HX-Request' in request.headers:
                response = HttpResponse(status=200)
                response['HX-Redirect'] = reverse('admin-users')
                return response
            else:
                return redirect('admin-users')
        else:
            # Re-render form with errors (stays in modal with HTMX)
            return render(request, 'parts/user_form_modal.html', {
                'content': form, 
                'form_post_url': form_post_url, 
                'modal_title': modal_title, 
                'form_button_label': 'Opslaan',
                'modal_element_id': element_id,
                'target_element_id': element_id,
                **get_delete_context('user-delete', edited_user.pk, f'{edited_user.first_name} {edited_user.last_name}'),
            })
    return HttpResponse(status=405)


@permission_required('core.delete_user', raise_exception=True)
def user_delete(request, pk):
    """Handle user deletion"""
    user = get_object_or_404(User, pk=pk, is_superuser=False)
    
    if request.method == 'GET':
        # Show delete confirmation modal
        return render(request, 'parts/generic_form_modal.html', {
            'modal_title': f"Verwijder gebruiker: {user.first_name} {user.last_name}",
            'warning_modal': True,
            'modal_element_id': "userFormModal",
            'target_element_id': "user_table",
            'delete_warning': f'Weet je zeker dat je {user.first_name} {user.last_name} wilt verwijderen?',
            'form_post_url': reverse('user-delete', kwargs={'pk': pk}),
            'form_button_label': 'Verwijderen',
        })
    elif request.method == 'POST':
        label_names = [label.name for label in user.labels.all()]
        context = {
            'id': pk,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'label_names': label_names,
            'group_names': [g.name for g in user.groups.all()]
        }
        user.delete()
        create_event(request.user.email, 'User.delete', context)
        response = HttpResponse(status=200)
        response['HX-Redirect'] = reverse('admin-users')
        return response
    return HttpResponse(status=405)


@permission_required('core.add_user', raise_exception=True)
def user_import_csv(request):
    """
    Import users from a CSV file.

    GET: Display the import main form
    POST: Process the uploaded CSV file and create users

    For expected CSV format, see create_users_from_csv function
    """
    if request.method == 'GET':
        return render(request, 'user_import.html')
    elif request.method == 'POST':
        if 'csv_file' not in request.FILES:
            return render(request, 'user_import.html', {
                'result': {
                    'success': False,
                    'errors': ['Geen bestand geüpload. Upload een CSV-bestand.']
                }
            })

        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            return render(request, 'user_import.html', {
                'result': {
                    'success': False,
                    'errors': ['Ongeldig bestandstype. Upload een CSV-bestand.']
                }
            })
        
        try:
            csv_content = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            return {
                'success': False,
                'errors': ['Invalid CSV file encoding. Please use UTF-8.']
            }

        result = create_users_from_csv(request.user, csv_content)

        # Return results in the form
        return render(request, 'user_import.html', {'result': result})
    else:
        return HttpResponse(status=405)


@permission_required([
    'core.add_assignment', 
    'core.add_service', 
    'core.add_placement', 
    'core.add_colleague',
    'core.add_ministry',
    ], raise_exception=True)
def placement_import_csv(request):
    """
    Import placements from a CSV file.

    GET: Display the import form
    POST: Process the uploaded CSV file and create placements (with related assignments, services, colleagues, and skills)

    For expected CSV format, see create_placements_from_csv function
    """
    if request.method == 'GET':
        return render(request, 'placement_import.html')
    elif request.method == 'POST':
        if 'csv_file' not in request.FILES:
            return render(request, 'placement_import.html', {
                'result': {
                    'success': False,
                    'errors': ['Geen bestand geüpload. Upload een CSV-bestand.']
                }
            })

        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            return render(request, 'placement_import.html', {
                'result': {
                    'success': False,
                    'errors': ['Ongeldig bestandstype. Upload een CSV-bestand.']
                }
            })

        try:
            csv_content = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            return render(request, 'placement_import.html', {
                'result': {
                    'success': False,
                    'errors': ['Invalid CSV file encoding. Please use UTF-8.']
                }
            })

        result = create_placements_from_csv(csv_content)

        # Return results in the form
        return render(request, 'placement_import.html', {'result': result})
    else:
        return HttpResponse(status=405)


@permission_required('core.view_labelcategory', raise_exception=True)
def label_admin(request):
    """Main label admin pag"""
    categories = annotate_usage_counts(LabelCategory.objects.all())
    return render(request, 'label_admin.html', {'categories': categories})


@permission_required('core.change_labelcategory', raise_exception=True)
def label_category_create(request):
    """
    Returns a partial html page, to be used with htmx
    """

    """Create a new label category"""
    form_post_url = reverse('label-category-create')
    modal_title = 'Nieuwe categorie'
    element_id = 'labelFormModal'
    form_button_label = 'Toevoegen'

    if request.method == 'GET':
        form = LabelCategoryForm()
        return render(request, 'parts/generic_form_modal.html', {
            'content': form,
            'form_post_url': form_post_url,
            'modal_title': modal_title,
            'form_button_label': form_button_label,
            'modal_element_id': element_id,
            'target_element_id': element_id,
        })
    elif request.method == 'POST':
        form = LabelCategoryForm(request.POST)
        if form.is_valid():
            saved_instance = form.save()
            messages.success(request, f"Categorie '{form.cleaned_data['name']}' succesvol aangemaakt")
            response = HttpResponse(status=200)
            hx_redirect = reverse('label-admin')
            # redirecting to part of the page does using anchor does not seem to work yet
            response['HX-Redirect'] = hx_redirect
            return response
        else:
            return render(request, 'parts/generic_form_modal.html', {
                'content': form,
                'form_post_url': form_post_url,
                'modal_title': modal_title,
                'form_button_label': form_button_label,
                'modal_element_id': element_id,
                'target_element_id': element_id,
            })


@permission_required('core.change_labelcategory', raise_exception=True)
def label_category_edit(request, pk):
    """
    Edit a label category
    Returns a partial html page, to be used with htmx
    """
    
    category = get_object_or_404(LabelCategory, pk=pk)
    form_post_url = reverse('label-category-edit', kwargs={'pk': pk})
    modal_title = f'Bewerk categorie: {category.name}'
    form_button_label = 'Opslaan'
    element_id = 'labelFormModal'

    if request.method == 'GET':
        form = LabelCategoryForm(instance=category)
        return render(request, 'parts/generic_form_modal.html', {
            'content': form,
            'form_post_url': form_post_url,
            'modal_title': modal_title,
            'form_button_label': form_button_label,
            'modal_element_id': element_id,
            'target_element_id': element_id,
            **get_delete_context('label-category-delete', category.pk, f"categorie '{category.name}'"),
        })
    elif request.method == 'POST':
        form = LabelCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse('label-admin')
            return response

        else:
            return render(request, 'parts/generic_form_modal.html', {
                'content': form,
                'form_post_url': form_post_url,
                'modal_title': modal_title,
                'form_button_label': form_button_label,
                'modal_element_id': element_id,
                'target_element_id': element_id,
                **get_delete_context('label-category-delete', category.pk, f"categorie '{category.name}'"),
            })


@permission_required('core.delete_labelcategory', raise_exception=True)
def label_category_delete(request, pk):
    """
    To be used with htmx
    """
    category = get_object_or_404(LabelCategory, pk=pk)
    if request.method == 'GET':
        return render(request, 'parts/generic_form_modal.html', {
            'modal_title': f"Verwijder categorie: {category.name}", 
            'warning_modal': True,
            'modal_element_id': "labelFormModal",
            'target_element_id': "labelFormModal",
            'delete_warning': f"Weet je zeker dat je deze categorie wilt verwijderen? Dit verwijdert ook alle {category.labels.count()} labels.",
            'form_post_url': reverse('label-category-delete', kwargs={'pk': pk}),
            'form_button_label': 'Verwijderen',
        })
    elif request.method == 'POST':
        category_name = category.name  # Store name before deleting
        category.delete()
        messages.success(request, f"Categorie '{category_name}' succesvol verwijderd")
        response = HttpResponse(status=200)
        response['HX-Redirect'] = reverse('label-admin')
        return response
    return HttpResponse(status=405)


@permission_required('core.add_label', raise_exception=True)
def label_create(request, pk):
    """
    Returns a partial html page, to be used with htmx
    """

    if request.method == 'POST':
        category = get_object_or_404(LabelCategory, pk=pk)
        form = LabelForm(request.POST, category_id=category.id)
        if form.is_valid(): 
            new_instance = form.save(commit=False)
            new_instance.category = category
            new_instance.save()

            category_qs = LabelCategory.objects.filter(id=category.id)
            category = annotate_usage_counts(category_qs).get()

            return render(request, 'parts/label_category.html', {
                'category': category
            })
        else:
            errors = {}
            for field, error in form.errors.items():
                errors[field] = error
            return render(request, 'parts/label_category.html', {
                'category': category,
                'errors': errors,
            })
    return HttpResponse(status=405)


@permission_required('core.change_label', raise_exception=True)
def label_edit(request, pk):
    """
    Returns a partial html page, to be used with htmx
    """
    label = get_object_or_404(Label, pk=pk)
    category = label.category
    form_post_url = reverse('label-edit', kwargs={'pk': pk})
    modal_title = f'Bewerk label: {label.name}'
    form_button_label = 'Opslaan'
    element_id = 'labelFormModal'

    if request.method == 'GET':
        form = LabelForm(instance=label, category_id=category.id)
        return render(request, 'parts/generic_form_modal.html', {
            'content': form,
            'form_post_url': form_post_url,
            'modal_title': modal_title,
            'form_button_label': form_button_label,
            'modal_element_id': element_id,
            'target_element_id': element_id,
            **get_delete_context('label-delete', label.pk, f"label '{label.name}'"),
        })
    elif request.method == 'POST':
        form = LabelForm(request.POST, instance=label)
        if form.is_valid():
            form.save()

            category_qs = LabelCategory.objects.filter(id=category.id)
            category = annotate_usage_counts(category_qs).get()

            response = render(request, 'parts/label_category.html', {
                'category': category
            })
            response['HX-Retarget'] = f"#label_category_{category.id}"
            response['HX-Trigger'] = 'closeModal'
            return response
        else:
            return render(request, 'parts/generic_form_modal.html', {
                'content': form,
                'form_post_url': form_post_url,
                'modal_title': modal_title,
                'form_button_label': form_button_label,
                'modal_element_id': element_id,
                'target_element_id': element_id,
                **get_delete_context('label-delete', label.pk, f"label '{label.name}'"),
            })


@permission_required('core.delete_label', raise_exception=True)
def label_delete(request, pk):
    """
    To be used with htmx
    """

    label = get_object_or_404(Label, pk=pk)
    category = label.category

    label_use_count = label.users.count() + label.colleagues.count()
    
    if request.method == 'GET':
        return render(request, 'parts/generic_form_modal.html', {
            'modal_title': f"Verwijder label: {label.name}", 
            'warning_modal': True,
            'modal_element_id': "labelFormModal",
            'target_element_id': f"label_category_{category.id}",
            'delete_warning': f"Weet je zeker dat je dit label wilt verwijderen? Het wordt gebruikt op {label_use_count} plekken.",
            'form_post_url': reverse('label-delete', kwargs={'pk': pk}),
            'form_button_label': 'Verwijderen',
        })
    elif request.method == 'POST':
        label.delete()

        category_qs = LabelCategory.objects.filter(id=category.id)
        category = annotate_usage_counts(category_qs).get()

        response = render(request, 'parts/label_category.html', {
            'category': category,
        })
        response['HX-Trigger'] = 'closeModal'
        return response
    
    return HttpResponse(status=405)
