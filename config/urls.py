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

from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from wies.core.views import (
    OrganizationUnitListView,
    PlacementListView,
    UserListView,
    admin_db,
    assignment_edit_attribute,
    auth,
    error_400,
    error_403,
    error_404,
    error_500,
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
    organization_create,
    organization_delete,
    organization_edit,
    organization_filter_modal,
    organization_tree_category_children,
    organization_tree_category_children_modal,
    organization_tree_children,
    organization_tree_children_modal,
    organization_tree_search,
    placement_import_csv,
    robots_txt,
    user_create,
    user_delete,
    user_edit,
    user_import_csv,
)

urlpatterns = [
    # Well-known paths
    path("robots.txt", robots_txt, name="robots-txt"),
    path(
        ".well-known/security.txt",
        RedirectView.as_view(url="https://www.ncsc.nl/.well-known/security.txt", permanent=False),
        name="security-txt",
    ),
    # Admin
    path("djadmin/db/", admin_db, name="djadmin-db"),
    path("djadmin/", admin.site.urls),
    # Wies
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
    path("instellingen/organisaties/", OrganizationUnitListView.as_view(), name="organization-list"),
    path("instellingen/organisaties/aanmaken/", organization_create, name="organization-create"),
    path("instellingen/organisaties/<int:pk>/bewerken/", organization_edit, name="organization-edit"),
    path("instellingen/organisaties/<int:pk>/verwijderen/", organization_delete, name="organization-delete"),
    # Organization filter partials (used by placements filter)
    path("plaatsingen/opdrachtgever/filter/", organization_filter_modal, name="organization-filter-modal"),
    path(
        "plaatsingen/opdrachtgever/tree/categorie/<str:org_type>/",
        organization_tree_category_children,
        name="organization-tree-category-children",
    ),
    path(
        "plaatsingen/opdrachtgever/tree/<int:parent_id>/", organization_tree_children, name="organization-tree-children"
    ),
    path(
        "plaatsingen/opdrachtgever/tree-modal/<int:parent_id>/",
        organization_tree_children_modal,
        name="organization-tree-children-modal",
    ),
    path(
        "plaatsingen/opdrachtgever/tree-modal/categorie/<str:org_type>/",
        organization_tree_category_children_modal,
        name="organization-tree-category-children-modal",
    ),
    path("plaatsingen/opdrachtgever/zoeken/", organization_tree_search, name="organization-tree-search"),
]

# Custom error handlers
handler400 = error_400
handler403 = error_403
handler404 = error_404
handler500 = error_500

if settings.DEBUG:
    urlpatterns += [
        path("test-400/", error_400, name="test-400"),
        path("test-403/", error_403, name="test-403"),
        path("test-404/", error_404, name="test-404"),
        path("test-500/", error_500, name="test-500"),
    ]
