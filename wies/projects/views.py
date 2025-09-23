import datetime
from urllib.parse import urlencode

from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView, TemplateView
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.db import models
from django.db.models import Q, Count
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate as auth_authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_not_required
from django.core import management
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse


from .models import Assignment, Colleague, Skill, Placement, Service, Ministry, Brand, Expertise, Note
from .forms import AssignmentForm, ColleagueForm, PlacementForm, ServiceForm
from .services.sync import sync_colleagues_from_exact, sync_colleagues_from_otys_iir
from .services.statistics import get_consultants_working, get_total_clients_count, get_total_budget
from .services.statistics import get_assignments_ending_soon, get_consultants_on_bench, get_new_leads, get_weeks_remaining, get_total_services, get_services_filled, get_average_utilization, get_available_since
from .services.placements import filter_placements_by_period

from wies.exact.models import ExactEmployee, ExactProject

from authlib.integrations.django_client import OAuth


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
        return redirect(request.build_absolute_uri(reverse("dashboard")))
    return HttpResponse(status=400)


def logout(request):
    if request.user:
        auth_logout(request)
    return redirect('/')

def dashboard(request):
    """Dashboard view - uses statistics functions for data calculations"""
    
    # Get active tab from request
    active_tab = request.GET.get('tab', 'ending_soon')
    
    total_budget = get_total_budget()
    formatted_budget = f"{int(total_budget):,}".replace(',', '.') if total_budget else "0"

    # Get consultants on bench with availability info
    consultants_bench = get_consultants_on_bench()
    for consultant in consultants_bench:
        consultant.available_since = get_available_since(consultant)

    # Statistics context
    context = {
        'consultants_working': get_consultants_working(),
        'total_clients_count': get_total_clients_count(),
        'total_budget': total_budget,
        'formatted_budget': formatted_budget,
        'total_services': get_total_services(),
        'services_filled': get_services_filled(),
        'average_utilization': get_average_utilization(),
        'assignments_ending_soon': get_assignments_ending_soon(),
        'consultants_bench': consultants_bench,
        'new_leads': get_new_leads(),
        'active_tab': active_tab,
    }

    # If HTMX request, return the dashboard tabs section
    if 'HX-Request' in request.headers:
        return render(request, 'parts/dashboard_tabs_section.html', context)
    
    return render(request, 'dashboard.html', context)


def get_service_details(request, service_id):
    """
    AJAX endpoint to get service details for placement form
    
    Returns JSON with service details including:
    - description, dates, cost calculation, and skill
    """
    try:
        service = Service.objects.get(id=service_id)
        
        # Calculate total cost
        total_cost = service.get_total_cost()
        weeks = service.get_weeks()
        
        if service.cost_type == "FIXED_PRICE" and service.fixed_cost:
            cost_display = f"€{service.fixed_cost:,.2f}".replace(',', '.')
            cost_calculation = None
        elif total_cost and weeks and service.hours_per_week:
            cost_display = f"€{total_cost:,.2f}".replace(',', '.')
            cost_calculation = f"{weeks} weken × {service.hours_per_week} uur × €100"
        else:
            cost_display = "Niet beschikbaar"
            cost_calculation = None
        
        data = {
            'description': service.description,
            'start_date': service.start_date.strftime('%d-%m-%Y') if service.start_date else '',
            'end_date': service.end_date.strftime('%d-%m-%Y') if service.end_date else '',
            'cost': cost_display,
            'cost_calculation': cost_calculation,
            'cost_type': service.cost_type,
            'skill': service.skill.name if service.skill else 'Geen rol opgegeven'
        }
        return JsonResponse(data)
    except Service.DoesNotExist:
        return JsonResponse({'error': 'Service not found'}, status=404)

@user_passes_test(lambda u: u.is_superuser and u.is_authenticated, login_url='/admin/login/')
def admin_db(request):
    context = {
        'assignment_count': Assignment.objects.count()
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
            Expertise.objects.all().delete()

            ExactEmployee.objects.all().delete()
            ExactProject.objects.all().delete()

        elif action == 'load_data':
            management.call_command('loaddata', 'dummy_data.json')
            management.call_command('loaddata', 'exact_dummy_data.json')
            messages.success(request, 'Data loaded successfully from dummy_data.json')
        elif action == 'sync_colleagues_exact':
            sync_colleagues_from_exact()
            messages.success(request, 'Colleagues synced successfully from Exact')
        elif action == 'sync_colleagues_otys_iir':
            sync_colleagues_from_otys_iir()
            messages.success(request, 'Colleagues synced successfully from OTYS IIR')
        return redirect('admin-db')
    
    return render(request, 'admin_db.html', context)


# Template filters and tags
@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)


