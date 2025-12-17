from django.views.generic.list import ListView
from django.views.generic import DetailView
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Prefetch, Value
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

from authlib.integrations.django_client import OAuth

from .models import Assignment, Colleague, Skill, Placement, Service, Ministry, Brand, User
from .services.sync import sync_all_otys_iir_records
from .services.placements import filter_placements_by_period, create_placements_from_csv
from .services.users import create_user, update_user, create_users_from_csv
from .forms import UserForm

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
        return redirect(request.build_absolute_uri(reverse("home")))
    return redirect('/no-access/')


@login_not_required  # page cannot require login because you land on this after unsuccesful login
def no_access(request):
    return render(request, 'no_access.html')


@login_not_required  # logout should be accessible without login
def logout(request):
    if request.user and request.user.is_authenticated:
        auth_logout(request)
    return redirect(reverse('login'))


@user_passes_test(lambda u: u.is_superuser and u.is_authenticated, login_url='/admin/login/')
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
            Brand.objects.all().delete()
        elif action == 'load_data':
            management.call_command('loaddata', 'dummy_data.json')
            messages.success(request, 'Data loaded successfully from dummy_data.json')
        elif action == 'add_dev_user':
            management.call_command('add_developer_user')
            messages.success(request, 'Developer user added')
        elif action == 'sync_all_otys_records':
            sync_all_otys_iir_records()
            messages.success(request, 'All records synced successfully from OTYS IIR')
        return redirect('admin-db')

    
    return render(request, 'admin_db.html', context)


