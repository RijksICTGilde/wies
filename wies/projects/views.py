import datetime
import json
from urllib.parse import urlencode

from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView, TemplateView
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.db import models
from django.db.models import Case, When, Max, F, Q, Count
from django.http import JsonResponse

from .models import Assignment, Colleague, Skill, Placement, Service, Ministry, Brand
from .forms import AssignmentForm, ColleagueForm, PlacementForm, ServiceForm


def home(request):
    """Redirect to placements page as default landing page"""
    return redirect('/placements/')


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


# Template filters and tags
@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)


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


class DynamicFilterMixin:
    """
    Mixin to provide dynamic filtering functionality for list views
    
    Provides methods for:
    - Date filtering with complex field mappings
    - Dynamic filter options based on current filters
    """
    
    def apply_date_filters(self, qs, date_field_mapping=None):
        """
        Apply date filters to queryset
        
        Args:
            qs: Base queryset
            date_field_mapping: Dict mapping filter params to model fields
        
        Returns:
            Filtered queryset
        """
        if not date_field_mapping:
            return qs
            
        date_filters = [
            ('start_date_from', 'gte'), ('start_date_to', 'lte'),
            ('end_date_from', 'gte'), ('end_date_to', 'lte')
        ]
        
        for param, operator in date_filters:
            value = self.request.GET.get(param)
            if value:
                date_type = 'start_date' if 'start_date' in param else 'end_date'
                lookup = f'{date_type}__{operator}'
                
                # Apply filter using the field mapping
                filter_kwargs = {}
                for filter_param, model_field in date_field_mapping.items():
                    filter_kwargs[f'{model_field}__{lookup}'] = value
                
                if filter_kwargs:
                    qs = qs.filter(**filter_kwargs)
        
        return qs
    
    def get_dynamic_filter_options(self, base_qs, filter_configs):
        """
        Get dynamic filter options based on current filters
        
        Args:
            base_qs: Base queryset to filter from
            filter_configs: List of dicts with filter configuration
        
        Returns:
            Dict with filter options for each filter type
        """
        context = {}
        
        for config in filter_configs:
            filter_name = config['name']
            model = config['model']
            field_path = config['field_path']
            exclude_param = config.get('exclude_param')
            
            # Start with base queryset
            filtered_qs = base_qs
            
            # Apply other filters (exclude current filter)
            for other_config in filter_configs:
                if other_config['name'] != filter_name:
                    param_name = other_config['param_name']
                    param_value = self.request.GET.get(param_name)
                    if param_value:
                        other_field_path = other_config['field_path']
                        filtered_qs = filtered_qs.filter(**{other_field_path: param_value})
            
            # Get distinct values for this filter
            distinct_values = filtered_qs.values_list(field_path, flat=True).distinct()
            
            # Handle different field types
            if field_path == 'organization':
                # For organization field, create a list of dicts with organization values
                context[filter_name] = [{'organization': value} for value in distinct_values if value]
            else:
                # For ID-based fields, get the actual model objects
                context[filter_name] = model.objects.filter(id__in=distinct_values).order_by('name')
        
        return context


class AssignmentTabsView(DynamicFilterMixin, ListView):
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
        
        # Apply date filters
        date_field_mapping = {
            'start_date': 'start_date',
            'end_date': 'end_date'
        }
        qs = self.apply_date_filters(qs, date_field_mapping)
        
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
        
        # Get dynamic filter options using the same base queryset
        filter_configs = [
            {
                'name': 'organizations',
                'model': Assignment,
                'field_path': 'organization',
                'param_name': 'organization',
                'distinct': True
            },
            {
                'name': 'clients',
                'model': Ministry,
                'field_path': 'ministry__id',
                'param_name': 'ministry'
            }
        ]
        
        # Use the same base queryset for dynamic filter options
        context.update(self.get_dynamic_filter_options(base_qs, filter_configs))
        
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
        
        return context
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            # Always return full tab section for HTMX requests to update counts
            return ['parts/assignment_tabs_section.html']
        else:
            return ['assignment_tabs.html']