@register.filter
def lookup(dictionary, key):
    """Template filter to lookup values in dictionary or GET params"""
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None


@register.filter
def get_skill_labels(skills):
    """Get skill names from skill objects"""
    return [skill.name for skill in skills.all()]


@register.filter
def format_currency(value):
    """Format number as currency with thousand separators"""
    if value is None:
        return None
    return f"{value:,.2f}".replace(',', '.')


@register.simple_tag(takes_context=True)
def assignments_url_with_tab(context, tab_key):
    """
    Build assignments URL with tab and preserved query parameters
    
    Args:
        context: Template context containing request
        tab_key: Tab identifier (e.g., 'leads', 'current', 'historical')
    
    Returns:
        URL with tab parameter and preserved filters
    """
    
    request = context['request']
    params = {'tab': tab_key}
    
    # Preserve existing query parameters
    for param in ['name', 'order', 'skill', 'organization', 'ministry', 'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to']:
        value = request.GET.get(param)
        if value:
            params[param] = value
    
    return f"{reverse('assignments')}?{urlencode(params)}"


@register.simple_tag(takes_context=True)
def placements_url_with_filters(context, url_name):
    """
    Build placements URL with preserved query parameters
    
    Args:
        context: Template context containing request
        url_name: URL name (e.g., 'placements-inzet', 'placements-beschikbaarheid')
    
    Returns:
        URL with preserved filters
    """
    
    request = context['request']
    params = {}
    
    # Preserve existing query parameters
    for param in ['search', 'brand', 'skill', 'client', 'period', 'order']:
        value = request.GET.get(param)
        if value:
            params[param] = value
    
    if params:
        return f"{reverse(url_name)}?{urlencode(params)}"
    else:
        return reverse(url_name)


@register.simple_tag(takes_context=True)
def placements_url_with_tab(context, tab_key):
    """
    Build placements URL with tab and preserved query parameters
    
    Args:
        context: Template context containing request
        tab_key: Tab identifier (e.g., 'inzet', 'timeline')
    
    Returns:
        URL with tab parameter and preserved filters
    """
    
    request = context['request']
    
    # Preserve existing query parameters
    params = {}
    for param in ['search', 'skill', 'brand', 'client', 'period', 'order']:
        value = request.GET.get(param)
        if value:
            params[param] = value
    
    # Add tab parameter for all tabs
    params['tab'] = tab_key
    return f"{reverse('placements')}?{urlencode(params)}"


