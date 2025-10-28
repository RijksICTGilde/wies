from urllib.parse import urlencode

from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView, TemplateView
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Prefetch
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

from .models import Assignment, Colleague, Skill, Placement, Service, Ministry, Brand, Expertise
from .services.sync import sync_colleagues_from_otys_iir
from .services.placements import filter_placements_by_period

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
        return redirect(request.build_absolute_uri(reverse("home")))
    return HttpResponse(status=400)


def logout(request):
    if request.user:
        auth_logout(request)
    return redirect('/')


def get_service_details(request, service_id):
    """
    AJAX endpoint to get service details for placement form

    Returns JSON with service details including:
    - description, dates, and skill
    """
    try:
        service = Service.objects.get(id=service_id)

        data = {
            'description': service.description,
            'start_date': service.start_date.strftime('%d-%m-%Y') if service.start_date else '',
            'end_date': service.end_date.strftime('%d-%m-%Y') if service.end_date else '',
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
        elif action == 'load_data':
            management.call_command('loaddata', 'dummy_data.json')
            messages.success(request, 'Data loaded successfully from dummy_data.json')
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


class PlacementTableView(ListView):
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
            # If paginating, return only rows
            if self.request.GET.get('page'):
                return ['parts/placement_table_rows.html']
            # Otherwise, return full table (for filter changes)
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

        context['search_field'] = 'search'
        context['search_placeholder'] = 'Zoek op collega, opdracht of opdrachtgever...'

        modal_filter_params = ['brand', 'skill', 'client', 'ministry', 'period']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))

        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'brand',
                'label': 'Merk',
                'placeholder': 'Alle merken',
                'options': [{'value': brand.id, 'label': brand.name} for brand in context.get('brands', [])]
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


class AssignmentDetail(DetailView):
    model = Assignment
    template_name = 'assignment_detail.html'

    def get_context_data(self, **kwargs):
        """Assignment detail view - uses statistics functions for calculations"""

        context = super().get_context_data(**kwargs)
        assignment = self.get_object()

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


class ColleagueDetail(DetailView):
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
                'assignment_type': placement.service.assignment.assignment_type,
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


class GlobalSearchView(TemplateView):
    """
    Global search view that searches across all major entities:
    - Assignments
    - Colleagues 
    - Placements
    - Services
    - Ministries
    - Clients
    """
    template_name = 'search_results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        search_query = self.request.GET.get('search', '').strip()
        context['search_query'] = search_query
        
        
        # Initialize empty results
        context['results'] = {
            'assignments': [],
            'colleagues': [],
            'ministries': [],
            'total_count': 0
        }
        
        if search_query:
            # Search Assignments
            assignments_qs = Assignment.objects.filter(
                Q(name__icontains=search_query) |
                Q(organization__icontains=search_query) |
                Q(extra_info__icontains=search_query)
            ).select_related('ministry')
            assignments_count = assignments_qs.count()
            assignments = assignments_qs
            
            # Search Colleagues
            colleagues_qs = Colleague.objects.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(skills__name__icontains=search_query) |
                Q(expertises__name__icontains=search_query)
            ).distinct().select_related('brand').prefetch_related('skills', 'expertises')
            colleagues_count = colleagues_qs.count()
            colleagues = colleagues_qs
            
            # Search Ministries
            ministries_qs = Ministry.objects.filter(
                Q(name__icontains=search_query) |
                Q(abbreviation__icontains=search_query)
            ).annotate(assignment_count=Count('assignment'))
            ministries_count = ministries_qs.count()
            ministries = ministries_qs
            
            # Calculate total count
            total_count = assignments_count + colleagues_count + ministries_count
            
            # Update context with results
            context['results'] = {
                'assignments': assignments,
                'colleagues': colleagues,
                'ministries': ministries,
                'total_count': total_count
            }
        
        return context
