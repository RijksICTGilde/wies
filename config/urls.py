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

from wies.core.views import (
    PlacementListView,
    UserListView,
    admin_db,
    assignment_edit_attribute,
    auth,
    label_admin,
    label_category_create,
    label_category_delete,
    label_category_edit,
    label_create,
    label_delete,
    label_edit,
    login,
    logout,
    no_access,
    placement_import_csv,
    user_create,
    user_delete,
    user_edit,
    user_import_csv,
)

urlpatterns = [
    path("djadmin/db/", admin_db, name="djadmin-db"),
    path("djadmin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="placements", permanent=False), name="home"),
    path("inloggen/", login, name="login"),
    path("geen-toegang/", no_access),
    path("uitloggen/", logout, name="logout"),
    path("auth/", auth, name="auth"),
    path("plaatsingen/", PlacementListView.as_view(), name="placements"),
    path("plaatsingen/importeren/", placement_import_csv, name="placement-import-csv"),
    path("opdrachten/<int:pk>/edit/<str:attribute>/", assignment_edit_attribute, name="assignment-edit-attribute"),
    path("instellingen/", RedirectView.as_view(pattern_name="admin-users", permanent=False), name="admin"),
    path("instellingen/gebruikers/", UserListView.as_view(), name="admin-users"),
    path("instellingen/gebruikers/aanmaken/", user_create, name="user-create"),
    path("instellingen/gebruikers/<int:pk>/bewerken/", user_edit, name="user-edit"),
    path("instellingen/gebruikers/<int:pk>/verwijderen/", user_delete, name="user-delete"),
    path("instellingen/gebruikers/importeren/", user_import_csv, name="user-import-csv"),
    path("instellingen/labels/", label_admin, name="label-admin"),
    path("instellingen/labels/categorie/aanmaken/", label_category_create, name="label-category-create"),
    path("instellingen/labels/categorie/<int:pk>/bewerken/", label_category_edit, name="label-category-edit"),
    path("instellingen/labels/categorie/<int:pk>/verwijderen/", label_category_delete, name="label-category-delete"),
    path("instellingen/labels/categorie/<int:pk>/labels/aanmaken/", label_create),
    path("instellingen/labels/<int:pk>/bewerken/", label_edit, name="label-edit"),
    path("instellingen/labels/<int:pk>/verwijderen/", label_delete, name="label-delete"),
]