class AssignmentTabsView(ListView):
    template_name = 'assignment_tabs.html'
    model = Assignment

    def get_base_queryset(self):
        """Get base queryset without status filtering"""
        qs = Assignment.objects.select_related('ministry').prefetch_related('services__skill').order_by('-start_date')
        
        # Apply name filter if provided
        name_filter = self.request.GET.get('name')
        if name_filter:
            qs = qs.filter(
                models.Q(name__icontains=name_filter) | 
                models.Q(extra_info__icontains=name_filter) | 
                models.Q(organization__icontains=name_filter) |
                models.Q(ministry__name__icontains=name_filter) |
                models.Q(ministry__abbreviation__icontains=name_filter)
            )
        
        # Apply skill filter if provided
        skill_filter = self.request.GET.get('skill')
        if skill_filter:
            qs = qs.filter(services__skill__id=skill_filter).distinct()
        
        # Apply specific filters
        filters = {
            'organization': 'organization',
            'ministry': 'ministry__id'
        }
        
        for param, lookup in filters.items():
            value = self.request.GET.get(param)
            if value:
                qs = qs.filter(**{lookup: value})

        # Apply order if provided
        order = self.request.GET.get('order')
        if order:
            qs = qs.order_by(order)
            
        return qs
    
    def get_queryset(self):
        """Get queryset for the active tab only"""
        active_tab = self.request.GET.get('tab', 'leads')
        base_qs = self.get_base_queryset()
        
        # Define status mapping for tabs
        tab_statuses = {
            'leads': ['LEAD', 'OPEN'],
            'current': ['LOPEND'],
            'historical': ['AFGEWEZEN', 'HISTORISCH']
        }
        
        # Filter by active tab statuses
        return base_qs.filter(status__in=tab_statuses[active_tab])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the active tab from request, default to 'leads'
        active_tab = self.request.GET.get('tab', 'leads')
        context['active_tab'] = active_tab
        
        base_qs = self.get_base_queryset()
        
        context['organizations'] = [{'organization': org} for org in Assignment.objects.values_list('organization', flat=True).distinct().order_by('organization') if org]
        context['skills'] = Skill.objects.all()
        context['clients'] = Ministry.objects.all()
        
        tab_groups = {
            'leads': {
                'title': 'Leads & open',
                'statuses': ['LEAD', 'OPEN'],
                'queryset': base_qs.filter(status__in=['LEAD', 'OPEN'])
            },
            'current': {
                'title': 'Huidig', 
                'statuses': ['LOPEND'],
                'queryset': base_qs.filter(status__in=['LOPEND'])
            },
            'historical': {
                'title': 'Historisch & afgewezen',
                'statuses': ['AFGEWEZEN', 'HISTORISCH'], 
                'queryset': base_qs.filter(status__in=['AFGEWEZEN', 'HISTORISCH'])
            }
        }
        
        context['tab_groups'] = tab_groups
        context['active_assignments'] = tab_groups[active_tab]['queryset']

        
        context['search_field'] = 'name'
        context['search_placeholder'] = 'Zoek op naam, opdrachtgever of ministerie...'
        
        modal_filter_params = ['skill', 'ministry', 'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))
        
        context['filter_groups'] = [
            {
            'type': 'select',
            'name': 'organization',
            'label': 'opdrachtgever',
            'placeholder': 'Alle opdrachtgevers',
            'options': [{'value': org['organization'], 'label': org['organization']} for org in context.get('organizations', [])]
            }, 
            {
                'type': 'select',
                'name': 'skill',
                'label': 'Rollen',
                'placeholder': 'Alle rollen',
                'options': [{'value': skill.id, 'label': skill.name} for skill in context.get('skills', [])]
            },
            {
                'type': 'select',
                'name': 'ministry',
                'label': 'Ministerie',
                'placeholder': 'Alle ministeries',
                'options': [{'value': client.id, 'label': client.name} for client in context.get('clients', [])]
            },
        ]

        context['primary_action'] = {
            'url': '/assignments/new',
            'button_text': 'Opdracht toevoegen'
        }
        
        return context
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            return ['parts/assignment_tabs_section.html']
        else:
            return ['assignment_tabs.html']


class ColleagueList(ListView):
    """
    View for colleagues list with filtering capabilities
    
    Features:
    - Search by name
    - Filter by skills and brands
    - HTMX support for smooth interactions
    """
    template_name = 'colleague_list.html'
    model = Colleague
    
    def get_queryset(self):
        """Apply filters to colleagues queryset"""
        qs = Colleague.objects.select_related('brand').prefetch_related('skills', 'expertises').order_by('name')
        
        name_filter = self.request.GET.get('name')
        if name_filter:
            qs = qs.filter(name__icontains=name_filter)
        
        ordering = self.request.GET.get('order')
        if ordering:
            qs = qs.order_by(ordering)

        filters = {
            'skill': 'skills__id',
            'brand': 'brand__id',
            'expertise': 'expertises__id'
        }
        
        for param, lookup in filters.items():
            value = self.request.GET.get(param)
            if value:
                qs = qs.filter(**{lookup: value})
        
        status_filter = self.request.GET.get('status')
        if status_filter == 'beschikbaar':
            # Colleagues who have NO active LOPEND placements (may have historical ones)
            active_colleague_ids = Placement.objects.filter(
                service__assignment__status='LOPEND'
            ).values_list('colleague_id', flat=True).distinct()
            qs = qs.exclude(id__in=active_colleague_ids)
        elif status_filter == 'ingezet':
            qs = qs.filter(
                placements__colleague__isnull=False,
                placements__service__assignment__status='LOPEND'
            )
        
        return qs.distinct()
    
    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)

        # Sort ingezet colleagues by availability date (sooner first)
        colleagues = list(context['object_list'])
        # Sort by end_date, with None values first
        colleagues.sort(key=lambda c: c.end_date or datetime.date.min)
        context['object_list'] = colleagues

        context['skills'] = Skill.objects.order_by('name')
        context['brands'] = Brand.objects.order_by('name')
        context['expertises'] = Expertise.objects.order_by('name')
        
        context['primary_filter'] = {
            'name': 'brand',
            'id': 'brand-filter',
            'placeholder': 'Alle merken',
            'options': [{'value': brand.id, 'label': brand.name} for brand in context.get('brands', [])]
        }
        
        context['search_field'] = 'name'
        context['search_placeholder'] = 'Zoek op naam...'
        
        modal_filter_params = ['skill', 'expertise', 'status']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))
        
        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'skill',
                'label': 'Rollen',
                'placeholder': 'Alle rollen',
                'options': [{'value': skill.id, 'label': skill.name} for skill in context.get('skills', [])]
            },
            {
                'type': 'select',
                'name': 'expertise',
                'label': 'ODI Expertise',
                'placeholder': 'Alle expertise',
                'options': [{'value': expertise.id, 'label': expertise.name} for expertise in context.get('expertises', [])]
            },
            {
                'type': 'select',
                'name': 'status',
                'label': 'Status',
                'placeholder': 'Alle statussen',
                'options': [
                    {'value': 'beschikbaar', 'label': 'Beschikbaar'},
                    {'value': 'ingezet', 'label': 'Ingezet'}
                ]
            }
        ]
        
        return context
    
    def get_template_names(self):
        """Return appropriate template based on request type"""
        if 'HX-Request' in self.request.headers:
            return ['parts/colleague_table.html']
        else:
            return ['colleague_list.html']


