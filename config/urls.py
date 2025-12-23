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

from wies.core.views import client
from wies.core.views import AssignmentDetailView, ColleagueDetailView
from wies.core.views import PlacementListView
from wies.core.views import MinistryDetailView
from wies.core.views import admin_db, login, no_access, logout, auth
from wies.core.views import UserListView, user_create, user_edit, user_delete, user_import_csv
from wies.core.views import placement_import_csv, dialog

urlpatterns = [
    path('admin/db/', admin_db, name='admin-db'),
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='placements', permanent=False), name='home'),
    path('login/', login, name='login'),
    path('no-access/', no_access),
    path('logout/', logout, name='logout'),
    path('auth/', auth, name='auth'),
    path('assignments/<int:pk>/', AssignmentDetailView.as_view(), name='assignment-detail'),
    path('colleagues/<int:pk>/', ColleagueDetailView.as_view(), name='colleague-detail'),
    path('placements/', PlacementListView.as_view(), name='placements'),
    path('placements/import/', placement_import_csv, name='placement-import-csv'),
    path('clients/<str:name>', client),
    path('ministries/<int:pk>/', MinistryDetailView.as_view(), name='ministry-detail'),
    path('users/', UserListView.as_view(), name='users'),
    path('users/create/', user_create, name='user-create'),
    path('users/<int:pk>/edit/', user_edit, name='user-edit'),
    path('users/<int:pk>/delete/', user_delete, name='user-delete'),
    path('users/import/', user_import_csv, name='user-import-csv'),
    path('dialog', dialog),
]
