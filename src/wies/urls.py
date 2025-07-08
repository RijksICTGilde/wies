"""
URL configuration for wies project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from projects.views import home
from projects.views import ProjectList
from projects.views import ProjectCreateView, ColleagueCreateView, ProjectDeleteView, ColleagueDeleteView
from projects.views import ProjectDetail, ColleagueDetail, ProjectUpdateView, ColleagueUpdateView
from projects.views import ColleagueList

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home),
    path('projects/', ProjectList.as_view(), name='projects'),
    path('projects/new', ProjectCreateView.as_view()),
    path('projects/<int:pk>/', ProjectDetail.as_view(), name='project-detail'),
    path('projects/<int:pk>/delete', ProjectDeleteView.as_view()),
    path('projects/<int:pk>/update', ProjectUpdateView.as_view()),
    path('colleagues/', ColleagueList.as_view(), name='colleagues'),
    path('colleagues/new', ColleagueCreateView.as_view()),
    path('colleagues/<int:pk>/', ColleagueDetail.as_view(), name='colleague-detail'),
    path('colleagues/<int:pk>/delete', ColleagueDeleteView.as_view()),
    path('colleagues/<int:pk>/update', ColleagueUpdateView.as_view()),
]