def add_months(source_date, months):
    """Add months to a date using only stdlib"""
    year = source_date.year + (source_date.month + months - 1) // 12
    month = (source_date.month + months - 1) % 12 + 1
    day = min(source_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 31][month - 1])
    return source_date.replace(year=year, month=month, day=day)


def add_timedelta(source_date, timedelta):
    """Add timedelta to date"""
    dt = datetime.datetime(source_date.year, source_date.month, source_date.day)
    return (dt + timedelta).date()


class PlacementTableView(ListView):
    """View for placements table view"""
    model = Placement
    template_name = 'placement_table.html'

    def get_queryset(self):
        """Apply filters to placements queryset - only show LOPEND assignments, not LEAD"""
        qs = Placement.objects.select_related(
            'colleague', 'colleague__brand', 'service', 'service__skill', 'service__assignment__ministry'
        ).filter(
            service__assignment__status='LOPEND'
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

        ordering = self.request.GET.get('order')
        if ordering:
            qs = qs.order_by(ordering)

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
            return ['parts/placement_table.html']
        return ['placement_table.html']

    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)

        context['skills'] = Skill.objects.order_by('name')
        context['brands'] = Brand.objects.order_by('name')
        context['clients'] = [
            {'id': org, 'name': org}
            for org in Assignment.objects.values_list('organization', flat=True).distinct().exclude(organization='').order_by('organization')
        ]
        context['ministries'] = Ministry.objects.order_by('name')

        context['primary_filter'] = {
            'name': 'brand',
            'id': 'brand-filter',
            'placeholder': 'Alle merken',
            'options': [{'value': brand.id, 'label': brand.name} for brand in context.get('brands', [])]
        }

        context['search_field'] = 'search'
        context['search_placeholder'] = 'Zoek op collega, opdracht of opdrachtgever...'

        modal_filter_params = ['skill', 'client', 'ministry', 'period']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))

        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'skill',
                'label': 'Rollen',
                'placeholder': 'Alle rollen',
                'options': [{'value': skill.id, 'label': skill.name} for skill in context.get('skills', [])]
            },
            {
                'type': 'select',
                'name': 'client',
                'label': 'Opdrachtgever',
                'placeholder': 'Alle opdrachtgevers',
                'options': [{'value': client['id'], 'label': client['name']} for client in context.get('clients', [])]
            },
            {
                'type': 'select',
                'name': 'ministry',
                'label': 'Ministerie',
                'placeholder': 'Alle ministeries',
                'options': [{'value': ministry.id, 'label': ministry.name} for ministry in context.get('ministries', [])]
            },
            {
                'type': 'date_range',
                'name': 'period',
                'label': 'Periode',
                'from_label': 'Van',
                'to_label': 'Tot',
                'require_both': True
            },
        ]

        return context


