from django.shortcuts import render
from django.views.generic.list import ListView

from .models import Project
from .models import Colleague

# Create your views here.
class ProjectList(ListView):
    template_name = 'projects.html'
    model = Project

class ColleagueList(ListView):
    template_name = 'colleagues.html'
    model = Colleague
