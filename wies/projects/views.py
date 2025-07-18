from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .models import Assignment, Colleague, Skills, Placement
from .forms import AssignmentForm, ColleagueForm, PlacementForm

def home(request):
    return redirect('/assignments/')

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_skill_labels(skill_values):
    """Convert skill values to labels"""
    labels = []
    for skill_val in skill_values:
        try:
            labels.append(Skills(skill_val).label)
        except ValueError:
            labels.append(skill_val)  # fallback to value if label not found
    return labels

# Create your views here.
class AssignmentList(ListView):
    template_name = 'assignment_list.html'
    model = Assignment

    def get_queryset(self):
        qs = Assignment.objects.order_by('-start_date')

        status_filter = dict(self.request.GET).get('status')  # without dict casting you get single items per get call
        order = self.request.GET.get('order')

        if status_filter:
            qs = qs.filter(status__in=status_filter)
        if order:
            qs = qs.order_by(order)

        return qs
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            return ['parts/assignment_table.html']
        else:
            return ['assignment_list.html']

class AssignmentCreateView(CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignment_new.html'

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

class ColleagueCreateView(CreateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleague_new.html'

class ColleagueDetail(DetailView):
    model = Colleague
    template_name = 'colleague_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        assignment_list = []
        for placement in self.object.placements.all():
            assignment_list.append({
                'name': placement.assignment.name,
                'id': placement.assignment.id,
                'assignment_type': placement.assignment.assignment_type,
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

class PlacementCreateView(CreateView):
    model = Placement
    form_class = PlacementForm
    template_name = 'placement_new.html'

class PlacementDeleteView(DeleteView):
    model = Placement
    success_url = reverse_lazy("assignments")
    template_name='placement_delete.html'
    

def client(request, name):

    assignments = Assignment.objects.filter(organization=name)

    # Build context with assignment data including colleagues
    assignments_data = []
    for assignment in assignments:
        colleagues = []
        for placement in assignment.placements.all():
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
            'colleagues': colleagues
        })

    return render(request, template_name='client_detail.html', context={
        'client_name': name,
        'assignments': assignments_data
    })

