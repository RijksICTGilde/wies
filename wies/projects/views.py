import datetime
import json
import os
from urllib.parse import urlencode

from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.db import models
from django.db.models import Q, Count
from django.http import JsonResponse
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.core import management

from .models import Assignment, Colleague, Skill, Placement, Service, Ministry, Brand, Expertise
from .forms import AssignmentForm, ColleagueForm, PlacementForm, ServiceForm
from .services.sync import sync_colleagues_from_exact

from wies.exact.models import ExactEmployee, ExactProject


def home(request):
    """Redirect to dashboard as default landing page"""
    return redirect('/dashboard/')

def dashboard(request):
    """Dashboard view - uses DashboardService for data calculations"""
    from .services.dashboard import DashboardService
    
    # Get all dashboard data from service
    context = DashboardService.get_dashboard_data()
    
    return render(request, template_name='dashboard.html', context=context)


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
        elif action == 'sync_colleagues':
            sync_colleagues_from_exact()
            messages.success(request, 'Colleagues synced successfully from Exact')
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
    from django.urls import reverse
    
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
    from django.urls import reverse
    
    request = context['request']
    params = {}
    
    # Preserve existing query parameters
    for param in ['search', 'brand', 'skill', 'client', 'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to', 'order']:
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
    from django.urls import reverse
    
    request = context['request']
    
    # Preserve existing query parameters
    params = {}
    for param in ['search', 'skill', 'brand', 'client', 'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to', 'order']:
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
        
        # Get base queryset with common filters applied (but no status filter yet)
        base_qs = self.get_base_queryset()
        
        # Get filter options (simplified - no longer dynamic)
        context['organizations'] = [{'organization': org} for org in Assignment.objects.values_list('organization', flat=True).distinct().order_by('organization') if org]
        context['clients'] = Ministry.objects.order_by('name')
        
        # Define tab groups with correct counts using the same base queryset
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
        
        # Add compact filter configuration
        context['primary_filter'] = {
            'name': 'organization',
            'id': 'organization-filter',
            'placeholder': 'Alle opdrachtgevers',
            'options': [{'value': org['organization'], 'label': org['organization']} for org in context.get('organizations', [])]
        }
        
        context['search_field'] = 'name'
        context['search_placeholder'] = 'Zoek op naam, opdrachtgever of ministerie...'
        
        # Calculate active filter count
        modal_filter_params = ['skill', 'ministry', 'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))
        
        # Add modal filter configuration
        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'skill',
                'label': 'Rollen',
                'placeholder': 'Alle rollen',
                'options': [{'value': skill.id, 'label': skill.name} for skill in Skill.objects.all()]
            },
            {
                'type': 'select',
                'name': 'ministry',
                'label': 'Ministerie',
                'placeholder': 'Alle ministeries',
                'options': [{'value': client.id, 'label': client.name} for client in context.get('clients', [])]
            },
        ]
        
        return context
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            # Always return full tab section for HTMX requests to update counts
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
        qs = Colleague.objects.select_related('brand').prefetch_related('skills').order_by('name')
        
        # Apply search filter
        name_filter = self.request.GET.get('name')
        if name_filter:
            qs = qs.filter(name__icontains=name_filter)
        
        # Apply ordering
        ordering = self.request.GET.get('order')
        if ordering:
            qs = qs.order_by(ordering)

        # Apply specific filters
        filters = {
            'skill': 'skills__id',
            'brand': 'brand__id'
        }
        
        for param, lookup in filters.items():
            value = self.request.GET.get(param)
            if value:
                qs = qs.filter(**{lookup: value})
        
        return qs.distinct()
    
    def get_context_data(self, **kwargs):
        """Add dynamic filter options"""
        context = super().get_context_data(**kwargs)
        
        # Get filter options (simplified - no longer dynamic)
        context['skills'] = Skill.objects.order_by('name')
        context['brands'] = Brand.objects.order_by('name')
        
        # Add compact filter configuration
        context['primary_filter'] = {
            'name': 'brand',
            'id': 'brand-filter',
            'placeholder': 'Alle merken',
            'options': [{'value': brand.id, 'label': brand.name} for brand in context.get('brands', [])]
        }
        
        context['search_field'] = 'name'
        context['search_placeholder'] = 'Zoek op naam...'
        
        # Calculate active filter count
        modal_filter_params = ['skill']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))
        
        # Add modal filter configuration
        context['filter_groups'] = [
            {
                'type': 'select',
                'name': 'skill',
                'label': 'Rollen',
                'placeholder': 'Alle rollen',
                'options': [{'value': skill.id, 'label': skill.name} for skill in context.get('skills', [])]
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
        """Apply filters to placements queryset"""
        qs = Placement.objects.select_related(
            'colleague', 'colleague__brand', 'service', 'service__skill', 'service__assignment__ministry'
        ).order_by('-service__assignment__start_date')
        
        # Apply search filter
        search_filter = self.request.GET.get('search')
        if search_filter:
            qs = qs.filter(
                Q(colleague__name__icontains=search_filter) |
                Q(service__assignment__name__icontains=search_filter) |
                Q(service__assignment__organization__icontains=search_filter) |
                Q(service__assignment__ministry__name__icontains=search_filter) |
                Q(service__assignment__ministry__abbreviation__icontains=search_filter)
            )
        
        # Apply ordering
        ordering = self.request.GET.get('order')
        if ordering:
            qs = qs.order_by(ordering)

        # Apply specific filters
        filters = {
            'skill': 'service__skill__id',
            'brand': 'colleague__brand__id',
            'client': 'service__assignment__ministry__id'
        }
        
        for param, lookup in filters.items():
            value = self.request.GET.get(param)
            if value:
                qs = qs.filter(**{lookup: value})
                        
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
        context['clients'] = Ministry.objects.order_by('name')
        
        # Add consistent filter configuration
        context['primary_filter'] = {
            'name': 'brand',
            'id': 'brand-filter',
            'placeholder': 'Alle merken',
            'options': [{'value': brand.id, 'label': brand.name} for brand in context.get('brands', [])]
        }
        
        context['search_field'] = 'search'
        context['search_placeholder'] = 'Zoek op collega, opdracht of opdrachtgever...'
        
        # Calculate active filter count
        modal_filter_params = ['skill', 'client', 'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))
        
        # Add modal filter configuration
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
                'options': [{'value': client.id, 'label': client.name} for client in context.get('clients', [])]
            },
        ]

        return context


class PlacementAvailabilityView(ListView):
    """View for placements availability (timeline view)"""
    model = Placement
    template_name = 'placement_availability.html'
    
    def get_queryset(self):
        """Apply filters to placements queryset"""
        qs = Placement.objects.select_related(
            'colleague', 'colleague__brand', 'service', 'service__skill', 'service__assignment__ministry'
        ).order_by('-service__assignment__start_date')
        
        # Apply search filter
        search_filter = self.request.GET.get('search')
        if search_filter:
            qs = qs.filter(
                Q(colleague__name__icontains=search_filter) |
                Q(service__assignment__name__icontains=search_filter) |
                Q(service__assignment__organization__icontains=search_filter) |
                Q(service__assignment__ministry__name__icontains=search_filter) |
                Q(service__assignment__ministry__abbreviation__icontains=search_filter)
            )
        
        # Apply ordering
        ordering = self.request.GET.get('order')
        if ordering:
            qs = qs.order_by(ordering)

        # Apply specific filters
        filters = {
            'skill': 'service__skill__id',
            'brand': 'colleague__brand__id',
            'client': 'service__assignment__ministry__id'
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
        context['clients'] = Ministry.objects.order_by('name')
        
        context['primary_filter'] = {
            'name': 'brand',
            'id': 'brand-filter',
            'placeholder': 'Alle merken',
            'options': [{'value': brand.id, 'label': brand.name} for brand in context.get('brands', [])]
        }
        
        context['search_field'] = 'search'
        context['search_placeholder'] = 'Zoek op collega, opdracht of opdrachtgever...'
        
        # Calculate active filter count
        modal_filter_params = ['skill', 'client', 'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to']
        context['active_filter_count'] = sum(1 for param in modal_filter_params if self.request.GET.get(param))
        
        # Add modal filter configuration
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
                'options': [{'value': client.id, 'label': client.name} for client in context.get('clients', [])]
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
        
        # Calculate today position
        today_offset_days = (today - timeline_start).days
        total_timeline_days = (timeline_end - timeline_start).days
        today_position_percent = int((today_offset_days / total_timeline_days) * 100)
        
        # Apply filters to get filtered placements
        filtered_placements = self.get_queryset()
        
        # Get consultants from filtered placements
        consultants = Colleague.objects.filter(
            placements__in=filtered_placements
        ).distinct().order_by('name')
        
        # Generate consultant data for timeline
        consultant_data = []
        for consultant in consultants:
            consultant_placements = []
            total_current_hours = 0
            
            # Get filtered placements for this consultant
            placements = filtered_placements.filter(
                colleague=consultant
            ).select_related('service__assignment', 'service__skill')
            
            # Collect all placement data first
            placement_data_list = []
            for placement in placements:
                # Calculate placement dates
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
            
            # Sort placements by start date
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
            "range": range(2)
        })
        return context