class PlacementAvailabilityView(ListView):
    """View for placements availability (timeline view)"""
    model = Placement
    template_name = 'placement_availability.html'
    
    def get_queryset(self):
        """Apply filters to placements queryset - only show LOPEND assignments, not LEAD"""
        qs = Placement.objects.select_related(
            'colleague', 'colleague__brand', 'service', 'service__skill', 'service__assignment__ministry'
        ).filter(
            service__assignment__status='LOPEND'  # Only show placements from running assignments
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
        
        ordering = self.request.GET.get('order')
        if ordering:
            qs = qs.order_by(ordering)

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

        return qs.distinct()

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if 'HX-Request' in self.request.headers:
            return ['parts/placement_timeline.html']
        return ['placement_availability.html']

    def get_context_data(self, **kwargs):
        """Add dynamic filter options and timeline data"""
        context = super().get_context_data(**kwargs)
        
        context['skills'] = Skill.objects.order_by('name')
        context['brands'] = Brand.objects.order_by('name')
        context['clients'] = [
            {'id': org, 'name': org} 
            for org in Assignment.objects.values_list('organization', flat=True).distinct().exclude(organization='').order_by('organization')
        ]
        context['ministries'] = Ministry.objects.order_by('name')
        
        context['primary_filter'] = {
            'name': 'brand',
            'id': 'brand-filter',
            'placeholder': 'Alle merken',
            'options': [{'value': brand.id, 'label': brand.name} for brand in context.get('brands', [])]
        }
        
        context['search_field'] = 'search'
        context['search_placeholder'] = 'Zoek op collega, opdracht of opdrachtgever...'

        modal_filter_params = ['skill', 'client', 'ministry']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))

        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'skill',
                'label': 'Rollen',
                'placeholder': 'Alle rollen',
                'options': [{'value': skill.id, 'label': skill.name} for skill in context.get('skills', [])]
            },
            {
                'type': 'select',
                'name': 'client',
                'label': 'Opdrachtgever',
                'placeholder': 'Alle opdrachtgevers',
                'options': [{'value': client['id'], 'label': client['name']} for client in context.get('clients', [])]
            },
            {
                'type': 'select',
                'name': 'ministry',
                'label': 'Ministerie',
                'placeholder': 'Alle ministeries',
                'options': [{'value': ministry.id, 'label': ministry.name} for ministry in context.get('ministries', [])]
            },
        ]

        context.update(self._get_timeline_context())
        return context
    
    def _get_timeline_context(self):
        """
        Generate timeline context data for availability view
        
        Returns:
            Dict with timeline data including months, consultant data, and positioning
        """
        today = datetime.date.today()
        timeline_start = add_timedelta(today, datetime.timedelta(weeks=-12)).replace(day=1)
        timeline_end = add_timedelta(today, datetime.timedelta(weeks=36)).replace(day=1)
        
        # Generate month headers
        months = []
        current_month = timeline_start.replace(day=1)
        while current_month <= timeline_end:
            months.append({
                'date': current_month,
                'name': current_month.strftime('%b %Y')
            })
            current_month = add_months(current_month, 1)
        
        today_offset_days = (today - timeline_start).days
        total_timeline_days = (timeline_end - timeline_start).days
        today_position_percent = int((today_offset_days / total_timeline_days) * 100)
        
        filtered_placements = self.get_queryset()
        
        consultants = Colleague.objects.filter(
            placements__in=filtered_placements
        ).distinct().order_by('name')
        
        # Generate consultant data for timeline
        consultant_data = []
        for consultant in consultants:
            consultant_placements = []
            total_current_hours = 0
            
            placements = filtered_placements.filter(
                colleague=consultant
            ).select_related('service__assignment', 'service__skill')
            
            placement_data_list = []
            for placement in placements:
                if placement.period_source == 'PLACEMENT':
                    start_date = placement.specific_start_date
                    end_date = placement.specific_end_date
                elif placement.period_source == 'SERVICE':
                    if placement.service.period_source == 'ASSIGNMENT':
                        start_date = placement.service.assignment.start_date
                        end_date = placement.service.assignment.end_date
                    else:
                        start_date = placement.service.specific_start_date
                        end_date = placement.service.specific_end_date
                else:
                    continue
                
                if not start_date or not end_date:
                    continue
                
                # Calculate timeline positions
                start_offset_days = (start_date - timeline_start).days
                end_offset_days = (end_date - timeline_start).days
                
                if start_offset_days < 0:
                    start_offset_days = 0
                if end_offset_days > total_timeline_days:
                    end_offset_days = total_timeline_days
                
                start_offset_percent = int((start_offset_days / total_timeline_days) * 100)
                width_percent = int(((end_offset_days - start_offset_days) / total_timeline_days) * 100)
                
                # Check if placement is current
                if start_date <= today <= end_date:
                    total_current_hours += placement.service.hours_per_week or 0
                
                placement_data_list.append({
                    'project_name': placement.service.assignment.name,
                    'hours_per_week': placement.service.hours_per_week or 0,
                    'start_offset_percent': start_offset_percent,
                    'width_percent': width_percent,
                    'start_date': start_date,
                    'end_date': end_date,
                })
            
            placement_data_list.sort(key=lambda x: x['start_date'])
            
            # Calculate horizontal positioning for overlapping assignments
            max_lanes = 1
            for i, placement in enumerate(placement_data_list):
                lane = 0
                # Check for overlaps with previous placements
                for j in range(i):
                    prev_placement = placement_data_list[j]
                    # Check if current placement overlaps with previous placement
                    if (placement['start_date'] < prev_placement['end_date'] and 
                        placement['end_date'] > prev_placement['start_date']):
                        # There's an overlap, try next lane
                        lane = max(lane, prev_placement.get('lane', 0) + 1)
                
                placement['lane'] = lane
                max_lanes = max(max_lanes, lane + 1)
            
            # Convert lane to top position (each lane is 30px high)
            for placement in placement_data_list:
                placement['top_px'] = placement['lane'] * 30
                # Remove temporary fields
                del placement['start_date']
                del placement['end_date']
                del placement['lane']
            
            consultant_placements = placement_data_list
            
            # Calculate total tracks height based on max lanes
            total_tracks_height = max(max_lanes * 30, 60)  # Minimum 60px height
            
            consultant_data.append({
                'consultant': consultant,
                'placements': consultant_placements,
                'total_current_hours': total_current_hours,
                'total_tracks_height': total_tracks_height,
            })
        
        return {
            'timeline_start': timeline_start,
            'timeline_end': timeline_end, 
            'months': months,
            'today_position_percent': today_position_percent,
            'consultant_data': consultant_data,
        }


