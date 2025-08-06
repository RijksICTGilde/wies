from django.urls import path
from . import views

app_name = 'exact'

urlpatterns = [
    # Dashboard
    path('', views.exact_dashboard, name='dashboard'),
    
    # Employee URLs
    path('employees/', views.ExactEmployeeListView.as_view(), name='employee-list'),
    path('employees/new/', views.ExactEmployeeCreateView.as_view(), name='employee-create'),
    path('employees/<int:pk>/', views.ExactEmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/<int:pk>/update/', views.ExactEmployeeUpdateView.as_view(), name='employee-update'),
    path('employees/<int:pk>/delete/', views.ExactEmployeeDeleteView.as_view(), name='employee-delete'),
    
    # Project URLs
    path('projects/', views.ExactProjectListView.as_view(), name='project-list'),
    path('projects/new/', views.ExactProjectCreateView.as_view(), name='project-create'),
    path('projects/<int:pk>/', views.ExactProjectDetailView.as_view(), name='project-detail'),
    path('projects/<int:pk>/update/', views.ExactProjectUpdateView.as_view(), name='project-update'),
    path('projects/<int:pk>/delete/', views.ExactProjectDeleteView.as_view(), name='project-delete'),
]