class PlacementListView(ListView):
    """View for placements table view with infinite scroll pagination"""
    model = Placement
    template_name = 'placement_table.html'
    paginate_by = 50

    def get_queryset(self):
        """Apply filters to placements queryset - only show INGEVULD assignments, not LEAD"""
        qs = Placement.objects.select_related(
            'colleague', 'colleague__brand', 'service', 'service__skill', 'service__assignment__ministry'
        ).filter(
            service__assignment__status='INGEVULD'
        ).order_by('-service__assignment__start_date')

        search_filter = self.request.GET.get('search')
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

        filters = {
            'skill': 'service__skill__id',
            'brand': 'colleague__brand__id',
            'client': 'service__assignment__organization',
            'ministry': 'service__assignment__ministry__id'
        }

        for param, lookup in filters.items():
            value = self.request.GET.get(param)
            if value:
                qs = qs.filter(**{lookup: value})

        # Apply period filtering for overlapping periods
        period = self.request.GET.get('period')
        if period:
            qs = filter_placements_by_period(qs, period)

        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if 'HX-Request' in self.request.headers:
            # If paginating, return only rows
            if self.request.GET.get('page'):
                return ['parts/placement_table_rows.html']
            # Otherwise, return full table (for filter changes)
            return ['parts/placement_table.html']
        return ['placement_table.html']
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests including panel requests via query parameters"""
        # Check for panel requests via query parameters
        colleague_id = request.GET.get('colleague')
        assignment_id = request.GET.get('assignment')
        
        if 'HX-Request' in request.headers:
            # Handle colleague panel
            if colleague_id and not assignment_id:
                return self._render_colleague_panel(request, colleague_id)
                
            # Handle assignment panel (with optional colleague context)
            if assignment_id:
                return self._render_assignment_panel(request, assignment_id, colleague_id)
                
            # This is a filter request - fall through to normal ListView handling
                
        return super().get(request, *args, **kwargs)

    def _build_close_url(self, request):
        """Build close URL preserving current filters"""
        params = QueryDict(mutable=True)
        params.update(request.GET)
        params.pop('colleague', None)
        params.pop('assignment', None)
        return f"/placements/?{params.urlencode()}" if params else "/placements/"

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

    def _render_colleague_panel(self, request, colleague_id):
        """Render colleague panel via HTMX"""
        placement = get_object_or_404(
            Placement.objects.select_related('colleague', 'colleague__brand'),
            pk=colleague_id
        )
        
        colleague_assignments = self._get_colleague_assignments(placement.colleague)
        assignment_list = [
            {
                'name': item['service__assignment__name'],
                'id': item['service__assignment__id'],
                'placement_id': item['id'],
                'organization': item['service__assignment__organization'],
                'ministry': {'name': item['service__assignment__ministry__name']} if item['service__assignment__ministry__name'] else None,
                'start_date': item['service__assignment__start_date'],
                'end_date': item['service__assignment__end_date'],
                'skill': item['service__skill__name'],
            }
            for item in colleague_assignments
        ]
        
        return render(request, 'parts/sidepanel.html', {
            'panel_content_template': 'parts/colleague_panel_content.html',
            'panel_title': placement.colleague.name,
            'breadcrumb_items': None,
            'close_url': self._build_close_url(request),
            'placement': placement,
            'colleague': placement.colleague,
            'assignment_list': assignment_list,
        })

    def _get_assignment_placements(self, assignment):
        """Get placements for an assignment"""
        return Placement.objects.filter(
            service__assignment=assignment
        ).select_related('colleague', 'colleague__brand', 'service__skill')

    def _render_assignment_panel(self, request, assignment_id, colleague_id=None):
        """Render assignment panel via HTMX"""
        assignment = get_object_or_404(Assignment, pk=assignment_id)
        placements = self._get_assignment_placements(assignment)
        
        # Build breadcrumb items - only show if we came from colleague panel
        breadcrumb_items = None
        if colleague_id:
            try:
                colleague = get_object_or_404(Placement, pk=colleague_id).colleague
                params = QueryDict(mutable=True)
                params.update(request.GET)
                params.pop('assignment', None)
                colleague_url = f"/placements/?{params.urlencode()}"
                
                breadcrumb_items = [
                    {'text': colleague.name, 'url': colleague_url},
                    {'text': assignment.name, 'url': None}
                ]
            except:
                pass
        
        return render(request, 'parts/sidepanel.html', {
            'panel_content_template': 'parts/assignment_panel_content.html',
            'panel_title': assignment.name,
            'breadcrumb_items': breadcrumb_items,
            'close_url': self._build_close_url(request),
            'assignment': assignment,
            'placements': placements,
        })

    def _get_colleague_panel_data(self, colleague_id):
        """Get colleague panel data for server-side rendering"""
        placement = get_object_or_404(
            Placement.objects.select_related('colleague', 'colleague__brand'),
            pk=colleague_id
        )
        
        colleague_assignments = self._get_colleague_assignments(placement.colleague)
        assignment_list = [
            {
                'name': item['service__assignment__name'],
                'id': item['service__assignment__id'],
                'placement_id': item['id'],
                'organization': item['service__assignment__organization'],
                'ministry': {'name': item['service__assignment__ministry__name']} if item['service__assignment__ministry__name'] else None,
                'start_date': item['service__assignment__start_date'],
                'end_date': item['service__assignment__end_date'],
                'skill': item['service__skill__name'],
            }
            for item in colleague_assignments
        ]
        
        return {
            'panel_content_template': 'parts/colleague_panel_content.html',
            'panel_title': placement.colleague.name,
            'breadcrumb_items': None,
            'close_url': self._build_close_url(self.request),
            'placement': placement,
            'colleague': placement.colleague,
            'assignment_list': assignment_list,
        }

    def _get_assignment_panel_data(self, assignment_id, colleague_id=None):
        """Get assignment panel data for server-side rendering"""
        assignment = get_object_or_404(Assignment, pk=assignment_id)
        placements = self._get_assignment_placements(assignment)
        
        # Build breadcrumb items - only show if we came from colleague panel
        breadcrumb_items = None
        if colleague_id:
            try:
                colleague = get_object_or_404(Placement, pk=colleague_id).colleague
                params = QueryDict(mutable=True)
                params.update(self.request.GET)
                params.pop('assignment', None)
                colleague_url = f"/placements/?{params.urlencode()}"
                
                breadcrumb_items = [
                    {'text': colleague.name, 'url': colleague_url},
                    {'text': assignment.name, 'url': None}
                ]
            except (Placement.DoesNotExist, AttributeError):
                pass
        
        return {
            'panel_content_template': 'parts/assignment_panel_content.html',
            'panel_title': assignment.name,
            'breadcrumb_items': breadcrumb_items,
            'close_url': self._build_close_url(self.request),
            'assignment': assignment,
            'placements': placements,
        }

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)

        context['search_field'] = 'search'
        context['search_placeholder'] = 'Zoek op collega, opdracht of opdrachtgever...'
        context['search_filter'] = self.request.GET.get('search')

        active_filters = {}  # key: val
        for filter_param in ['brand', 'skill', 'client', 'ministry', 'period']:
            val = self.request.GET.get(filter_param)
            if val:
                active_filters[filter_param] = val

        if active_filters.get('period'):
            period_from, period_to = active_filters['period'].split('_')
            active_filters['period'] = {
                'from': period_from,
                'to': period_to,
            }

        brand_options = [
            {'value': '', 'label': 'Alle merken'}
        ]
        for brand in Brand.objects.order_by('name'):
            brand_options.append({'value': str(brand.id), 'label': brand.name})
            if active_filters.get('brand') == str(brand.id):
                brand_options[-1]['selected'] = True

        skill_options = [
            {'value': '', 'label': 'Alle rollen'}
        ]
        for skill in Skill.objects.order_by('name'):
            skill_options.append({'value': str(skill.id), 'label': skill.name})
            if active_filters.get('skill') == str(skill.id):
                skill_options[-1]['selected'] = True

        clients = [
            {'id': org, 'name': org}
            for org in Assignment.objects.values_list('organization', flat=True).distinct().exclude(organization='').order_by('organization')
        ]

        client_options = [
            {'value': '', 'label': 'Alle opdrachtgevers'},
        ]
        for client in clients:
            client_options.append({'value': client['id'], 'label': client['name']})
            if active_filters.get('client') == str(client['id']):
                client_options[-1]['selected'] = True

        ministry_options = [
            {'value': '', 'label': 'Alle ministeries'},
        ]
        for ministry in Ministry.objects.order_by('name'):
            ministry_options.append({'value': str(ministry.id), 'label': ministry.name})
            if active_filters.get('ministry') == str(ministry.id):
                ministry_options[-1]['selected'] = True

        context['active_filters'] = active_filters
        context['active_filter_count'] = len(active_filters)

        # TODO: this can be become an object to help defining correctly and performing extra preprocessing on context
        # introduce value_key, label_key:
        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'brand',
                'label': 'Merk',
                'options': brand_options,
                'value': active_filters.get('brand', ''),
            },
            {
                'type': 'select',
                'name': 'skill',
                'label': 'Rollen',
                'options': skill_options,
                'value': active_filters.get('skill', ''),
            },
            {
                'type': 'select',
                'name': 'client',
                'label': 'Opdrachtgever',
                'options': client_options,
                'value': active_filters.get('client', ''),
            },
            {
                'type': 'select',
                'name': 'ministry',
                'label': 'Ministerie',
                'options': ministry_options,
                'value': active_filters.get('ministry', ''),
            },
            {
                'type': 'date_range',
                'name': 'period',
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
                if key != 'page':  # Exclude page param
                    filter_params.append(f'{key}={value}')
            params_str = '&'.join(filter_params)
            next_page = context['page_obj'].next_page_number()
            context['next_page_url'] = f'?page={next_page}' + (f'&{params_str}' if params_str else '')
        else:
            context['next_page_url'] = None

        # Server-side panel rendering
        colleague_id = self.request.GET.get('colleague')
        assignment_id = self.request.GET.get('assignment')
        
        # Only add panel data for non-HTMX requests (server-side rendering)
        if not 'HX-Request' in self.request.headers:
            if colleague_id or assignment_id:
                try:
                    if colleague_id and not assignment_id:
                        context['panel_data'] = self._get_colleague_panel_data(colleague_id)
                        print(f"DEBUG: Added colleague panel data for {colleague_id}")
                    elif assignment_id:
                        context['panel_data'] = self._get_assignment_panel_data(assignment_id, colleague_id)
                        print(f"DEBUG: Added assignment panel data for {assignment_id}")
                except (Placement.DoesNotExist, Assignment.DoesNotExist):
                    # Invalid panel parameters - ignore
                    print(f"DEBUG: Invalid panel parameters: colleague={colleague_id}, assignment={assignment_id}")
                    pass
        else:
            print("DEBUG: HTMX request, not adding panel data")

        return context






class UserListView(PermissionRequiredMixin, ListView):
    """View for user list with filtering and infinite scroll pagination"""
    model = User
    template_name = 'user_list.html'
    paginate_by = 50
    permission_required = 'core.view_user'

    def get_queryset(self):
        """Apply filters to users queryset - exclude superusers"""
        qs = User.objects.select_related('brand').prefetch_related('groups').filter(
            is_superuser=False
        ).order_by('last_name', 'first_name')

        search_filter = self.request.GET.get('search')
        if search_filter:
            qs = qs.annotate(
                full_name=Concat('first_name', Value(' '), 'last_name'),
            ).filter(
                Q(full_name__icontains=search_filter) |
                Q(first_name__icontains=search_filter) |
                Q(last_name__icontains=search_filter) |
                Q(email__icontains=search_filter)
            )

        # Brand filter
        brand_filter = self.request.GET.get('brand')
        if brand_filter:
            qs = qs.filter(brand__id=brand_filter)

        # Role filter
        role_filter = self.request.GET.get('role')
        if role_filter:
            qs = qs.filter(groups__id=role_filter)

        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if 'HX-Request' in self.request.headers:
            # If paginating, return only rows
            if self.request.GET.get('page'):
                return ['parts/user_table_rows.html']
            # Otherwise, return full table (for filter changes)
            return ['parts/user_table.html']
        return ['user_list.html']

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)

        context['search_field'] = 'search'
        context['search_placeholder'] = 'Zoek op naam of email...'
        context['search_filter'] = self.request.GET.get('search')

        active_filters = {}
        brand_filter = self.request.GET.get('brand')
        if brand_filter:
            active_filters['brand'] = brand_filter

        role_filter = self.request.GET.get('role')
        if role_filter:
            active_filters['role'] = role_filter

        brand_options = [
            {'value': '', 'label': 'Alle merken'},
        ]
        for brand in Brand.objects.order_by('name'):
            brand_options.append({'value': brand.id, 'label': brand.name})
            if active_filters.get('brand') == str(brand.id):
                brand_options[-1]['selected'] = True

        role_options = [
            {'value': '', 'label': 'Alle rollen'},
        ]
        for group in Group.objects.all().order_by('name'):
            role_options.append({'value': group.id, 'label': group.name})
            if active_filters.get('role') == str(group.id):
                role_options[-1]['selected'] = True

        context['active_filters'] = active_filters
        context['active_filter_count'] = len(active_filters)

        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'brand',
                'label': 'Merk',
                'options': brand_options,
            },
            {
                'type': 'select',
                'name': 'role',
                'label': 'Rol',
                'options': role_options,
            },
        ]

        context['primary_button'] = {
            'button_text': 'Nieuwe gebruiker',
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
                if key != 'page':
                    filter_params.append(f'{key}={value}')
            params_str = '&'.join(filter_params)
            next_page = context['page_obj'].next_page_number()
            context['next_page_url'] = f'?page={next_page}' + (f'&{params_str}' if params_str else '')
        else:
            context['next_page_url'] = None

        return context


@permission_required('core.add_user', raise_exception=True)
def user_create(request):
    """Handle user creation - GET returns form modal, POST processes creation"""
    
    form_post_url = reverse('user-create')
    modal_title = 'Nieuwe gebruiker'
    
    if request.method == 'GET':
        # Return modal HTML with empty UserForm
        form = UserForm()
        return render(request, 'parts/user_form_modal.html', {'form': form, 'form_post_url': form_post_url, 'modal_title': modal_title, 'form_button_label': 'Toevoegen'})
    elif request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            create_user(
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                brand=form.cleaned_data.get('brand'),
                groups=form.cleaned_data.get('groups')
            )
            # For HTMX requests, use HX-Redirect header to force full page redirect
            # For standard form posts, use normal redirect
            if 'HX-Request' in request.headers:
                response = HttpResponse(status=200)
                response['HX-Redirect'] = reverse('users')
                return response
            else:
                return redirect('users')
        else:
            # Re-render form with errors (stays in modal with HTMX)
            return render(request, 'parts/user_form_modal.html', {'form': form, 'form_post_url': form_post_url, 'modal_title': modal_title, 'form_button_label': 'Toevoegen'})
    return HttpResponse(status=405)


@permission_required('core.change_user', raise_exception=True)
def user_edit(request, pk):
    """Handle user editing - GET returns form modal with user data, POST processes update"""
    editing_user = get_object_or_404(User, pk=pk, is_superuser=False)
    form_post_url = reverse('user-edit', args=[editing_user.id])
    modal_title = 'Gebruiker bewerken'

    if request.method == 'GET':
        # Return modal HTML with UserForm populated with user data
        form = UserForm(instance=editing_user)
        return render(request, 'parts/user_form_modal.html', {'form': form, 'form_post_url': form_post_url, 'modal_title': modal_title, 'form_button_label': 'Opslaan'})
    elif request.method == 'POST':
        form = UserForm(request.POST, instance=editing_user)
        if form.is_valid():
            update_user(
                user=editing_user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                brand=form.cleaned_data.get('brand'),
                groups=form.cleaned_data.get('groups')
            )
            # For HTMX requests, use HX-Redirect header to force full page redirect
            # For standard form posts, use normal redirect
            if 'HX-Request' in request.headers:
                response = HttpResponse(status=200)
                response['HX-Redirect'] = reverse('users')
                return response
            else:
                return redirect('users')
        else:
            # Re-render form with errors (stays in modal with HTMX)
            return render(request, 'parts/user_form_modal.html', {'form': form, 'form_post_url': form_post_url, 'modal_title': modal_title, 'form_button_label': 'Opslaan'})
    return HttpResponse(status=405)


@permission_required('core.delete_user', raise_exception=True)
def user_delete(request, pk):
    """Handle user deletion"""
    if request.method == 'POST':
        user = get_object_or_404(User, pk=pk, is_superuser=False)
        user.delete()
        # Redirect to users list - page reload resets filters
        return redirect('users')
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

        result = create_users_from_csv(csv_content)

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