# Simplified view classes without duplicated logic
class AssignmentCreateView(CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignment_new.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "placement_form": PlacementForm(),
            "range": range(2),
            "cancel_url": "/assignments/"
        })
        return context

class AssignmentDetail(DetailView):
    model = Assignment
    template_name = 'assignment_detail.html'
    
    def get_context_data(self, **kwargs):
        """Assignment detail view - uses statistics functions for calculations"""
        
        context = super().get_context_data(**kwargs)
        assignment = self.get_object()
        
        total_budget = assignment.get_total_services_cost()
        formatted_budget = f"{int(total_budget):,}".replace(',', '.') if total_budget else "0"

        assignment_data = {
            'weeks_remaining': get_weeks_remaining(assignment),
            'total_budget': total_budget,
            'formatted_budget': formatted_budget,
            'budget_percentage': 85,  # Placeholder percentage,
            'project_score': 8.5,  # This could be calculated based on deadlines, budget, etc.,
        } 

        context.update(assignment_data)
        
        # Get the active tab from request, default to 'diensten'
        active_tab = self.request.GET.get('tab', 'services')
        context['active_tab'] = active_tab
        
        # Add notes to context
        context['notes'] = assignment.notes.all()
        
        # Define tab groups for navigation
        tab_groups = {
            'services': {
                'title': 'Diensten',
                'content': 'services_and_placements'
            },
            'notes': {
                'title': 'Notities',
                'content': 'notes'
            }
        }
        context['tab_groups'] = tab_groups
        
        return context

