import datetime
import json
from urllib.parse import urlencode

from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView, TemplateView
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.db import models
from django.db.models import Case, When, Max, F
from django.http import JsonResponse

from .models import Assignment, Colleague, Skill, Placement, Service, Ministry
from .forms import AssignmentForm, ColleagueForm, PlacementForm, ServiceForm

def home(request):
    return redirect('/placements/')

def get_service_details(request, service_id):
    """AJAX endpoint to get service details for placement form"""
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

@register.filter
def get_item(dictionary, key):
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
    """Build assignments URL with tab and preserved query parameters"""
    from django.urls import reverse
    
    request = context['request']
    params = {'tab': tab_key}
    
    # Preserve existing query parameters
    for param in ['name', 'order', 'skill']:
        value = request.GET.get(param)
        if value:
            params[param] = value
    
    return f"{reverse('assignments')}?{urlencode(params)}"


class AssignmentTabsView(ListView):
    template_name = 'assignment_tabs.html'
    model = Assignment

    def get_base_queryset(self):
        """Get base queryset without status filtering"""
        qs = Assignment.objects.order_by('-start_date')
        
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
        
        # Define tab groups with correct counts
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

class AssignmentCreateView(CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignment_new.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["placement_form"] = PlacementForm()
        context["range"] = range(2)
        return context

class AssignmentDetail(DetailView):
    model = Assignment
    template_name = 'assignment_detail.html'

class AssignmentDeleteView(DeleteView):
    model = Assignment
    success_url = reverse_lazy("assignments")
    template_name='assignment_delete.html'

class AssignmentUpdateView(UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignment_update.html'

class ColleagueList(ListView):
    template_name = 'colleague_list.html'
    model = Colleague

    def get_queryset(self):
        qs = Colleague.objects.all()
        
        # Filter by skill
        skill_filter = dict(self.request.GET).get('skill', [])
        print('skill_filter', skill_filter)
        for skill in skill_filter:
            qs = qs.filter(skills__id=skill)
        
        # Filter by name
        name_filter = self.request.GET.get('name')
        if name_filter:
            qs = qs.filter(name__icontains=name_filter)
            
        # Calculate max end date considering both placement and service period_source properties
        max_end_date_annotation = Max(
            Case(
                When(
                    placements__period_source='SERVICE',
                    then=Case(
                        When(placements__service__period_source='ASSIGNMENT', then='placements__service__assignment__end_date'),
                        default='placements__service__specific_end_date',
                        output_field=models.DateField()
                    )
                ),
                default='placements__specific_end_date',
                output_field=models.DateField()
            )
        )
        qs = qs.annotate(max_end_date=max_end_date_annotation)
        
        # Handle ordering
        order = self.request.GET.get('order')
        if order:
            qs = qs.order_by(order)
        else:
            # Default ordering by max_end_date
            qs = qs.order_by('max_end_date')
            
        return qs
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            return ['parts/colleague_table.html']
        else:
            return ['colleague_list.html']

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

        assignment_list = []
        for placement in self.object.placements.all():
            assignment_list.append({
                'name': placement.service.assignment.name,
                'id': placement.service.assignment.id,
                'assignment_type': placement.service.assignment.assignment_type,
            })

        context["assignment_list"] = assignment_list
        return context

class ColleagueDeleteView(DeleteView):
    model = Colleague
    success_url = reverse_lazy("colleagues")
    template_name='colleague_delete.html'

class ColleagueUpdateView(UpdateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleague_update.html'

class PlacementDetailView(DetailView):
    model = Placement
    template_name = 'placement_detail.html'

class PlacementUpdateView(UpdateView):
    model = Placement
    form_class = PlacementForm
    template_name = 'placement_update.html'

    def form_valid(self, form):
        # todo: not super happy about this work around, but good enough for now
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
        # todo: not super happy about this work around, but good enough for now
        assignment_id = self.kwargs['pk']
        super().form_valid(form)
        return redirect(Assignment.objects.get(id=assignment_id))
    
class PlacementDeleteView(DeleteView):
    model = Placement
    success_url = reverse_lazy("assignments")
    template_name='placement_delete.html'
    
    def post(self, request, *args, **kwargs):
        placement_id = self.kwargs['pk']
        assignment_id = Placement.objects.get(id=placement_id).service.assignment.id
        super().post(request, *args, **kwargs)
        return redirect(Assignment.objects.get(id=assignment_id))


def add_months(source_date, months):
    """Add months to a date using only stdlib"""
    year = source_date.year + (source_date.month + months - 1) // 12
    month = (source_date.month + months - 1) % 12 + 1
    day = min(source_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return source_date.replace(year=year, month=month, day=day)


def add_timedelta(source_date, timedelta):
    # normally date objects do not support adding timedelta
    dt = datetime.datetime(source_date.year, source_date.month, source_date.day)
    return (dt + timedelta).date()


class PlacementList(ListView):
    template_name = 'placement_list.html'
    model = Placement

    def get_queryset(self):
        qs = Placement.objects.order_by('-service__assignment__start_date')

        # TODO: should certain relations be prefetched? the following were suggested:
        # 'colleague'
        # 'service__assignment__client'
        # 'service__assignment'

        
        # Filter by consultant name
        consultant_filter = self.request.GET.get('consultant')
        if consultant_filter:
            qs = qs.filter(colleague__name__icontains=consultant_filter)
        
        # Filter by assignment name  
        assignment_filter = self.request.GET.get('assignment')
        if assignment_filter:
            qs = qs.filter(service__assignment__name__icontains=assignment_filter)
        
        # Filter by skills
        skill_filter = self.request.GET.get('skill')
        if skill_filter:
            qs = qs.filter(service__skill__id=skill_filter)
        
        # Filter by client/organization or ministry
        client_filter = self.request.GET.get('client')
        if client_filter:
            qs = qs.filter(
                models.Q(service__assignment__organization__icontains=client_filter) |
                models.Q(service__assignment__ministry__name__icontains=client_filter) |
                models.Q(service__assignment__ministry__abbreviation__icontains=client_filter)
            )

        # Date filters
        start_date_from = self.request.GET.get('start_date_from')
        if start_date_from:
            qs = qs.filter(
                models.Q(
                    models.Q(period_source='SERVICE') & 
                    models.Q(
                        models.Q(service__period_source='ASSIGNMENT', service__assignment__start_date__gte=start_date_from) |
                        models.Q(service__period_source='SERVICE', service__specific_start_date__gte=start_date_from)
                    )
                ) |
                models.Q(period_source='PLACEMENT', specific_start_date__gte=start_date_from)
            )
        
        start_date_to = self.request.GET.get('start_date_to')
        if start_date_to:
            qs = qs.filter(
                models.Q(
                    models.Q(period_source='SERVICE') & 
                    models.Q(
                        models.Q(service__period_source='ASSIGNMENT', service__assignment__start_date__lte=start_date_to) |
                        models.Q(service__period_source='SERVICE', service__specific_start_date__lte=start_date_to)
                    )
                ) |
                models.Q(period_source='PLACEMENT', specific_start_date__lte=start_date_to)
            )
        
        end_date_from = self.request.GET.get('end_date_from')
        if end_date_from:
            qs = qs.filter(
                models.Q(
                    models.Q(period_source='SERVICE') & 
                    models.Q(
                        models.Q(service__period_source='ASSIGNMENT', service__assignment__end_date__gte=end_date_from) |
                        models.Q(service__period_source='SERVICE', service__specific_end_date__gte=end_date_from)
                    )
                ) |
                models.Q(period_source='PLACEMENT', specific_end_date__gte=end_date_from)
            )
        
        end_date_to = self.request.GET.get('end_date_to')
        if end_date_to:
            qs = qs.filter(
                models.Q(
                    models.Q(period_source='SERVICE') & 
                    models.Q(
                        models.Q(service__period_source='ASSIGNMENT', service__assignment__end_date__lte=end_date_to) |
                        models.Q(service__period_source='SERVICE', service__specific_end_date__lte=end_date_to)
                    )
                ) |
                models.Q(period_source='PLACEMENT', specific_end_date__lte=end_date_to)
            )
        
        # Order by parameter
        order = self.request.GET.get('order')
        if order:
            # Handle complex sorting for date fields that use properties
            if order in ['start_date', '-start_date']:
                # Complex sorting for start_date - use Case/When to handle period_source logic
                qs = qs.annotate(
                    computed_start_date=Case(
                        When(period_source='SERVICE', then=Case(
                            When(service__period_source='ASSIGNMENT', then=F('service__assignment__start_date')),
                            default=F('service__specific_start_date')
                        )),
                        default=F('specific_start_date')
                    )
                ).order_by('computed_start_date' if order == 'start_date' else '-computed_start_date')
            elif order in ['end_date', '-end_date']:
                # Complex sorting for end_date - use Case/When to handle period_source logic
                qs = qs.annotate(
                    computed_end_date=Case(
                        When(period_source='SERVICE', then=Case(
                            When(service__period_source='ASSIGNMENT', then=F('service__assignment__end_date')),
                            default=F('service__specific_end_date')
                        )),
                        default=F('specific_end_date')
                    )
                ).order_by('computed_end_date' if order == 'end_date' else '-computed_end_date')
            else:
                # Standard sorting for other fields
                qs = qs.order_by(order)

        return qs
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            return ['parts/placement_table.html']
        else:
            return ['placement_list.html']


class PlacementTimelineView(ListView):
    template_name = 'placement_timeline.html'
    model = Colleague

    def get_queryset(self):
        # Start met alle consultants die placements hebben
        consultants = Colleague.objects.filter(placements__isnull=False).distinct()
        
        # Filter op geselecteerde consultants (als er filters zijn)
        consultant_filter = dict(self.request.GET).get('consultants')
        if consultant_filter:
            consultants = consultants.filter(id__in=consultant_filter)
        
        # Sorteer op beschikbaarheid - wie het eerst beschikbaar is komt bovenaan
        today = datetime.date.today()
        consultant_availability = []
        
        for consultant in consultants:
            # Vind laatste einddatum van actieve placements
            latest_end_date = None
            for placement in consultant.placements.all():
                # Bereken werkelijke end datum
                if placement.period_source == 'SERVICE':
                    if placement.service.period_source == 'ASSIGNMENT':
                        end_date = placement.service.assignment.end_date
                    else:
                        end_date = placement.service.specific_end_date
                else:
                    end_date = placement.specific_end_date
                
                if end_date and end_date >= today:
                    if latest_end_date is None or end_date > latest_end_date:
                        latest_end_date = end_date
            
            # Als geen actieve placements, dan nu beschikbaar
            availability_date = latest_end_date or today
            consultant_availability.append((consultant, availability_date))
        
        # Sorteer op beschikbaarheidsdatum
        consultant_availability.sort(key=lambda x: x[1])
        
        return [item[0] for item in consultant_availability]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Timeline bereik: 3 maanden geleden tot 9 maanden in de toekomst (12 maanden totaal)
        today = datetime.date.today()
        timeline_start = add_timedelta(today, datetime.timedelta(weeks=-3*4)).replace(day=1) # approximately 3 months back (3 x 4weeks, taking first day of that month)
        timeline_end = add_timedelta(
            add_timedelta(today, 
                          datetime.timedelta(weeks=10*4)).replace(day=1),  # approximately 9 months forwards ((9+1) x 4weeks, taking first day of that month and subtracting 1 day)
            datetime.timedelta(days=-1)) 
        
        # Genereer maand headers
        months = []
        current_month = timeline_start.replace(day=1)
        while current_month <= timeline_end:
            months.append({
                'date': current_month,
                'name': current_month.strftime('%b %Y')
            })
            current_month = add_months(current_month, 1)
        
        # Bereid consultant data voor
        consultant_data = []
        for consultant in context['object_list']:

            placements = consultant.placements.select_related(
                'service__assignment'
            ).all()
            
            # Bereken placement bars
            placement_bars = []
            total_hours = 0
            
            top_placement = 8
            nr_placements = 0
            for placement in placements:

                # Bereken werkelijke start/end datums
                if placement.period_source == 'SERVICE':
                    if placement.service.period_source == 'ASSIGNMENT':
                        start_date = placement.service.assignment.start_date
                        end_date = placement.service.assignment.end_date
                    else:
                        start_date = placement.service.specific_start_date
                        end_date = placement.service.specific_end_date
                else:
                    start_date = placement.specific_start_date
                    end_date = placement.specific_end_date
                
                # Skip placements zonder datums
                if not start_date or not end_date:
                    continue
                
                # Skip placements buiten timeline bereik
                if end_date < timeline_start or start_date > timeline_end:
                    continue
                
                # Clip datums aan timeline bereik
                clipped_start = max(start_date, timeline_start)
                clipped_end = min(end_date, timeline_end)
                
                # Bereken posities
                total_days = (timeline_end - timeline_start).days
                start_offset_days = (clipped_start - timeline_start).days
                duration_days = (clipped_end - clipped_start).days

                start_offset_percent = (start_offset_days / total_days) * 100
                width_percent = (duration_days / total_days) * 100
                
                placement_bars.append({
                    'placement': placement,
                    'project_name': placement.service.assignment.name,
                    'hours_per_week': placement.hours_per_week or 0,
                    'start_offset_percent': int(start_offset_percent),
                    'width_percent': int(width_percent),
                    'start_date': start_date,
                    'end_date': end_date,
                    'clipped_start': clipped_start,
                    'clipped_end': clipped_end,
                    'top_px': top_placement
                })
                
                # Tel uren op (alleen voor actieve placements)
                if start_date <= today <= end_date:
                    total_hours += placement.hours_per_week or 0

                top_placement += 30
                nr_placements += 1
            
            consultant_data.append({
                'consultant': consultant,
                'placements': placement_bars,
                'total_current_hours': total_hours,
                'total_tracks': nr_placements,
                'total_tracks_height': nr_placements*30,
            })
        
        print('nr_placements', nr_placements)

        # Bereken vandaag positie
        today_offset_days = (today - timeline_start).days
        total_timeline_days = (timeline_end - timeline_start).days
        today_position_percent = (today_offset_days / total_timeline_days) * 100
        
        context.update({
            'consultant_data': consultant_data,
            'timeline_start': timeline_start,
            'timeline_end': timeline_end,
            'months': months,
            'today_position_percent': int(today_position_percent),
            'all_consultants': Colleague.objects.filter(placements__isnull=False).distinct().order_by('name'),
        })
        
        return context
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            return ['parts/placement_timeline.html']
        else:
            return ['placement_timeline.html']


class ServiceCreateView(CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_new.html'
    
    def form_valid(self, form):
        assignment_id = self.kwargs['pk']
        form.assignment_id = self.kwargs['pk']
        super().form_valid(form)
        return redirect(Assignment.objects.get(id=assignment_id))


class ServiceUpdateView(UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_update.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = f'/assignments/{context['object'].assignment.id}/'
        return context

    def form_valid(self, form):
        # todo: not super happy about this work around, but good enough for now
        service_id = self.kwargs['pk']
        assignment_id = Service.objects.get(id=service_id).assignment.id
        super().form_valid(form)
        return redirect(Assignment.objects.get(id=assignment_id))

class ServiceDeleteView(DeleteView):
    model = Service
    success_url = reverse_lazy("assignments")
    template_name='service_delete.html'
    
    def post(self, request, *args, **kwargs):
        service_id = self.kwargs['pk']
        assignment_id = Service.objects.get(id=service_id).assignment.id
        super().post(request, *args, **kwargs)
        return redirect(Assignment.objects.get(id=assignment_id))


class ServiceDetailView(DetailView):
    model = Service
    template_name = 'service_detail.html'


def clients(request):
    clients = Assignment.objects.values_list('organization', flat=True).distinct()
    return render(request, template_name='client_list.html', context={
        'clients': clients,
    })

def client(request, name):

    assignments = Assignment.objects.filter(organization=name)

    # Build context with assignment data including colleagues
    assignments_data = []
    for assignment in assignments:
        colleagues = []
        for service in assignment.services.all():
            for placement in service.placements.all():
                if placement.colleague:  # Only add if colleague exists
                    colleagues.append({
                        'id': placement.colleague.pk,
                        'name': placement.colleague.name
                    })
        
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


class SkillsView(TemplateView):
    template_name = 'skills.html'


class MinistryListView(ListView):
    model = Ministry
    template_name = 'ministry_list.html'
    context_object_name = 'ministries'
    
    def get_queryset(self):
        return Ministry.objects.all().order_by('name')


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
        
        # Build context with assignment data including colleagues
        assignments_data = []
        for assignment in assignments:
            colleagues = []
            for service in assignment.services.all():
                for placement in service.placements.all():
                    if placement.colleague:  # Only add if colleague exists
                        colleagues.append({
                            'id': placement.colleague.pk,
                            'name': placement.colleague.name
                        })
            
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

