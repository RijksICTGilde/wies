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
from django.views.generic import RedirectView

from wies.projects.views import client
from wies.projects.views import AssignmentDetail, ColleagueDetail
from wies.projects.views import PlacementTableView
from wies.projects.views import MinistryDetailView
from wies.projects.views import admin_db, login, logout, auth

urlpatterns = [
    path('admin/db/', admin_db, name='admin-db'),
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='placements', permanent=False), name='home'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('auth/', auth, name='auth'),
    path('assignments/<int:pk>/', AssignmentDetail.as_view(), name='assignment-detail'),
    path('colleagues/<int:pk>/', ColleagueDetail.as_view(), name='colleague-detail'),
    path('placements/', PlacementTableView.as_view(), name='placements'),
    path('clients/<str:name>', client),
    path('ministries/<int:pk>/', MinistryDetailView.as_view(), name='ministry-detail'),
]