class AssignmentDeleteView(DeleteView):
    model = Assignment
    success_url = reverse_lazy("assignments")
    template_name = 'assignment_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/assignments/{context["object"].pk}/'
        return context

class AssignmentUpdateView(UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignment_update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/assignments/{context["object"].pk}/'
        return context

class ColleagueCreateView(CreateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleague_new.html'

    def form_valid(self, form):
        form.instance.source = 'wies'
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['skills'] = Skill.objects.all()
        context['cancel_url'] = '/colleagues/'
        return context

class ColleagueDetail(DetailView):
    model = Colleague
    template_name = 'colleague_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment_list = [
            {
                'name': placement.service.assignment.name,
                'id': placement.service.assignment.id,
                'assignment_type': placement.service.assignment.assignment_type,
            }
            for placement in self.object.placements.all()
        ]
        context["assignment_list"] = assignment_list
        return context

class ColleagueDeleteView(DeleteView):
    model = Colleague
    success_url = reverse_lazy("colleagues")
    template_name = 'colleague_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/colleagues/{context["object"].pk}/'
        return context

class ColleagueUpdateView(UpdateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleague_update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/colleagues/{context["object"].pk}/'
        return context

class PlacementDetailView(DetailView):
    model = Placement
    template_name = 'placement_detail.html'

class PlacementUpdateView(UpdateView):
    model = Placement
    form_class = PlacementForm
    template_name = 'placement_update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/assignments/{context["object"].service.assignment.id}/'
        return context

    def form_valid(self, form):
        placement_id = self.kwargs['pk']
        assignment_id = Placement.objects.get(id=placement_id).service.assignment.id
        super().form_valid(form)
        return redirect(Assignment.objects.get(id=assignment_id))

class PlacementCreateView(CreateView):
    model = Placement
    form_class = PlacementForm
    template_name = 'placement_new.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = Service.objects.get(id=self.kwargs['pk'])
        context['service'] = service
        context['cancel_url'] = f'/assignments/{service.assignment.id}/'
        return context
    
    def form_valid(self, form):
        service_id = self.kwargs['pk']
        form.service_id = service_id
        super().form_valid(form)
        return redirect(Service.objects.get(id=service_id).assignment)

class PlacementDeleteView(DeleteView):
    model = Placement
    success_url = reverse_lazy("assignments")
    template_name = 'placement_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/assignments/{context["object"].service.assignment.id}/'
        return context

    def post(self, request, *args, **kwargs):
        placement_id = self.kwargs['pk']
        assignment_id = Placement.objects.get(id=placement_id).service.assignment.id
        super().post(request, *args, **kwargs)
        return redirect(Assignment.objects.get(id=assignment_id))

class ServiceCreateView(CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_new.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment_id = self.kwargs['pk']
        context['cancel_url'] = f'/assignments/{assignment_id}/'
        return context

    def form_valid(self, form):
        assignment_id = self.kwargs['pk']
        form.assignment_id = assignment_id
        super().form_valid(form)
        return redirect(Assignment.objects.get(id=assignment_id))

class ServiceUpdateView(UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_update.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/assignments/{context["object"].assignment.id}/'
        return context

    def form_valid(self, form):
        # TODO: not super happy about this work around, but good enough for now
        service_id = self.kwargs['pk']
        assignment_id = Service.objects.get(id=service_id).assignment.id
        super().form_valid(form)
        return redirect(Assignment.objects.get(id=assignment_id))

class ServiceDeleteView(DeleteView):
    model = Service
    success_url = reverse_lazy("assignments")
    template_name = 'service_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/assignments/{context["object"].assignment.id}/'
        return context

    def post(self, request, *args, **kwargs):
        service_id = self.kwargs['pk']
        assignment_id = Service.objects.get(id=service_id).assignment.id
        super().post(request, *args, **kwargs)
        return redirect(Assignment.objects.get(id=assignment_id))

class ServiceDetailView(DetailView):
    model = Service
    template_name = 'service_detail.html'

def clients(request):
    """Clients view - uses statistics functions for statistics"""
    
    search_query = request.GET.get('search', '')
    
    clients = Assignment.objects.values_list('organization', flat=True).distinct().exclude(organization='').exclude(organization__isnull=True)
    
    if search_query:
        clients = clients.filter(organization__icontains=search_query)
    
    clients = clients.order_by('organization')
    
    total_budget = get_total_budget()
    formatted_budget = f"{int(total_budget):,}".replace(',', '.') if total_budget else "0"
    
    context = {
        'clients': clients,
        'consultants_working': get_consultants_working(),
        'total_clients_count': get_total_clients_count(),
        'total_budget': total_budget,
        'formatted_budget': formatted_budget,
    }
    
    if 'HX-Request' in request.headers:
        return render(request, 'parts/clients_table.html', context)
    
    return render(request, 'client_list.html', context)

def client(request, name):
    assignments = Assignment.objects.filter(organization=name)
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

class MinistryListView(ListView):
    model = Ministry
    template_name = 'ministry_list.html'
    context_object_name = 'ministries'
    
    def get_queryset(self):
        queryset = Ministry.objects.annotate(
            assignment_count=Count('assignment')
        ).order_by('name')
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(abbreviation__icontains=search_query)
            )
        
        return queryset
    
    def get_filter_context_data(self):
        """Configure filters for the ministry list"""
        search_query = self.request.GET.get('search', '')
        
        active_filter_count = 0
        if search_query:
            active_filter_count += 1
        
        return {
            'search_field': 'search',
            'search_placeholder': 'Zoek ministeries...',
            'active_filter_count': active_filter_count,
            'filter_groups': [],  # No additional filters for ministries
        }

    def get_template_names(self):
        """Return appropriate template based on request type"""
        if 'HX-Request' in self.request.headers:
            return ['parts/ministry_table.html']
        else:
            return ['ministry_list.html']

class MinistryCreateView(CreateView):
    model = Ministry
    template_name = 'ministry_form.html'
    fields = ['name', 'abbreviation']
    success_url = reverse_lazy('ministries')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = '/ministries/'
        return context


class MinistryUpdateView(UpdateView):
    model = Ministry
    template_name = 'ministry_form.html'
    fields = ['name', 'abbreviation']
    success_url = reverse_lazy('ministries')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/ministries/{context["object"].pk}/'
        return context


class MinistryDeleteView(DeleteView):
    model = Ministry
    template_name = 'ministry_confirm_delete.html'
    success_url = reverse_lazy('ministries')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/ministries/{context["object"].pk}/'
        return context

class MinistryDetailView(DetailView):
    model = Ministry
    template_name = 'ministry_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignments = Assignment.objects.filter(ministry=self.object)
        
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


class ProfileView(TemplateView):
    template_name = 'profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get tab from query parameter, default to 'overzicht'
        active_tab = self.request.GET.get('tab', 'overzicht')
        context['active_tab'] = active_tab
        
        # Get or create colleague profile for current user
        colleague = None
        recent_placements = []
        if hasattr(self.request.user, 'colleague'):
            colleague = self.request.user.colleague
            if colleague:
                # Get recent placements for this colleague
                recent_placements = colleague.placements.select_related(
                    'service__assignment'
                ).order_by('-specific_end_date', '-service__assignment__end_date')[:3]
        
        context['colleague'] = colleague
        context['recent_placements'] = recent_placements
        return context


def add_note(request, assignment_id):
    """Add a new note to an assignment"""
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            # Get the colleague associated with the current user
            if hasattr(request.user, 'colleague') and request.user.colleague:
                assignment = Assignment.objects.get(pk=assignment_id)
                colleague = request.user.colleague
                Note.objects.create(
                    assignment=assignment,
                    colleague=colleague,
                    message=message
                )
                messages.success(request, 'Notitie succesvol toegevoegd.')
            else:
                messages.error(request, 'Geen collega profiel gevonden voor huidige gebruiker.')
        else:
            messages.error(request, 'Notitie mag niet leeg zijn.')
    
    return redirect('assignment-detail', pk=assignment_id)
