from django.views.generic.list import ListView
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView
from django.template.defaulttags import register
from django.shortcuts import redirect
from django.urls import reverse_lazy

from .models import Project
from .models import Colleague
from .models import Skills

from django import forms

from multiselectfield import MultiSelectFormField

class RVOFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if name == "colleagues":
                # Forceer de juiste class voor Select2
                widget.attrs['class'] = "js-colleague-select utrecht-select utrecht-select--html-select"
            elif name == "skills":
                # Forceer de juiste class voor Select2
                widget.attrs['class'] = "js-skills-select utrecht-select utrecht-select--html-select"
            elif isinstance(widget, forms.DateInput):
                widget.input_type = 'date'
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-textbox utrecht-textbox--html-input utrecht-textbox--sm'
            elif isinstance(widget, forms.TextInput):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-textbox utrecht-textbox--html-input'
            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-textarea utrecht-textarea--html-textarea'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-select utrecht-select--html-select'
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-select utrecht-select--html-select utrecht-select--multiple'

class ProjectForm(RVOFormMixin, forms.ModelForm):
    skills = MultiSelectFormField(required=False, choices=Skills.choices, widget=forms.SelectMultiple)  # overwrite default widget

    class Meta:
        model = Project
        fields = '__all__'

class ColleagueForm(RVOFormMixin, forms.ModelForm):
    skills = MultiSelectFormField(required=False, choices=Skills.choices, widget=forms.SelectMultiple)  # overwrite default widget

    class Meta:
        model = Colleague
        fields = '__all__'

def home(request):
    return redirect('/projects/')

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

# Create your views here.
class ProjectList(ListView):
    template_name = 'projects.html'
    model = Project

    def get_queryset(self):
        qs = Project.objects.order_by('-start_date')

        status_filter = dict(self.request.GET).get('status')  # without dict casting you get single items per get call
        order = self.request.GET.get('order')

        if status_filter:
            qs = qs.filter(status__in=status_filter)
        if order:
            qs = qs.order_by(order)

        return qs
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            return ['project_table.html']
        else:
            return ['projects.html']

class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects_new.html'

class ProjectDetail(DetailView):
    model = Project
    template_name = 'project_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        skill_list = []
        for skill_val in self.object.skills:
            skill_list.append({
                'val': skill_val,
                'label': Skills(skill_val).label
            })

        context["colleague_list"] = list(self.object.colleagues.values('name', 'id'))
        context["skill_list"] = skill_list
        return context

class ProjectDeleteView(DeleteView):
    model = Project
    success_url = reverse_lazy("projects")
    template_name='project_delete.html'

class ProjectUpdateView(UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'project_update_minimal.html'

class ColleagueList(ListView):
    template_name = 'colleagues.html'
    model = Colleague

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: not happy about this. it is often repeated
        # should look for better solution to get both value and label into template
        skills = {}  # key = id, val = skill_list
        for colleague in context['object_list']:
            skill_list = []
            for skill_val in colleague.skills:
                skill_list.append({
                    'val': skill_val,
                    'label': Skills(skill_val).label
                })
            skills[colleague.id] = skill_list

        context['skills'] = skills
        return context

class ColleagueCreateView(CreateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleagues_new.html'

class ColleagueDetail(DetailView):
    model = Colleague
    template_name = 'colleague_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        skill_list = []
        for skill_val in self.object.skills:
            skill_list.append({
                'val': skill_val,
                'label': Skills(skill_val).label
            })

        context["skill_list"] = skill_list
        context["project_list"] = list(self.object.projects.values('name', 'id'))
        return context

class ColleagueDeleteView(DeleteView):
    model = Colleague
    success_url = reverse_lazy("colleagues")
    template_name='colleague_delete.html'

class ColleagueUpdateView(UpdateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleague_update.html'
