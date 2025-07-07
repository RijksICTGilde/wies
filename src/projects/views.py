from django.shortcuts import render
from django.views.generic.list import ListView
from django.views.generic import FormView, DetailView, CreateView

from django.shortcuts import redirect
from django.urls import reverse_lazy

from .models import Project
from .models import Colleague

def home(request):
    return redirect('/projects/')

# Create your views here.
class ProjectList(ListView):
    template_name = 'projects.html'
    model = Project

class ProjectCreateView(CreateView):
    model = Project
    fields = ['name', 'start_date']
    template_name = 'projects_new.html'

class ProjectDetail(DetailView):
    model = Project
    template_name = 'project_detail.html'

class ColleagueList(ListView):
    template_name = 'colleagues.html'
    model = Colleague

class ColleagueCreateView(CreateView):
    model = Colleague
    fields = ['name', 'function']
    template_name = 'colleagues_new.html'

class ColleagueDetail(DetailView):
    model = Colleague
    template_name = 'colleague_detail.html'