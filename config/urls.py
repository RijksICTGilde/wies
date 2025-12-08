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

from wies.core.views import PlacementListView
from wies.core.views import admin_db, login, no_access, logout, auth
from wies.core.views import UserListView, user_create, user_edit, user_delete, user_import_csv
from wies.core.views import placement_import_csv
from wies.core.views import label_category_list, label_category_create, label_category_edit, label_category_delete
from wies.core.views import label_create, label_edit, label_delete


urlpatterns = [
    path('djadmin/db/', admin_db, name='djadmin-db'),
    path('djadmin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='placements', permanent=False), name='home'),
    path('login/', login, name='login'),
    path('no-access/', no_access),
    path('logout/', logout, name='logout'),
    path('auth/', auth, name='auth'),
    path('placements/', PlacementListView.as_view(), name='placements'),
    path('placements/import/', placement_import_csv, name='placement-import-csv'),
    path('admin/', RedirectView.as_view(pattern_name='admin-users', permanent=False), name='admin'),
    path('admin/users/', UserListView.as_view(), name='admin-users'),
    path('admin/users/create/', user_create, name='user-create'),
    path('admin/users/<int:pk>/edit/', user_edit, name='user-edit'),
    path('admin/users/<int:pk>/delete/', user_delete, name='user-delete'),
    path('admin/users/import/', user_import_csv, name='user-import-csv'),
    path('admin/labels/', label_category_list, name='label-categories'),
    path('admin/labels/category/create/', label_category_create, name='label-category-create'),
    path('admin/labels/category/<int:pk>/edit/', label_category_edit, name='label-category-edit'),
    path('admin/labels/category/<int:pk>/delete/', label_category_delete, name='label-category-delete'),
    path('admin/labels/category/<int:pk>/labels/create/', label_create),
    path('admin/labels/<int:pk>/edit/', label_edit, name='label-edit'),
    path('admin/labels/<int:pk>/delete/', label_delete, name='label-delete'),
]
