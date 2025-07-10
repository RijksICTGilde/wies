from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView
from django.template.defaulttags import register
from django.shortcuts import redirect
from django.urls import reverse_lazy

from .models import Project
from .models import Colleague
from .models import Skills

def home(request):
    return redirect('/projects/')

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

# Create your views here.
class ProjectList(ListView):
    template_name = 'projects.html'
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
            return ['project_table.html']
        else:
            return ['projects.html']

class ProjectCreateView(CreateView):
    model = Project
    fields = ['name', 'start_date']
    template_name = 'projects_new.html'

class ProjectDetail(DetailView):
    model = Project
    template_name = 'project_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        skill_list = []
        for skill_val in self.object.skills:
            skill_list.append({
                'val': skill_val,
                'label': Skills(skill_val).label
            })

        context["colleague_list"] = list(self.object.colleagues.values('name', 'id'))
        context["skill_list"] = skill_list
        return context

class ProjectDeleteView(DeleteView):
    model = Project
    success_url = reverse_lazy("projects")
    template_name='project_delete.html'

class ProjectUpdateView(UpdateView):
    model = Project
    # fields = ['name', 'start_date']
    # template_name='project_update.html'
    fields = ['name', 'start_date', 'end_date', 'colleagues', 'status', 'organization', 'extra_info', 'skills'] # these lines are necessary to enable linking of colleagues and projects 
    template_name='project_update_minimal.html'  


class ColleagueList(ListView):
    template_name = 'colleagues.html'
    model = Colleague

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: not happy about this. it is often repeated
        # should look for better solution to get both value and label into template
        skills = {}  # key = id, val = skill_list
        for colleague in context['object_list']:
            skill_list = []
            for skill_val in colleague.skills:
                skill_list.append({
                    'val': skill_val,
                    'label': Skills(skill_val).label
                })
            skills[colleague.id] = skill_list

        context['skills'] = skills
        return context

class ColleagueCreateView(CreateView):
    model = Colleague
    fields = ['name', 'function']
    template_name = 'colleagues_new.html'

class ColleagueDetail(DetailView):
    model = Colleague
    template_name = 'colleague_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        skill_list = []
        for skill_val in self.object.skills:
            skill_list.append({
                'val': skill_val,
                'label': Skills(skill_val).label
            })

        context["skill_list"] = skill_list
        context["project_list"] = list(self.object.projects.values('name', 'id'))
        return context

class ColleagueDeleteView(DeleteView):
    model = Colleague
    success_url = reverse_lazy("colleagues")
    template_name='colleague_delete.html'

class ColleagueUpdateView(UpdateView):
    model = Colleague
    fields = ['name', 'skills']
    template_name='colleague_update_minimal.html'
