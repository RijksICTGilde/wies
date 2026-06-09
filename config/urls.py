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
from django.urls import path
from django.views.generic import RedirectView

from wies.core.views import (
    AssignmentListNDDView,
    AssignmentListView,
    PlacementListNDDView,
    PlacementListView,
    UserListNDDView,
    UserListView,
    assignment_create,
    assignment_events_partial,
    assignment_import_csv,
    assignment_import_csv_ndd,
    client_modal,
    contact,
    contact_ndd,
    error_400,
    error_403,
    error_404,
    error_500,
    inline_edit_view,
    label_admin,
    label_admin_ndd,
    label_category_create,
    label_category_delete,
    label_category_edit,
    label_create,
    label_delete,
    label_edit,
    no_access,
    organization_admin,
    organization_admin_ndd,
    privacy,
    privacy_ndd,
    robots_txt,
    search_suggestions,
    staff_dashboard,
    staff_dashboard_ndd,
    staff_database,
    staff_database_ndd,
    toegankelijkheid,
    toegankelijkheid_ndd,
    user_create,
    user_delete,
    user_edit,
    user_import_csv,
    user_import_csv_ndd,
    user_profile,
    user_profile_ndd,
)
from wies.rijksauth.views import auth, login, logout

urlpatterns = [
    # Well-known paths
    path("favicon.ico", RedirectView.as_view(url=settings.STATIC_URL + "favicon.ico", permanent=False)),
    path("robots.txt", robots_txt, name="robots-txt"),
    path(
        ".well-known/security.txt",
        RedirectView.as_view(url="https://www.ncsc.nl/.well-known/security.txt", permanent=False),
        name="security-txt",
    ),
    # Wies
    path("", PlacementListView.as_view(), name="home"),
    path("ndd/", PlacementListNDDView.as_view(), name="ndd-home"),
    path("ndd/vacatures/", AssignmentListNDDView.as_view(), name="ndd-assignments"),
    path("ndd/profiel/", user_profile_ndd, name="ndd-profile"),
    path("ndd/beheer/gebruikers/", UserListNDDView.as_view(), name="ndd-admin-users"),
    path("ndd/beheer/labels/", label_admin_ndd, name="ndd-label-admin"),
    path("ndd/vacatures/importeren/", assignment_import_csv_ndd, name="ndd-assignment-import-csv"),
    path("ndd/contact/", contact_ndd, name="ndd-contact"),
    path("ndd/privacy/", privacy_ndd, name="ndd-privacy"),
    path("ndd/toegankelijkheid/", toegankelijkheid_ndd, name="ndd-toegankelijkheid"),
    path("ndd/beheer/statistieken/", staff_dashboard_ndd, name="ndd-staff-dashboard"),
    path("ndd/beheer/database/", staff_database_ndd, name="ndd-staff-database"),
    path("ndd/beheer/organisaties/", organization_admin_ndd, name="ndd-organization-admin"),
    path("ndd/beheer/gebruikers/importeren/", user_import_csv_ndd, name="ndd-user-import-csv"),
    path("inloggen/", login, name="login"),
    path("geen-toegang/", no_access),
    path("uitloggen/", logout, name="logout"),
    path("auth/", auth, name="auth"),
    path("opdrachten/", AssignmentListView.as_view(), name="assignment-list"),
    path("opdrachten/aanmaken/", assignment_create, name="assignment-create"),
    path("opdrachten/importeren/", assignment_import_csv, name="assignment-import-csv"),
    path("opdrachten/<int:pk>/events/", assignment_events_partial, name="assignment-events-partial"),
    path("beheer/", RedirectView.as_view(pattern_name="admin-users", permanent=False), name="admin"),
    path("beheer/gebruikers/", UserListView.as_view(), name="admin-users"),
    path("beheer/gebruikers/aanmaken/", user_create, name="user-create"),
    path("beheer/gebruikers/<int:pk>/bewerken/", user_edit, name="user-edit"),
    path("beheer/gebruikers/<int:pk>/verwijderen/", user_delete, name="user-delete"),
    path("beheer/gebruikers/importeren/", user_import_csv, name="user-import-csv"),
    path("beheer/organisaties/", organization_admin, name="organization-admin"),
    path("beheer/labels/", label_admin, name="label-admin"),
    path("beheer/labels/categorie/aanmaken/", label_category_create, name="label-category-create"),
    path("beheer/labels/categorie/<int:pk>/bewerken/", label_category_edit, name="label-category-edit"),
    path("beheer/labels/categorie/<int:pk>/verwijderen/", label_category_delete, name="label-category-delete"),
    path("beheer/labels/categorie/<int:pk>/labels/aanmaken/", label_create),
    path("beheer/labels/<int:pk>/bewerken/", label_edit, name="label-edit"),
    path("beheer/labels/<int:pk>/verwijderen/", label_delete, name="label-delete"),
    path("beheer/statistieken/", staff_dashboard, name="staff-dashboard"),
    path("beheer/database/", staff_database, name="staff-database"),
    path("profiel/", user_profile, name="user-profile"),
    path("contact/", contact, name="contact"),
    path("privacy/", privacy, name="privacy"),
    path("toegankelijkheid/", toegankelijkheid, name="toegankelijkheid"),
    path("zoek-suggesties/", search_suggestions, name="search-suggestions"),
    path("client-modal/", client_modal, name="client-modal"),
    path(
        "inline-edit/<slug:model_label>/<int:pk>/<slug:name>/",
        inline_edit_view,
        name="inline-edit",
    ),
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
