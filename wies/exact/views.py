from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import ExactEmployee, ExactProject


class ExactEmployeeListView(ListView):
    model = ExactEmployee
    template_name = 'exact/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(naam_medewerker__icontains=search)
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset


class ExactEmployeeDetailView(DetailView):
    model = ExactEmployee
    template_name = 'exact/employee_detail.html'
    context_object_name = 'employee'


class ExactEmployeeCreateView(CreateView):
    model = ExactEmployee
    template_name = 'exact/employee_form.html'
    fields = [
        'naam_medewerker', 'aantal_uren', 'rin_nummer', 'schaalniveau', 
        'kostenplaats', 'if_kf', 'uren_schrijven', 'email', 
        'organisatieonderdeel', 'manager', 'status'
    ]


class ExactEmployeeUpdateView(UpdateView):
    model = ExactEmployee
    template_name = 'exact/employee_form.html'
    fields = [
        'naam_medewerker', 'aantal_uren', 'rin_nummer', 'schaalniveau', 
        'kostenplaats', 'if_kf', 'uren_schrijven', 'email', 
        'organisatieonderdeel', 'manager', 'status'
    ]


class ExactEmployeeDeleteView(DeleteView):
    model = ExactEmployee
    template_name = 'exact/employee_confirm_delete.html'
    success_url = reverse_lazy('exact:employee-list')


class ExactProjectListView(ListView):
    model = ExactProject
    template_name = 'exact/project_list.html'
    context_object_name = 'projects'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        type_project = self.request.GET.get('type')
        
        if search:
            queryset = queryset.filter(projectnaam__icontains=search)
        if type_project:
            queryset = queryset.filter(type_project=type_project)
            
        return queryset


class ExactProjectDetailView(DetailView):
    model = ExactProject
    template_name = 'exact/project_detail.html'
    context_object_name = 'project'


class ExactProjectCreateView(CreateView):
    model = ExactProject
    template_name = 'exact/project_form.html'
    fields = [
        'projectnaam', 'odi_thema', 'product_dienst_assortiment', 
        'start_datum', 'eind_datum', 'aantal_uur', 'tarief', 
        'type_project', 'organisatieonderdeel', 'manager', 'moeder',
        'contract_besteld_door', 'contract_contactpersoon', 
        'contract_factuur_voor', 'contract_ter_attentie_van',
        'contract_eenzijdig_getekend', 'contract_tweezijdig_getekend',
        'uw_referentie', 'uw_kenmerk'
    ]


class ExactProjectUpdateView(UpdateView):
    model = ExactProject
    template_name = 'exact/project_form.html'
    fields = [
        'projectnaam', 'odi_thema', 'product_dienst_assortiment', 
        'start_datum', 'eind_datum', 'aantal_uur', 'tarief', 
        'type_project', 'organisatieonderdeel', 'manager', 'moeder',
        'contract_besteld_door', 'contract_contactpersoon', 
        'contract_factuur_voor', 'contract_ter_attentie_van',
        'contract_eenzijdig_getekend', 'contract_tweezijdig_getekend',
        'uw_referentie', 'uw_kenmerk'
    ]


class ExactProjectDeleteView(DeleteView):
    model = ExactProject
    template_name = 'exact/project_confirm_delete.html'
    success_url = reverse_lazy('exact:project-list')


def exact_dashboard(request):
    """Dashboard view showing overview of employees and projects"""
    employee_count = ExactEmployee.objects.count()
    active_employee_count = ExactEmployee.objects.filter(status='ACTIEF').count()
    project_count = ExactProject.objects.count()
    
    recent_employees = ExactEmployee.objects.order_by('-created_at')[:5]
    recent_projects = ExactProject.objects.order_by('-created_at')[:5]
    
    context = {
        'employee_count': employee_count,
        'active_employee_count': active_employee_count,
        'project_count': project_count,
        'recent_employees': recent_employees,
        'recent_projects': recent_projects,
    }
    
    return render(request, 'exact/dashboard.html', context)