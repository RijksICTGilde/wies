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
from django.http import HttpResponse

from authlib.integrations.django_client import OAuth

from .models import Assignment, Colleague, Skill, Placement, Service, Ministry, Brand, User
from .services.sync import sync_all_otys_iir_records
from .services.placements import filter_placements_by_period
from .services.users import create_user
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

        brand_options = []
        for brand in Brand.objects.order_by('name'):
            brand_options.append({'value': brand.id, 'label': brand.name})
            if active_filters.get('brand') == str(brand.id):
                brand_options[-1]['selected'] = True

        skill_options = []
        for skill in Skill.objects.order_by('name'):
            skill_options.append({'value': skill.id, 'label': skill.name})
            if active_filters.get('skill') == str(skill.id):
                skill_options[-1]['selected'] = True

        clients = [
            {'id': org, 'name': org}
            for org in Assignment.objects.values_list('organization', flat=True).distinct().exclude(organization='').order_by('organization')
        ]

        client_options = []
        for client in clients:
            client_options.append({'value': client['id'], 'label': client['name']})
            if active_filters.get('client') == str(client['id']):
                client_options[-1]['selected'] = True

        ministry_options = []
        for ministry in Ministry.objects.order_by('name'):
            ministry_options.append({'value': ministry.id, 'label': ministry.name})
            if active_filters.get('ministry') == str(ministry.id):
                ministry_options[-1]['selected'] = True

        context['active_filters'] = active_filters
        context['active_filter_count'] = len(active_filters)

        # TODO: this can be become an object to help defining correctly and performing extra preprocessing on context
        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'brand',
                'label': 'Merk',
                'placeholder': 'Alle merken',
                'options': brand_options,
                'value_key': 'id',
                'label_ley': 'name',
            },
            {
                'type': 'select',
                'name': 'skill',
                'label': 'Rollen',
                'placeholder': 'Alle rollen',
                'options': skill_options,
            },
            {
                'type': 'select',
                'name': 'client',
                'label': 'Opdrachtgever',
                'placeholder': 'Alle opdrachtgevers',
                'options': client_options,
            },
            {
                'type': 'select',
                'name': 'ministry',
                'label': 'Ministerie',
                'placeholder': 'Alle ministeries',
                'options': ministry_options,
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

        return context


class AssignmentDetailView(DetailView):
    model = Assignment
    template_name = 'assignment_detail.html'


class ColleagueDetailView(DetailView):
    model = Colleague
    template_name = 'colleague_detail.html'

    def get_queryset(self):
        return Colleague.objects.prefetch_related(
            Prefetch('placements', queryset=Placement.objects.select_related(
                'service__assignment'
            ))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment_list = [
            {
                'name': placement.service.assignment.name,
                'id': placement.service.assignment.id,
            }
            for placement in self.object.placements.all()
        ]
        context["assignment_list"] = assignment_list
        return context


def client(request, name):
    assignments = Assignment.objects.filter(
        organization=name
    ).prefetch_related(
        Prefetch('services', queryset=Service.objects.prefetch_related(
            Prefetch('placements', queryset=Placement.objects.select_related('colleague'))
        ))
    )
    assignments_data = []

    for assignment in assignments:
        colleagues = [
            {'id': placement.colleague.pk, 'name': placement.colleague.name}
            for service in assignment.services.all()
            for placement in service.placements.all()
            if placement.colleague
        ]

        assignments_data.append({
            'id': assignment.pk,
            'name': assignment.name,
            'start_date': assignment.start_date,
            'end_date': assignment.end_date,
            'colleagues': colleagues,
            'status': assignment.status,
        })

    return render(request, template_name='client_detail.html', context={
        'client_name': name,
        'assignments': assignments_data
    })


class MinistryDetailView(DetailView):
    model = Ministry
    template_name = 'ministry_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignments = Assignment.objects.filter(
            ministry=self.object
        ).prefetch_related(
            Prefetch('services', queryset=Service.objects.prefetch_related(
                Prefetch('placements', queryset=Placement.objects.select_related('colleague'))
            ))
        )

        assignments_data = []
        for assignment in assignments:
            colleagues = [
                {'id': placement.colleague.pk, 'name': placement.colleague.name}
                for service in assignment.services.all()
                for placement in service.placements.all()
                if placement.colleague
            ]

            assignments_data.append({
                'id': assignment.pk,
                'name': assignment.name,
                'start_date': assignment.start_date,
                'end_date': assignment.end_date,
                'organization': assignment.organization,
                'colleagues': colleagues,
                'status': assignment.status,
            })

        context['assignments'] = assignments_data
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

        brand_options = []
        for brand in Brand.objects.order_by('name'):
            brand_options.append({'value': brand.id, 'label': brand.name})
            if active_filters.get('brand') == str(brand.id):
                brand_options[-1]['selected'] = True

        role_options = []
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
                'placeholder': 'Alle merken',
                'options': brand_options,
            },
            {
                'type': 'select',
                'name': 'role',
                'label': 'Rol',
                'placeholder': 'Alle rollen',
                'options': role_options,
            },
        ]

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
    if request.method == 'GET':
        # Return modal HTML with empty UserForm
        form = UserForm()
        return render(request, 'parts/user_form_modal.html', {'form': form})
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
            return render(request, 'parts/user_form_modal.html', {'form': form})
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
