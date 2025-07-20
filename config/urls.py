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

from wies.projects.views import home, client
from wies.projects.views import AssignmentList
from wies.projects.views import AssignmentCreateView, ColleagueCreateView, AssignmentDeleteView, ColleagueDeleteView
from wies.projects.views import AssignmentDetail, ColleagueDetail, AssignmentUpdateView, ColleagueUpdateView
from wies.projects.views import ColleagueList, PlacementDetailView, PlacementUpdateView, PlacementCreateView, PlacementDeleteView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home),
    path('assignments/', AssignmentList.as_view(), name='assignments'),
    path('assignments/new', AssignmentCreateView.as_view()),
    path('assignments/<int:pk>/', AssignmentDetail.as_view(), name='assignment-detail'),
    path('assignments/<int:pk>/delete', AssignmentDeleteView.as_view()),
    path('assignments/<int:pk>/update', AssignmentUpdateView.as_view()),
    path('assignments/<int:pk>/placements/new', PlacementCreateView.as_view()),
    path('colleagues/', ColleagueList.as_view(), name='colleagues'),
    path('colleagues/new', ColleagueCreateView.as_view()),
    path('colleagues/<int:pk>/', ColleagueDetail.as_view(), name='colleague-detail'),
    path('colleagues/<int:pk>/delete', ColleagueDeleteView.as_view()),
    path('colleagues/<int:pk>/update', ColleagueUpdateView.as_view()),
    path('placements/<int:pk>/', PlacementDetailView.as_view(), name='placement-detail'),
    path('placements/<int:pk>/update', PlacementUpdateView.as_view()),
    path('placements/<int:pk>/delete', PlacementDeleteView.as_view()),
    path('clients/<str:name>', client),
]