class AssignmentDetail(DetailView):
    model = Assignment
    template_name = 'assignment_detail.html'
    
    def get_context_data(self, **kwargs):
        """Assignment detail view - uses AssignmentService for calculations"""
        from .services.assignment import AssignmentService
        
        context = super().get_context_data(**kwargs)
        assignment = self.get_object()
        
        # Get assignment statistics from service
        assignment_data = AssignmentService.get_assignment_statistics(assignment)
        context.update(assignment_data)
        
        return context

class AssignmentDeleteView(DeleteView):
    model = Assignment
    success_url = reverse_lazy("assignments")
    template_name = 'assignment_delete.html'

class AssignmentUpdateView(UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignment_update.html'

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

class ColleagueUpdateView(UpdateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleague_update.html'

# Placement views
class PlacementDetailView(DetailView):
    model = Placement
    template_name = 'placement_detail.html'

class PlacementUpdateView(UpdateView):
    model = Placement
    form_class = PlacementForm
    template_name = 'placement_update.html'

    def form_valid(self, form):
        placement_id = self.kwargs['pk']
        assignment_id = Placement.objects.get(id=placement_id).service.assignment.id
        super().form_valid(form)
        return redirect(Assignment.objects.get(id=assignment_id))

class PlacementCreateView(CreateView):
    model = Placement
    form_class = PlacementForm
    template_name = 'placement_new.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['assignment_id'] = self.kwargs['pk']
        return kwargs
    
    def form_valid(self, form):
        assignment_id = self.kwargs['pk']
        super().form_valid(form)
        return redirect(Assignment.objects.get(id=assignment_id))
    
class PlacementDeleteView(DeleteView):
    model = Placement
    success_url = reverse_lazy("assignments")
    template_name = 'placement_delete.html'
    
    def post(self, request, *args, **kwargs):
        placement_id = self.kwargs['pk']
        assignment_id = Placement.objects.get(id=placement_id).service.assignment.id
        super().post(request, *args, **kwargs)
        return redirect(Assignment.objects.get(id=assignment_id))

# Service views
class ServiceCreateView(CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_new.html'
    
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
    
    def post(self, request, *args, **kwargs):
        service_id = self.kwargs['pk']
        assignment_id = Service.objects.get(id=service_id).assignment.id
        super().post(request, *args, **kwargs)
        return redirect(Assignment.objects.get(id=assignment_id))

class ServiceDetailView(DetailView):
    model = Service
    template_name = 'service_detail.html'

# Client views
def clients(request):
    """Clients view - uses DashboardService for statistics"""
    from .services.dashboard import DashboardService
    
    search_query = request.GET.get('search', '')
    
    clients = Assignment.objects.values_list('organization', flat=True).distinct().exclude(organization='').exclude(organization__isnull=True)
    
    if search_query:
        clients = clients.filter(organization__icontains=search_query)
    
    clients = clients.order_by('organization')
    
    # Get statistics from service
    statistics = DashboardService.get_dashboard_statistics()
    
    return render(request, template_name='client_list.html', context={
        'clients': clients,
        'search_query': search_query,
        **statistics,  # Unpack all statistics
    })

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

# Ministry views
class MinistryListView(ListView):
    model = Ministry
    template_name = 'ministry_list.html'
    context_object_name = 'ministries'
    
    def get_queryset(self):
        queryset = Ministry.objects.annotate(
            assignment_count=Count('assignment')
        ).order_by('name')
        
        # Apply search filter
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
        
        # Count active filters
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

class MinistryUpdateView(UpdateView):
    model = Ministry
    template_name = 'ministry_form.html'
    fields = ['name', 'abbreviation']
    success_url = reverse_lazy('ministries')

class MinistryDeleteView(DeleteView):
    model = Ministry
    template_name = 'ministry_confirm_delete.html'
    success_url = reverse_lazy('ministries')

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