class ColleagueList(DynamicFilterMixin, ListView):
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
        
        # Get base queryset for dynamic filtering
        base_qs = Colleague.objects.select_related('brand').prefetch_related('skills')
        
        # Apply non-dropdown filters
        name_filter = self.request.GET.get('name')
        if name_filter:
            base_qs = base_qs.filter(name__icontains=name_filter)
        
        # Get dynamic filter options
        filter_configs = [
            {
                'name': 'skills',
                'model': Skill,
                'field_path': 'skills__id',
                'param_name': 'skill'
            },
            {
                'name': 'brands',
                'model': Brand,
                'field_path': 'brand__id',
                'param_name': 'brand'
            }
        ]
        
        context.update(self.get_dynamic_filter_options(base_qs, filter_configs))
        
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


class PlacementList(DynamicFilterMixin, ListView):
    """
    View for placements with tabbed interface (Inzet/Beschikbaarheid)
    
    Features:
    - Dynamic filtering with preserved state
    - HTMX support for smooth interactions
    - Tab-based content switching (table/timeline)
    - Timeline data generation for availability view
    """
    template_name = 'placement_list.html'
    model = Placement

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

        # Apply date filters
        date_field_mapping = {
            'start_date': 'service__assignment__start_date',
            'end_date': 'service__assignment__end_date'
        }
        qs = self.apply_date_filters(qs, date_field_mapping)
        
        return qs.distinct()

    def get_context_data(self, **kwargs):
        """Add dynamic filter options and timeline data"""
        context = super().get_context_data(**kwargs)
        
        # Get base queryset for dynamic filtering
        base_qs = Placement.objects.select_related(
            'colleague__brand', 'service__skill', 'service__assignment__ministry'
        )
        
        # Apply non-dropdown filters
        search_filter = self.request.GET.get('search')
        if search_filter:
            base_qs = base_qs.filter(
                Q(colleague__name__icontains=search_filter) |
                Q(service__assignment__name__icontains=search_filter) |
                Q(service__assignment__organization__icontains=search_filter) |
                Q(service__assignment__ministry__name__icontains=search_filter) |
                Q(service__assignment__ministry__abbreviation__icontains=search_filter)
            )
        
        # Apply date filters to base queryset
        date_field_mapping = {
            'start_date': 'service__assignment__start_date',
            'end_date': 'service__assignment__end_date'
        }
        base_qs = self.apply_date_filters(base_qs, date_field_mapping)
        
        # Get dynamic filter options
        filter_configs = [
            {
                'name': 'skills',
                'model': Skill,
                'field_path': 'service__skill__id',
                'param_name': 'skill'
            },
            {
                'name': 'brands',
                'model': Brand,
                'field_path': 'colleague__brand__id',
                'param_name': 'brand'
            },
            {
                'name': 'clients',
                'model': Ministry,
                'field_path': 'service__assignment__ministry__id',
                'param_name': 'client'
            }
        ]
        
        context.update(self.get_dynamic_filter_options(base_qs, filter_configs))
        
        # Add timeline data
        context.update(self._get_timeline_context())
        
        # Add active tab context
        context['active_tab'] = self.request.GET.get('tab', 'inzet')
        
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
    
    def get_template_names(self):
        """Return appropriate template based on request type"""
        if 'HX-Request' in self.request.headers:
            # For sort requests, return only the table template
            if 'order' in self.request.GET:
                return ['parts/placement_table.html']
            # For other HTMX requests, return the content area template
            return ['parts/placement_content.html']
        else:
            return ['placement_list.html']


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
    clients = Assignment.objects.values_list('organization', flat=True).distinct()
    return render(request, template_name='client_list.html', context={'clients': clients})

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
        return Ministry.objects.annotate(
            assignment_count=Count('assignment')
        ).order_by('name')

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

# Other views
class SkillsView(TemplateView):
    template_name = 'skills.html'

