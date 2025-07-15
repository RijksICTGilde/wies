from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden

from .models import ProjectBase, Project, Colleague, Skills, Assignment, Job
from .forms import ProjectForm, ColleagueForm, AssignmentForm, JobForm

def home(request):
    return redirect('/projects/')

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
class ProjectList(ListView):
    template_name = 'project_list.html'
    model = Project

    def get_queryset(self):
        qs = Project.objects.order_by('-start_date')

        status_filter = dict(self.request.GET).get('status')  # without dict casting you get single items per get call
        order = self.request.GET.get('order')

        if status_filter:
            qs = qs.filter(status__in=status_filter)
        if order:
            qs = qs.order_by(order)

        return qs
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            return ['parts/project_table.html']
        else:
            return ['project_list.html']

class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'project_new.html'

class ProjectDetail(DetailView):
    model = Project
    template_name = 'project_detail.html'

class ProjectDeleteView(DeleteView):
    model = Project
    success_url = reverse_lazy("projects")
    template_name='project_delete.html'

class ProjectUpdateView(UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'project_update.html'

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

        project_list = []
        for assignment in self.object.assignments.all():
            project_list.append({
                'name': assignment.project.name,
                'id': assignment.project.id,
                'project_type': assignment.project.project_type,
            })

        context["project_list"] = project_list
        return context

class ColleagueDeleteView(DeleteView):
    model = Colleague
    success_url = reverse_lazy("colleagues")
    template_name='colleague_delete.html'

class ColleagueUpdateView(UpdateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleague_update.html'

class AssignmentDetailView(DetailView):
    model = Assignment
    template_name = 'assignment_detail.html'

class AssignmentUpdateView(UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignment_update.html'

class AssignmentCreateView(CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignment_new.html'

class AssignmentDeleteView(DeleteView):
    model = Assignment
    success_url = reverse_lazy("projects")
    template_name='assignment_delete.html'
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.project.project_type == 'INDIVIDUAL':
            return HttpResponseForbidden("Cannot delete assignments that belong to jobs (individual projects)")
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.project.project_type == 'INDIVIDUAL':
            return HttpResponseForbidden("Cannot delete assignments that belong to jobs (individual projects)")
        return super().post(request, *args, **kwargs)

def client(request, name):

    projects = ProjectBase.objects.filter(organization=name)

    # Build context with project data including colleagues
    projects_data = []
    for project in projects:
        colleagues = []
        for assignment in project.assignments.all():
            if assignment.colleague:  # Only add if colleague exists
                colleagues.append({
                    'id': assignment.colleague.pk,
                    'name': assignment.colleague.name
                })
        
        projects_data.append({
            'id': project.pk,
            'name': project.name,
            'start_date': project.start_date,
            'end_date': project.end_date,
            'colleagues': colleagues
        })

    return render(request, template_name='client_detail.html', context={
        'client_name': name,
        'projects': projects_data
    })

# Job views for individual projects
class JobList(ListView):
    template_name = 'job_list.html'
    model = Job

    def get_queryset(self):
        qs = Job.objects.order_by('-start_date')

        status_filter = dict(self.request.GET).get('status')
        order = self.request.GET.get('order')

        if status_filter:
            qs = qs.filter(status__in=status_filter)
        if order:
            qs = qs.order_by(order)

        return qs

class JobCreateView(CreateView):
    model = Job
    form_class = JobForm
    template_name = 'job_new.html'

    def form_valid(self, form):
        # Save the job instance first
        response = super().form_valid(form)
        
        # Extract assignment-related fields from the form
        skills = form.cleaned_data.get('skills')
        colleague = form.cleaned_data.get('colleague')
        hours_per_week = form.cleaned_data.get('hours_per_week')
        
        # Always create an assignment (even if empty)
        Assignment.objects.create(
            project=self.object,
            colleague=colleague,  # Can be None
            skills=skills or [],
            hours_per_week=hours_per_week,
            start_date=self.object.start_date,
            end_date=self.object.end_date
        )
        
        return response

class JobDetail(DetailView):
    model = Job
    template_name = 'job_detail.html'

class JobUpdateView(UpdateView):
    model = Job
    form_class = JobForm
    template_name = 'job_update.html'

    def get_initial(self):
        initial = super().get_initial()
        
        # Get the first assignment for this job (assuming one assignment per job)
        assignment = self.object.assignments.first()
        if assignment:
            initial['skills'] = assignment.skills
            initial['colleague'] = assignment.colleague
            initial['hours_per_week'] = assignment.hours_per_week
        
        return initial

    def form_valid(self, form):
        # Save the job instance first
        response = super().form_valid(form)
        
        # Extract assignment-related fields from the form
        skills = form.cleaned_data.get('skills')
        colleague = form.cleaned_data.get('colleague')
        hours_per_week = form.cleaned_data.get('hours_per_week')
        
        # Update the existing assignment
        assignment = self.object.assignments.first()
        if not assignment:
            assignment = Assignment.objects.create(project=ProjectBase.objects.get(id=self.object.id))

        assignment.colleague = colleague  # Can be None
        assignment.skills = skills or []
        assignment.hours_per_week = hours_per_week
        assignment.start_date = self.object.start_date
        assignment.end_date = self.object.end_date
        assignment.save()
        
        return response

class JobDeleteView(DeleteView):
    model = Job
    success_url = reverse_lazy("jobs")
    template_name = 'job_delete.html'
